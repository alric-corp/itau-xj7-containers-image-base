import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from oci_artifact import INDEX, MANIFEST, platform_view, prepare, verify


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "blobs/sha256").mkdir(parents=True)
        self.entries = []
        for arch in ("amd64", "arm64"):
            config = self.store({"os": "linux", "architecture": arch})
            layer = self.store({"payload": arch})
            manifest = self.store({"schemaVersion": 2, "mediaType": MANIFEST,
                                   "config": config, "layers": [layer]})
            manifest.update(mediaType=MANIFEST, platform={"os": "linux", "architecture": arch})
            self.entries.append(manifest)
        self.write_index()

    def store(self, document):
        raw = json.dumps(document).encode()
        digest = hashlib.sha256(raw).hexdigest()
        (self.root / "blobs/sha256" / digest).write_bytes(raw)
        return {"size": len(raw), "digest": "sha256:" + digest}

    def write_index(self):
        (self.root / "index.json").write_text(json.dumps({"schemaVersion": 2, "mediaType": INDEX,
                                                       "manifests": self.entries}))

    def test_published_index_digest_is_the_original_apko_index(self):
        expected = "sha256:" + hashlib.sha256((self.root / "index.json").read_bytes()).hexdigest()
        result = prepare(self.root)
        self.assertEqual(result["digest"], expected)
        self.assertEqual(verify(self.root), result)
        self.assertEqual(set(result["platforms"]), {"linux/amd64", "linux/arm64"})

    def test_missing_architecture_is_rejected(self):
        self.entries.pop()
        self.write_index()
        with self.assertRaises(ValueError):
            prepare(self.root)

    def test_scan_view_contains_only_requested_platform(self):
        prepare(self.root)
        with tempfile.TemporaryDirectory() as view:
            platform_view(self.root, "arm64", view)
            entries = json.loads((Path(view) / "index.json").read_text())["manifests"]
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["platform"]["architecture"], "arm64")
            self.assertEqual((Path(view) / "blobs").resolve(), (self.root / "blobs").resolve())

    def test_duplicate_platform_is_rejected(self):
        self.entries[1]["platform"] = self.entries[0]["platform"]
        self.write_index()
        with self.assertRaises(ValueError):
            prepare(self.root)

    def test_platform_variant_is_accepted_by_verifier_and_scanner_view(self):
        self.entries[1]["platform"]["variant"] = "v8"
        self.write_index()
        prepare(self.root)
        with tempfile.TemporaryDirectory() as view:
            platform_view(self.root, "arm64", view)
            entries = json.loads((Path(view) / "index.json").read_text())["manifests"]
            self.assertEqual(entries, [self.entries[1]])

    def test_both_readers_reject_invalid_wrapper(self):
        prepare(self.root)
        root = json.loads((self.root / "index.json").read_text())
        root["manifests"].append(root["manifests"][0])
        (self.root / "index.json").write_text(json.dumps(root))
        with self.assertRaises(ValueError):
            verify(self.root)
        with tempfile.TemporaryDirectory() as view, self.assertRaises(ValueError):
            platform_view(self.root, "arm64", view)

    def test_tampered_manifest_is_rejected(self):
        prepare(self.root)
        path = self.root / "blobs/sha256" / self.entries[0]["digest"].split(":")[1]
        path.write_text("tampered")
        with self.assertRaises(ValueError):
            verify(self.root)

    def test_missing_layer_is_rejected(self):
        prepare(self.root)
        path = self.root / "blobs/sha256" / self.entries[0]["digest"].split(":")[1]
        layer = json.loads(path.read_text())["layers"][0]
        (self.root / "blobs/sha256" / layer["digest"].split(":")[1]).unlink()
        with self.assertRaises(FileNotFoundError):
            verify(self.root)


if __name__ == "__main__":
    unittest.main()
