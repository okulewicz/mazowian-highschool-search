#!/usr/bin/env python3
"""Build, smoke-test, and atomically activate a graph with pinned OTP."""

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

OTP_IMAGE = (
    "opentripplanner/opentripplanner:2.10.0"
    "@sha256:8d54e5c589186707ee365417f2202dc878c451fa3001b8edff07019531100933"
)


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def smoke_test(graph_path):
    name = "otp-smoke-" + uuid.uuid4().hex[:12]
    subprocess.run(
        ["docker", "run", "-d", "--rm", "--name", name, "-p", "127.0.0.1::8080",
         "-v", f"{Path(graph_path).resolve()}:/var/opentripplanner:ro",
         OTP_IMAGE, "--load", "/var/opentripplanner"],
        check=True, capture_output=True, text=True,
    )
    try:
        port_result = subprocess.run(
            ["docker", "port", name, "8080/tcp"], check=True, capture_output=True, text=True
        ).stdout.strip().split(":")[-1]
        endpoint = f"http://127.0.0.1:{port_result}/otp/gtfs/v1"
        body = json.dumps({"query": "{ routes { gtfsId } }"}).encode()
        request = urllib.request.Request(endpoint, data=body, headers={"Content-Type": "application/json"})
        for _ in range(60):
            try:
                with urllib.request.urlopen(request, timeout=2) as response:
                    result = json.loads(response.read())
                if result.get("errors"):
                    raise RuntimeError(f"OTP GraphQL smoke query failed: {result['errors']}")
                return
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                time.sleep(2)
        raise RuntimeError("OTP did not become ready for the GraphQL smoke query")
    finally:
        subprocess.run(["docker", "stop", name], check=False, capture_output=True)


def build(snapshot_root, routing_root):
    snapshot_root = Path(snapshot_root).resolve()
    routing_root = Path(routing_root).resolve()
    current = snapshot_root / "current"
    manifest_path = current / "manifest.json"
    if not current.is_dir() or not manifest_path.is_file():
        raise ValueError(f"Missing validated transport snapshot: {current}")
    snapshot_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if snapshot_manifest.get("schema_version") != 1 or len(snapshot_manifest.get("sources", [])) < 2:
        raise ValueError("Transport snapshot manifest is invalid or incomplete")
    for source in snapshot_manifest["sources"]:
        input_path = current / ("mazowieckie.osm.pbf" if source["kind"] == "osm" else f"{source['id']}.gtfs.zip")
        if not input_path.is_file() or sha256_file(input_path) != source["sha256"]:
            raise ValueError(f"Snapshot input failed checksum verification: {input_path.name}")

    routing_root.mkdir(parents=True, exist_ok=True)
    graphs = routing_root / "graphs"
    graphs.mkdir(exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".build-", dir=graphs))
    try:
        for source in snapshot_manifest["sources"]:
            filename = "mazowieckie.osm.pbf" if source["kind"] == "osm" else f"{source['id']}.gtfs.zip"
            shutil.copyfile(current / filename, staging / filename)
        build_config = {"otp_image": OTP_IMAGE, "command": ["--build", "--save"], "otp_version": "2.10.0"}
        (staging / "build-config.json").write_text(json.dumps(build_config, indent=2) + "\n")
        subprocess.run(
            ["docker", "run", "--rm", "-v", f"{staging}:/var/opentripplanner",
             OTP_IMAGE, "--build", "--save", "/var/opentripplanner"],
            check=True,
        )
        graph_file = staging / "graph.obj"
        if not graph_file.is_file() or graph_file.stat().st_size == 0:
            raise RuntimeError("OTP completed without producing a graph.obj")
        smoke_test(staging)
        manifest = {
            "schema_version": 1,
            "built_at": datetime.now(timezone.utc).isoformat(),
            "otp_version": "2.10.0",
            "otp_image": OTP_IMAGE,
            "build_configuration_sha256": sha256_file(staging / "build-config.json"),
            "transport_snapshot_id": snapshot_manifest["snapshot_id"],
            "inputs": [
                {"id": source["id"], "sha256": source["sha256"]}
                for source in snapshot_manifest["sources"]
            ],
            "graph_sha256": sha256_file(graph_file),
        }
        (staging / "graph-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        graph_id = uuid.uuid4().hex
        destination = graphs / graph_id
        staging.rename(destination)
        pointer = routing_root / f".active-{graph_id}"
        pointer.symlink_to(Path("graphs") / graph_id)
        pointer.replace(routing_root / "active")
        return manifest
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


if __name__ == "__main__":
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".data")
    try:
        result = build(root / "transport", root / "routing")
    except Exception as error:
        print(f"graph build failed: {error}", file=sys.stderr)
        sys.exit(1)
    print(f"activated graph for snapshot {result['transport_snapshot_id']}")
