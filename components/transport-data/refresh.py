#!/usr/bin/env python3
"""Download and atomically publish validated static GTFS and OSM inputs."""

import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

MAX_GTFS_BYTES = 500 * 1024 * 1024
MAX_OSM_BYTES = 2 * 1024 * 1024 * 1024
TIMEOUT_SECONDS = 30
ALLOWED_HOSTS = {"mkuran.pl", "download.geofabrik.de"}
REQUIRED_GTFS_FILES = {"agency.txt", "stops.txt", "routes.txt", "trips.txt", "stop_times.txt"}


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        parsed = urllib.parse.urlparse(new_url)
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
            raise ValueError(f"Refusing redirect to unapproved URL: {new_url}")
        return super().redirect_request(request, response, code, message, headers, new_url)


def _download(url, destination, maximum):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError(f"Refusing unapproved source URL: {url}")
    opener = urllib.request.build_opener(SafeRedirectHandler)
    request = urllib.request.Request(url, headers={"User-Agent": "mazowian-highschool-search/transport-data"})
    digest = hashlib.sha256()
    size = 0
    with opener.open(request, timeout=TIMEOUT_SECONDS) as response, destination.open("wb") as output:
        final_url = response.geturl()
        final = urllib.parse.urlparse(final_url)
        if final.scheme != "https" or final.hostname not in ALLOWED_HOSTS:
            raise ValueError(f"Refusing unapproved final URL: {final_url}")
        while chunk := response.read(1024 * 1024):
            size += len(chunk)
            if size > maximum:
                raise ValueError(f"Download exceeds {maximum} bytes")
            output.write(chunk)
            digest.update(chunk)
    return {
        "source_url": url,
        "final_url": final_url,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "size_bytes": size,
        "sha256": digest.hexdigest(),
    }


def _validate_gtfs(path):
    with zipfile.ZipFile(path) as archive:
        names = set()
        for info in archive.infolist():
            member = Path(info.filename)
            if member.is_absolute() or ".." in member.parts or info.is_dir():
                if info.is_dir():
                    continue
                raise ValueError(f"Unsafe GTFS archive member: {info.filename}")
            names.add(member.name)
        missing = REQUIRED_GTFS_FILES - names
        if missing:
            raise ValueError(f"GTFS archive is missing required files: {', '.join(sorted(missing))}")
        if not ({"calendar.txt", "calendar_dates.txt"} & names):
            raise ValueError("GTFS archive has no calendar.txt or calendar_dates.txt")
        for info in archive.infolist():
            if not info.is_dir():
                with archive.open(info) as member:
                    while member.read(1024 * 1024):
                        pass
    return {"validation": "valid-gtfs-zip"}


def _validate_pbf(path):
    with path.open("rb") as source:
        header = source.read(64)
    if len(header) < 15 or b"OSMHeader" not in header:
        raise ValueError("OSM input is not a readable PBF header")
    return {"validation": "valid-osm-pbf-header"}


def refresh(source_config, snapshot_root, downloader=_download):
    snapshot_root = Path(snapshot_root)
    snapshots = snapshot_root / "snapshots"
    snapshots.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".refresh-", dir=snapshots))
    sources_manifest = []
    try:
        config = json.loads(Path(source_config).read_text(encoding="utf-8"))
        osm = config["osm"]
        osm_path = staging / "mazowieckie.osm.pbf"
        osm_metadata = downloader(osm["url"], osm_path, MAX_OSM_BYTES)
        osm_metadata.update({"id": osm["id"], "kind": "osm", "license": osm["license"], "attribution": osm["attribution"]})
        osm_metadata.update(_validate_pbf(osm_path))
        sources_manifest.append(osm_metadata)

        for feed in config["gtfs"]:
            gtfs_path = staging / f"{feed['id']}.gtfs.zip"
            metadata = downloader(feed["url"], gtfs_path, MAX_GTFS_BYTES)
            metadata.update({"id": feed["id"], "kind": "static-gtfs", "license": feed["license"], "attribution": feed["attribution"]})
            metadata.update(_validate_gtfs(gtfs_path))
            sources_manifest.append(metadata)

        manifest = {
            "schema_version": 1,
            "snapshot_id": uuid.uuid4().hex,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "sources": sources_manifest,
        }
        manifest_path = staging / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        snapshot = snapshots / manifest["snapshot_id"]
        staging.rename(snapshot)
        current_tmp = snapshot_root / f".current-{uuid.uuid4().hex}"
        current_tmp.symlink_to(Path("snapshots") / manifest["snapshot_id"])
        current_tmp.replace(snapshot_root / "current")
        return manifest
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


if __name__ == "__main__":
    config = os.environ.get("SOURCES_CONFIG", "/app/sources.json")
    root = os.environ.get("SNAPSHOT_ROOT", "/data/transport")
    try:
        result = refresh(config, root)
    except Exception as error:
        print(f"refresh failed: {error}", file=sys.stderr)
        sys.exit(1)
    print(f"published snapshot {result['snapshot_id']}")
