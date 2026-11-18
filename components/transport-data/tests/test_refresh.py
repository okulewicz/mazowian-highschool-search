import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

COMPONENT_DIR = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("transport_refresh", COMPONENT_DIR / "refresh.py")
refresh_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(refresh_module)

ATTRIBUTIONS = (
    "ZTM Warszawa\nMikołaj Kuranowski\nOpenStreetMap contributors\n"
)


def static_feed(attributions=ATTRIBUTIONS, unsafe_path=None):
    buffer = __import__("io").BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for filename in (
            "agency.txt",
            "routes.txt",
            "stops.txt",
            "trips.txt",
            "stop_times.txt",
        ):
            archive.writestr(filename, "id\nexample\n")
        archive.writestr(
            "calendar.txt",
            "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\n"
            "s,1,1,1,1,1,0,0,20260101,20261231\n",
        )
        if attributions is not None:
            archive.writestr("attributions.txt", attributions)
        if unsafe_path:
            archive.writestr(unsafe_path, "unsafe")
    return buffer.getvalue()


def gtfs_realtime_feed(timestamp):
    def varint(value):
        result = bytearray()
        while value > 0x7F:
            result.append((value & 0x7F) | 0x80)
            value >>= 7
        result.append(value)
        return bytes(result)

    header = b"\x0a\x01\x32\x18" + varint(timestamp)
    return b"\x0a" + varint(len(header)) + header


class RefreshTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.config_path = self.root / "sources.json"
        self.output = self.root / "output"
        self.sources = [
            {
                "id": "ztm-warsaw-static",
                "operator": "ZTM Warszawa",
                "kind": "static_gtfs",
                "url": "https://mkuran.pl/gtfs/warsaw.zip",
                "geographic_coverage": "Warsaw metropolitan area",
                "required": True,
                "license": ["ZTM terms", "ODbL bus shapes"],
                "attribution_file": "attributions.txt",
                "required_attributions": [
                    "ZTM Warszawa",
                    "Mikołaj Kuranowski",
                    "OpenStreetMap contributors",
                ],
            },
            {
                "id": "warsaw-vehicles",
                "operator": "Miasto Stołeczne Warszawa",
                "kind": "gtfs_realtime_vehicle_positions",
                "url": "https://mkuran.pl/gtfs/warsaw/vehicles.pb",
                "geographic_coverage": "Warsaw metropolitan area",
                "required": False,
                "license": ["Warsaw Open Data Project Usage Terms"],
                "stale_after_seconds": 900,
                "attribution_template": (
                    "Miasto Stołeczne Warszawa. Download date: {feed_header_date}. "
                    "http://api.um.warszawa.pl"
                ),
                "limitations": ["Some trip_id values may not match static GTFS."],
            },
            {
                "id": "polish-updates-json",
                "operator": "Polish Trains",
                "kind": "realtime_trip_updates_json",
                "url": "https://mkuran.pl/gtfs/polish_trains/updates.json",
                "geographic_coverage": "Poland",
                "required": False,
                "license": ["CC BY 4.0", "PKP PLK terms"],
                "stale_after_seconds": 3600,
            },
        ]
        self.config_path.write_text(
            json.dumps({"schema_version": 1, "index_url": "https://mkuran.pl/gtfs/",
                        "sources": self.sources}),
            encoding="utf-8",
        )
        self.config_patcher = patch.object(refresh_module, "SOURCES_FILE", self.config_path)
        self.config_patcher.start()
        self.addCleanup(self.config_patcher.stop)

    def mock_downloads(self, **overrides):
        now = int(refresh_module.time.time())
        payloads = {
            self.sources[0]["url"]: static_feed(),
            self.sources[1]["url"]: gtfs_realtime_feed(now),
            self.sources[2]["url"]: json.dumps({"timestamp": now - 7200}).encode(),
        }
        payloads.update(overrides)

        def fake_download(url, _max_bytes):
            payload = payloads[url]
            if isinstance(payload, Exception):
                raise payload
            return payload

        return patch.object(refresh_module, "download", side_effect=fake_download)

    def test_publishes_separate_static_and_realtime_files_with_attribution(self):
        with self.mock_downloads():
            snapshot = refresh_module.refresh(self.output)

        manifest = json.loads((snapshot / "manifest.json").read_text(encoding="utf-8"))
        records = {record["id"]: record for record in manifest["sources"]}
        static = records["ztm-warsaw-static"]
        vehicle = records["warsaw-vehicles"]
        updates = records["polish-updates-json"]

        self.assertEqual(static["kind"], "static_gtfs")
        self.assertEqual(static["feed_validity"], {
            "start_date": "20260101", "end_date": "20261231", "expired": False
        })
        self.assertEqual(static["attribution_text"], ATTRIBUTIONS)
        self.assertEqual((snapshot / "attributions.txt").read_text(), ATTRIBUTIONS)
        self.assertTrue((snapshot / "ztm-warsaw-static.zip").is_file())
        self.assertTrue((snapshot / "warsaw-vehicles.pb").is_file())
        self.assertTrue((snapshot / "polish-updates-json.json").is_file())
        self.assertEqual(vehicle["freshness"], "fresh")
        self.assertIn("Miasto Stołeczne Warszawa", vehicle["required_attribution"])
        self.assertIn("http://api.um.warszawa.pl", vehicle["required_attribution"])
        self.assertIn("trip_id values may not match", vehicle["limitations"][0])
        self.assertEqual(updates["freshness"], "stale")

    def test_unavailable_realtime_does_not_prevent_static_snapshot(self):
        with self.mock_downloads(**{
            self.sources[1]["url"]: refresh_module.RefreshError("offline")
        }):
            snapshot = refresh_module.refresh(self.output)
        manifest = json.loads((snapshot / "manifest.json").read_text(encoding="utf-8"))
        records = {record["id"]: record for record in manifest["sources"]}
        self.assertEqual(records["ztm-warsaw-static"]["status"], "available")
        self.assertEqual(records["warsaw-vehicles"]["status"], "unavailable")

    def test_required_source_failure_preserves_current_snapshot(self):
        with self.mock_downloads():
            previous = refresh_module.refresh(self.output)
        current_before = (self.output / "current.json").read_text(encoding="utf-8")

        with self.mock_downloads(**{
            self.sources[0]["url"]: refresh_module.RefreshError("offline")
        }):
            with self.assertRaises(refresh_module.RefreshError):
                refresh_module.refresh(self.output)

        self.assertEqual((self.output / "current.json").read_text(encoding="utf-8"),
                         current_before)
        self.assertTrue(previous.is_dir())

    def test_corrupt_and_unsafe_static_archives_are_rejected(self):
        source = self.sources[0]
        with self.assertRaises(refresh_module.RefreshError):
            refresh_module._validate_gtfs(b"not a zip", source)
        with self.assertRaises(refresh_module.RefreshError):
            refresh_module._validate_gtfs(static_feed(unsafe_path="../outside.txt"), source)

    def test_rejects_non_allowlisted_urls(self):
        for url in (
            "http://mkuran.pl/gtfs/warsaw.zip",
            "https://example.com/feed.zip",
            "https://user@mkuran.pl/gtfs/warsaw.zip",
        ):
            with self.subTest(url=url), self.assertRaises(refresh_module.RefreshError):
                refresh_module._validate_url(url)

    def test_vehicle_attribution_uses_feed_header_date(self):
        timestamp = 1_767_225_600
        self.assertEqual(
            refresh_module.feed_header_timestamp(gtfs_realtime_feed(timestamp)),
            timestamp,
        )
        self.assertEqual(
            refresh_module._utc_datetime(timestamp),
            "2026-01-01T00:00:00Z",
        )

    def test_source_configuration_keeps_all_feeds_separate(self):
        config = json.loads(
            (COMPONENT_DIR / "sources.json").read_text(encoding="utf-8")
        )
        records = config["sources"]
        self.assertEqual(len(records), 8)
        self.assertEqual(len({record["id"] for record in records}), len(records))
        self.assertEqual(
            {record["kind"] for record in records if record["required"]},
            {"static_gtfs"},
        )
        polish_static = next(
            record for record in records if record["id"] == "polish-trains-static"
        )
        self.assertIn("PKP PLK public sector data usage terms (Polish)",
                      polish_static["license"])
        self.assertIn("Mikołaj Kuranowski", polish_static["required_attributions"])
        self.assertTrue(polish_static["upstream_readme"].endswith("/README.md"))
        self.assertTrue(all(
            record["url"].startswith("https://mkuran.pl/gtfs/")
            for record in records
        ))


if __name__ == "__main__":
    unittest.main()
