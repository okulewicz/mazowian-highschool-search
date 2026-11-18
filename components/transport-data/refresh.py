#!/usr/bin/env python3
"""Download approved GTFS sources and publish validated immutable snapshots."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
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
from pathlib import Path, PurePosixPath

COMPONENT_DIR = Path(__file__).resolve().parent
SOURCES_FILE = COMPONENT_DIR / "sources.json"
ALLOWED_HOST = "mkuran.pl"
TIMEOUT_SECONDS = 20
RETRIES = 2
MAX_STATIC_BYTES = 512 * 1024 * 1024
MAX_REALTIME_BYTES = 32 * 1024 * 1024
MAX_ZIP_ENTRIES = 20_000
MAX_UNCOMPRESSED_BYTES = 2 * 1024 * 1024 * 1024
MAX_METADATA_FILE_BYTES = 64 * 1024 * 1024
GTFS_REQUIRED_FILES = {
    "agency.txt",
    "routes.txt",
    "stops.txt",
    "trips.txt",
    "stop_times.txt",
}


class RefreshError(Exception):
    """Raised when a required source or snapshot publication fails."""


def _validate_url(url: str) -> None:
    parsed = urllib.parse.urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != ALLOWED_HOST
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
    ):
        raise RefreshError(f"Refusing unapproved source URL: {url}")


class _SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download(url: str, max_bytes: int) -> bytes:
    """Fetch one allowlisted HTTPS URL with bounded retries, time, and size."""
    _validate_url(url)
    opener = urllib.request.build_opener(_SafeRedirect)
    last_error = None
    for attempt in range(RETRIES + 1):
        try:
            body = bytearray()
            with opener.open(url, timeout=TIMEOUT_SECONDS) as response:
                while True:
                    chunk = response.read(min(64 * 1024, max_bytes + 1 - len(body)))
                    if not chunk:
                        return bytes(body)
                    body.extend(chunk)
                    if len(body) > max_bytes:
                        raise RefreshError(
                            f"Source exceeds the {max_bytes}-byte limit: {url}"
                        )
        except RefreshError:
            raise
        except (OSError, urllib.error.URLError) as exc:
            last_error = exc
            if attempt < RETRIES:
                time.sleep(2**attempt)
    raise RefreshError(f"Download failed for {url}: {last_error}") from last_error


def _read_varint(data: bytes, pos: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while pos < len(data) and shift < 70:
        byte = data[pos]
        pos += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, pos
        shift += 7
    raise RefreshError("Malformed GTFS-Realtime protobuf varint")


def _protobuf_fields(data: bytes):
    pos = 0
    while pos < len(data):
        tag, pos = _read_varint(data, pos)
        field_number, wire_type = tag >> 3, tag & 7
        if not field_number:
            raise RefreshError("Malformed GTFS-Realtime protobuf field tag")
        if wire_type == 0:
            value, pos = _read_varint(data, pos)
        elif wire_type == 1:
            end = pos + 8
            if end > len(data):
                raise RefreshError("Truncated GTFS-Realtime protobuf field")
            value, pos = data[pos:end], end
        elif wire_type == 2:
            length, pos = _read_varint(data, pos)
            end = pos + length
            if end > len(data):
                raise RefreshError("Truncated GTFS-Realtime protobuf field")
            value, pos = data[pos:end], end
        elif wire_type == 5:
            end = pos + 4
            if end > len(data):
                raise RefreshError("Truncated GTFS-Realtime protobuf field")
            value, pos = data[pos:end], end
        else:
            raise RefreshError("Unsupported GTFS-Realtime protobuf wire type")
        yield field_number, wire_type, value


def feed_header_timestamp(data: bytes) -> int | None:
    """Read FeedMessage.header.timestamp without decoding feed entities."""
    for number, wire_type, header in _protobuf_fields(data):
        if number == 1 and wire_type == 2:
            for header_number, header_wire, value in _protobuf_fields(header):
                if header_number == 3 and header_wire == 0:
                    return value
            return None
    return None


def _validate_gtfs(data: bytes, source: dict) -> tuple[str, str, str | None]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except (zipfile.BadZipFile, OSError) as exc:
        raise RefreshError(f"Invalid GTFS ZIP for {source['id']}") from exc
    with archive:
        members = archive.infolist()
        if len(members) > MAX_ZIP_ENTRIES:
            raise RefreshError(f"Too many files in GTFS ZIP for {source['id']}")
        total_size = 0
        names = set()
        for member in members:
            path = PurePosixPath(member.filename)
            if path.is_absolute() or ".." in path.parts or "\\" in member.filename:
                raise RefreshError(f"Unsafe path in GTFS ZIP for {source['id']}")
            mode = member.external_attr >> 16
            if mode and (mode & 0o170000) == 0o120000:
                raise RefreshError(f"Symlink in GTFS ZIP for {source['id']}")
            total_size += member.file_size
            if total_size > MAX_UNCOMPRESSED_BYTES:
                raise RefreshError(f"Uncompressed GTFS ZIP is too large for {source['id']}")
            if not member.is_dir():
                names.add(member.filename)
        if not GTFS_REQUIRED_FILES.issubset(names):
            missing = sorted(GTFS_REQUIRED_FILES - names)
            raise RefreshError(f"Missing GTFS files for {source['id']}: {', '.join(missing)}")
        if archive.testzip() is not None:
            raise RefreshError(f"Corrupt member in GTFS ZIP for {source['id']}")

        attribution_text = None
        attribution_name = source.get("attribution_file")
        if attribution_name:
            matches = [
                member for member in members
                if member.filename == attribution_name
            ]
            if not matches:
                raise RefreshError(f"Missing {attribution_name} in {source['id']}")
            if matches[0].file_size > MAX_METADATA_FILE_BYTES:
                raise RefreshError(f"Attribution file too large in {source['id']}")
            attribution_text = archive.read(matches[0]).decode("utf-8-sig")
            missing = [
                credit for credit in source.get("required_attributions", [])
                if credit.casefold() not in attribution_text.casefold()
            ]
            if missing:
                raise RefreshError(
                    f"Missing required attribution in {source['id']}: {', '.join(missing)}"
                )

        dates = []
        if "calendar.txt" in names:
            calendar_member = next(
                member for member in members
                if member.filename == "calendar.txt"
            )
            if calendar_member.file_size > MAX_METADATA_FILE_BYTES:
                raise RefreshError(f"calendar.txt too large in {source['id']}")
            text = archive.read(calendar_member).decode("utf-8-sig")
            for row in csv.DictReader(io.StringIO(text)):
                for key in ("start_date", "end_date"):
                    value = row.get(key, "")
                    if len(value) == 8 and value.isdigit():
                        datetime.strptime(value, "%Y%m%d")
                        dates.append(value)
        if "calendar_dates.txt" in names:
            exception_member = next(
                member for member in members
                if member.filename == "calendar_dates.txt"
            )
            if exception_member.file_size > MAX_METADATA_FILE_BYTES:
                raise RefreshError(f"calendar_dates.txt too large in {source['id']}")
            text = archive.read(exception_member).decode("utf-8-sig")
            for row in csv.DictReader(io.StringIO(text)):
                value = row.get("date", "")
                if len(value) == 8 and value.isdigit():
                    datetime.strptime(value, "%Y%m%d")
                    dates.append(value)
        if not dates:
            raise RefreshError(f"No service dates found in GTFS ZIP for {source['id']}")
        return min(dates), max(dates), attribution_text


def _json_timestamp(data: bytes) -> int | None:
    try:
        value = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise RefreshError("Invalid JSON trip-updates source")

    def scan(item):
        if isinstance(item, dict):
            for key, candidate in item.items():
                if key.casefold() in {"timestamp", "updated_at", "update_time", "retrieved_at"}:
                    if isinstance(candidate, (int, float)):
                        return int(candidate)
                    if isinstance(candidate, str):
                        try:
                            parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
                            return int(parsed.timestamp())
                        except ValueError:
                            pass
                found = scan(candidate)
                if found is not None:
                    return found
        elif isinstance(item, list):
            for candidate in item:
                found = scan(candidate)
                if found is not None:
                    return found
        return None

    return scan(value)


def _utc_datetime(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat().replace("+00:00", "Z")


def _source_record(source: dict, output: Path) -> dict:
    kind = source["kind"]
    limit = MAX_STATIC_BYTES if kind == "static_gtfs" else MAX_REALTIME_BYTES
    record = {
        "id": source["id"],
        "operator": source["operator"],
        "kind": kind,
        "url": source["url"],
        "retrieved_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "geographic_coverage": source["geographic_coverage"],
        "license": source["license"],
        "required": source["required"],
        "status": "available",
    }
    if "limitations" in source:
        record["limitations"] = source["limitations"]
    if "upstream_readme" in source:
        record["upstream_readme"] = source["upstream_readme"]
    try:
        data = download(source["url"], limit)
        record["retrieved_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        filename = f"{source['id']}.zip" if kind == "static_gtfs" else (
            f"{source['id']}.json" if kind.endswith("_json") else f"{source['id']}.pb"
        )
        (output / filename).write_bytes(data)
        record.update({
            "file": filename,
            "sha256": hashlib.sha256(data).hexdigest(),
            "size_bytes": len(data),
        })
        if kind == "static_gtfs":
            start_date, end_date, attribution_text = _validate_gtfs(data, source)
            record["feed_validity"] = {
                "start_date": start_date,
                "end_date": end_date,
                "expired": end_date < datetime.now(timezone.utc).strftime("%Y%m%d"),
            }
            if attribution_text is not None:
                record["attribution_text"] = attribution_text
                attribution_filename = (
                    "attributions.txt" if source["id"] == "ztm-warsaw-static"
                    else f"{source['id']}-attributions.txt"
                )
                (output / attribution_filename).write_text(
                    attribution_text, encoding="utf-8"
                )
        elif kind.endswith("_json"):
            timestamp = _json_timestamp(data)
            record["feed_header_timestamp"] = _utc_datetime(timestamp) if timestamp else None
        else:
            timestamp = feed_header_timestamp(data)
            if timestamp is None:
                raise RefreshError("GTFS-Realtime FeedHeader timestamp is missing")
            record["feed_header_timestamp"] = _utc_datetime(timestamp) if timestamp else None
        if kind != "static_gtfs":
            timestamp = None
            timestamp_text = record.get("feed_header_timestamp")
            if timestamp_text:
                timestamp = int(datetime.fromisoformat(timestamp_text.replace("Z", "+00:00")).timestamp())
            if timestamp is None and kind.endswith("_json"):
                timestamp = _json_timestamp(data)
                if timestamp:
                    record["feed_header_timestamp"] = _utc_datetime(timestamp)
            stale_after = source.get("stale_after_seconds")
            record["freshness"] = (
                "unknown" if timestamp is None else
                "stale" if time.time() - timestamp > stale_after else "fresh"
            )
            record["stale_after_seconds"] = stale_after
            if kind == "gtfs_realtime_vehicle_positions":
                feed_date = (
                    datetime.fromtimestamp(timestamp, timezone.utc).date().isoformat()
                    if timestamp is not None else "unknown"
                )
                record["required_attribution"] = source["attribution_template"].format(
                    feed_header_date=feed_date
                )
        return record
    except Exception as exc:
        if source["required"]:
            raise RefreshError(f"Required source {source['id']} failed: {exc}") from exc
        record.update({"status": "unavailable", "error": str(exc)})
        return record


def refresh(output_dir: Path) -> Path:
    """Publish a complete static snapshot and return its directory."""
    config = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
    sources = config["sources"]
    output_dir = Path(output_dir)
    snapshots = output_dir / "snapshots"
    snapshots.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".staging-", dir=snapshots))
    retrieved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        records = [_source_record(source, staging) for source in sources]
        manifest = {
            "schema_version": 1,
            "source_index_url": config["index_url"],
            "retrieved_at": retrieved_at,
            "sources": records,
        }
        manifest_path = staging / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        snapshot_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
        for path in staging.iterdir():
            path.chmod(0o444)
        staging.chmod(0o555)
        snapshot = snapshots / snapshot_id
        os.replace(staging, snapshot)
        pointer_tmp = output_dir / f".current-{uuid.uuid4().hex}.tmp"
        pointer_tmp.write_text(json.dumps({"snapshot": snapshot_id}) + "\n", encoding="utf-8")
        os.replace(pointer_tmp, output_dir / "current.json")
        return snapshot
    except Exception:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        raise


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="snapshot output directory")
    args = parser.parse_args(argv)
    try:
        snapshot = refresh(args.output)
    except Exception as exc:
        print(f"Refresh failed; current snapshot was not changed: {exc}", file=sys.stderr)
        return 1
    print(snapshot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
