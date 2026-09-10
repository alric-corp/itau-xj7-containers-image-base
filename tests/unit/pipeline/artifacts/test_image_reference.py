import unittest

from scripts.pipeline.artifacts.image_reference import require_digest_reference


class ReferenceTests(unittest.TestCase):
    def test_digest_reference(self):
        require_digest_reference("registry.example:5000/team/image@sha256:" + "a" * 64)

    def test_invalid_and_option_like_references(self):
        for value in (None, "registry/image:stable", "registry/image@sha256:bad",
                      "registry/image@sha256:" + "a" * 64 + "\n",
                      "--option@sha256:" + "a" * 64):
            with self.subTest(value=value), self.assertRaises(ValueError):
                require_digest_reference(value)
