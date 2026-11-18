import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from build_graph import OTP_IMAGE, build


class GraphBuildTests(unittest.TestCase):
    def _snapshot(self, root):
        transport = root / "transport"
        snapshot = transport / "snapshots" / "fixture"
        snapshot.mkdir(parents=True)
        files = {
            "mazowieckie.osm.pbf": b"synthetic-pbf",
            "fixture.gtfs.zip": b"synthetic-gtfs",
        }
        sources = []
        for filename, content in files.items():
            (snapshot / filename).write_bytes(content)
            sources.append({
                "id": "osm" if filename.endswith(".pbf") else "fixture",
                "kind": "osm" if filename.endswith(".pbf") else "static-gtfs",
                "sha256": hashlib.sha256(content).hexdigest(),
            })
        (snapshot / "manifest.json").write_text(json.dumps({
            "schema_version": 1,
            "snapshot_id": "fixture",
            "sources": sources,
        }))
        (transport / "current").symlink_to(Path("snapshots") / "fixture")
        return transport

    def test_build_activates_only_after_graph_smoke_passes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            transport = self._snapshot(root)

            def fake_docker(command, **kwargs):
                if "--build" in command:
                    volume = next(arg for arg in command if arg.endswith(":/var/opentripplanner"))
                    Path(volume.split(":", 1)[0], "graph.obj").write_bytes(b"synthetic graph")

            with patch("build_graph.subprocess.run", side_effect=fake_docker), patch("build_graph.smoke_test"):
                manifest = build(transport, root / "routing")

            active = root / "routing" / "active"
            self.assertTrue((active / "graph.obj").is_file())
            self.assertEqual(manifest["otp_image"], OTP_IMAGE)
            self.assertEqual(manifest["transport_snapshot_id"], "fixture")

    def test_failed_build_keeps_previous_active_graph(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            transport = self._snapshot(root)
            routing = root / "routing"
            old = routing / "graphs" / "old"
            old.mkdir(parents=True)
            (old / "graph.obj").write_bytes(b"old graph")
            routing.mkdir(exist_ok=True)
            (routing / "active").symlink_to(Path("graphs") / "old")

            with patch("build_graph.subprocess.run", side_effect=RuntimeError("build failed")):
                with self.assertRaises(RuntimeError):
                    build(transport, routing)

            self.assertEqual((routing / "active").resolve(), old)
            self.assertEqual((old / "graph.obj").read_bytes(), b"old graph")


if __name__ == "__main__":
    unittest.main()
