import csv
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from refresh import refresh


def fixture_gtfs():
    files = {
        "agency.txt": [["agency_id", "agency_name"], ["a", "fixture"]],
        "stops.txt": [["stop_id", "stop_name", "stop_lat", "stop_lon"], ["s1", "one", "52", "21"]],
        "routes.txt": [["route_id", "agency_id", "route_type"], ["r1", "a", "3"]],
        "trips.txt": [["route_id", "service_id", "trip_id"], ["r1", "wk", "t1"]],
        "stop_times.txt": [["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"], ["t1", "08:00:00", "08:00:00", "s1", "1"]],
        "calendar.txt": [["service_id"], ["wk"]],
    }
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name, rows in files.items():
            text = io.StringIO()
            csv.writer(text).writerows(rows)
            archive.writestr(name, text.getvalue())
    return output.getvalue()


class RefreshTests(unittest.TestCase):
    def test_publishes_manifest_with_checksums(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = root / "sources.json"
            config.write_text(json.dumps({
                "schema_version": 1,
                "osm": {"id": "osm", "url": "https://download.geofabrik.de/test.pbf", "license": "ODbL", "attribution": "OSM"},
                "gtfs": [{"id": "fixture", "url": "https://mkuran.pl/fixture.zip", "license": "CC0", "attribution": "fixture"}],
            }))

            def downloader(url, destination, maximum):
                content = b"\x00\x00\x00\x0b\x0a\x09OSMHeader" if url.endswith(".pbf") else fixture_gtfs()
                destination.write_bytes(content)
                import hashlib
                return {"source_url": url, "final_url": url, "retrieved_at": "2026-01-01T00:00:00+00:00",
                        "size_bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}

            manifest = refresh(config, root / "published", downloader)
            current = root / "published" / "current"
            self.assertEqual(json.loads((current / "manifest.json").read_text())["snapshot_id"], manifest["snapshot_id"])
            self.assertEqual(len(manifest["sources"]), 2)

    def test_failed_refresh_keeps_current_pointer(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = root / "sources.json"
            config.write_text(json.dumps({
                "schema_version": 1,
                "osm": {"id": "osm", "url": "https://download.geofabrik.de/test.pbf", "license": "ODbL", "attribution": "OSM"},
                "gtfs": [{"id": "fixture", "url": "https://mkuran.pl/fixture.zip", "license": "CC0", "attribution": "fixture"}],
            }))
            destination = root / "published"

            def good(url, path, maximum):
                content = b"\x00\x00\x00\x0b\x0a\x09OSMHeader" if url.endswith(".pbf") else fixture_gtfs()
                path.write_bytes(content)
                import hashlib
                return {"source_url": url, "final_url": url, "retrieved_at": "now", "size_bytes": len(content),
                        "sha256": hashlib.sha256(content).hexdigest()}

            refresh(config, destination, good)
            old_target = (destination / "current").resolve()

            def fail(url, path, maximum):
                if url.endswith(".pbf"):
                    path.write_bytes(b"bad")
                else:
                    raise OSError("fixture failure")
                import hashlib
                content = path.read_bytes()
                return {"source_url": url, "final_url": url, "retrieved_at": "now", "size_bytes": len(content),
                        "sha256": hashlib.sha256(content).hexdigest()}

            with self.assertRaises((ValueError, OSError)):
                refresh(config, destination, fail)
            self.assertEqual((destination / "current").resolve(), old_target)


if __name__ == "__main__":
    unittest.main()
