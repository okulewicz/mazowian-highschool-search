#!/usr/bin/env python3
"""Build and atomically publish PMTiles from a versioned local OSM PBF."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone


TILEMAKER_IMAGE = (
    "ghcr.io/systemed/tilemaker@sha256:"
    "9cd8728a37a31c8a5205e091cedd3ff2c2c450c57e1ce3e5b58916185540ebba"
)
ATTRIBUTION = (
    '<a href="https://www.openstreetmap.org/copyright">'
    "© OpenStreetMap contributors</a>; "
    '<a href="https://www.geofabrik.de/">Geofabrik GmbH</a> processing'
)
SCRIPT_DIR = Path(__file__).resolve().parent


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_id(input_sha256, config_sha256, process_sha256):
    identity = "\n".join(
        (input_sha256, config_sha256, process_sha256, TILEMAKER_IMAGE)
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def publish_current(versions_dir, version_dir):
    current = versions_dir.parent / "current"
    if current.exists() and not current.is_symlink():
        raise RuntimeError(f"refusing to replace non-symlink pointer: {current}")
    temporary_link = versions_dir.parent / f".current-{os.getpid()}"
    temporary_link.unlink(missing_ok=True)
    temporary_link.symlink_to(version_dir.relative_to(versions_dir.parent))
    os.replace(temporary_link, current)


def run_generation(input_path, expected_sha256, output_root, source_url, retrieved_at):
    input_path = input_path.resolve(strict=True)
    if not input_path.is_file():
        raise ValueError(f"OSM input is not a regular file: {input_path}")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise ValueError("--input-sha256 must be a lowercase SHA-256 digest")
    actual_sha256 = sha256_file(input_path)
    if actual_sha256 != expected_sha256:
        raise ValueError(
            f"input checksum mismatch: expected {expected_sha256}, got {actual_sha256}"
        )
    if not source_url.startswith("https://"):
        raise ValueError("--source-url must be an HTTPS URL")
    try:
        datetime.fromisoformat(retrieved_at.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("--retrieved-at must be an ISO 8601 timestamp") from error

    config_path = SCRIPT_DIR / "config.json"
    process_path = SCRIPT_DIR / "process.lua"
    config_sha256 = sha256_file(config_path)
    process_sha256 = sha256_file(process_path)
    version = build_id(actual_sha256, config_sha256, process_sha256)
    output_root = output_root.resolve()
    versions_dir = output_root / "versions"
    versions_dir.mkdir(parents=True, exist_ok=True)
    version_dir = versions_dir / version

    if version_dir.exists():
        manifest_path = version_dir / "manifest.json"
        tiles_path = version_dir / "map.pmtiles"
        if not manifest_path.is_file() or not tiles_path.is_file():
            raise RuntimeError(f"incomplete existing tile version: {version_dir}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("input_sha256") != actual_sha256:
            raise RuntimeError(f"existing tile version has conflicting provenance: {version_dir}")
        if sha256_file(tiles_path) != manifest.get("tiles_sha256"):
            raise RuntimeError(f"existing tile version checksum mismatch: {tiles_path}")
        publish_current(versions_dir, version_dir)
        return manifest

    staging_dir = Path(tempfile.mkdtemp(prefix=".tiles-", dir=versions_dir))
    try:
        tiles_path = staging_dir / "map.pmtiles"
        input_parent = input_path.parent
        command = [
            "docker", "run", "--rm", "--network", "none",
            "--mount", f"type=bind,source={input_parent},target=/input,readonly",
            "--mount", f"type=bind,source={staging_dir.resolve()},target=/output",
            "--mount", f"type=bind,source={SCRIPT_DIR},target=/config,readonly",
            TILEMAKER_IMAGE,
            "--input", f"/input/{input_path.name}",
            "--output", "/output/map.pmtiles",
            "--config", "/config/config.json",
            "--process", "/config/process.lua",
            "--threads", "1",
        ]
        subprocess.run(command, check=True)
        if not tiles_path.is_file() or tiles_path.stat().st_size == 0:
            raise RuntimeError("Tilemaker completed without producing PMTiles")
        with tiles_path.open("rb") as tiles:
            if tiles.read(8) != b"PMTiles\x03":
                raise RuntimeError("Tilemaker output is not a PMTiles v3 archive")

        manifest = {
            "schema_version": 1,
            "tile_format": "PMTiles v3 containing Mapbox Vector Tiles",
            "version": version,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "input": str(input_path.name),
            "input_sha256": actual_sha256,
            "source_url": source_url,
            "retrieved_at": retrieved_at,
            "coverage": "as supplied by the local OSM snapshot",
            "tilemaker_image": TILEMAKER_IMAGE,
            "config_sha256": config_sha256,
            "process_sha256": process_sha256,
            "minzoom": 5,
            "maxzoom": 14,
            "attribution": ATTRIBUTION,
            "tiles_sha256": sha256_file(tiles_path),
            "tiles_bytes": tiles_path.stat().st_size,
        }
        (staging_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(staging_dir, version_dir)
        publish_current(versions_dir, version_dir)
        return manifest
    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="local snapshot OSM PBF")
    parser.add_argument("--input-sha256", required=True, help="expected PBF SHA-256")
    parser.add_argument("--source-url", required=True, help="snapshot source page URL")
    parser.add_argument("--retrieved-at", required=True, help="snapshot retrieval time (ISO 8601)")
    parser.add_argument("--output-root", required=True, type=Path, help="artifact directory")
    args = parser.parse_args(argv)
    try:
        manifest = run_generation(
            args.input,
            args.input_sha256,
            args.output_root,
            args.source_url,
            args.retrieved_at,
        )
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"tile generation failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
