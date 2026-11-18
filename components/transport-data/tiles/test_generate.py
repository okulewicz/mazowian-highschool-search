import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import generate


class TileGenerationTests(unittest.TestCase):
    def test_checksum_mismatch_fails_before_invoking_renderer(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "snapshot.osm.pbf"
            source.write_bytes(b"synthetic snapshot")
            with patch.object(generate.subprocess, "run") as run:
                with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                    generate.run_generation(
                        source,
                        "0" * 64,
                        Path(temporary) / "output",
                        "https://download.geofabrik.de/example",
                        "2026-01-01T00:00:00Z",
                    )
            run.assert_not_called()

    def test_publish_records_checksums_and_switches_current(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "snapshot.osm.pbf"
            source.write_bytes(b"synthetic snapshot")
            checksum = hashlib.sha256(source.read_bytes()).hexdigest()

            def fake_tilemaker(command, check):
                mount = next(
                    argument
                    for argument in command
                    if argument.startswith("type=bind,") and "target=/output" in argument
                )
                output_dir = Path(mount.split("source=", 1)[1].split(",target=", 1)[0])
                output = output_dir / "map.pmtiles"
                with output.open("wb") as tiles:
                    tiles.write(b"PMTiles\x03" + b"synthetic vector tiles")

            with patch.object(generate.subprocess, "run", side_effect=fake_tilemaker):
                manifest = generate.run_generation(
                    source,
                    checksum,
                    Path(temporary) / "artifacts",
                    "https://download.geofabrik.de/example",
                    "2026-01-01T00:00:00Z",
                )

            current = Path(temporary) / "artifacts" / "current"
            self.assertTrue(current.is_symlink())
            version_dir = current.resolve()
            saved_manifest = json.loads(
                (version_dir / "manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(saved_manifest, manifest)
            self.assertEqual(
                saved_manifest["tiles_sha256"],
                hashlib.sha256((version_dir / "map.pmtiles").read_bytes()).hexdigest(),
            )

    def test_renderer_failure_does_not_replace_current(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "snapshot.osm.pbf"
            source.write_bytes(b"synthetic snapshot")
            output = Path(temporary) / "artifacts"
            versions = output / "versions"
            versions.mkdir(parents=True)
            old_version = versions / "known-good"
            old_version.mkdir()
            current = output / "current"
            current.symlink_to(Path("versions") / "known-good")

            with patch.object(
                generate.subprocess,
                "run",
                side_effect=generate.subprocess.CalledProcessError(1, ["docker"]),
            ):
                with self.assertRaises(generate.subprocess.CalledProcessError):
                    generate.run_generation(
                        source,
                        hashlib.sha256(source.read_bytes()).hexdigest(),
                        output,
                        "https://download.geofabrik.de/example",
                        "2026-01-01T00:00:00Z",
                    )
            self.assertEqual(current.resolve(), old_version)
            self.assertEqual(list(versions.iterdir()), [old_version])


if __name__ == "__main__":
    unittest.main()
