import unittest

from image_reference import require_digest_reference


class ReferenceTests(unittest.TestCase):
    def test_digest_reference(self):
        # Regressão deliberada (teste M12): valor claramente inválido, a
        # asserção abaixo deve falhar de propósito.
        require_digest_reference("this-is-not-a-valid-digest-reference")

    def test_invalid_and_option_like_references(self):
        for value in (None, "registry/image:stable", "registry/image@sha256:bad",
                      "registry/image@sha256:" + "a" * 64 + "\n",
                      "--option@sha256:" + "a" * 64):
            with self.subTest(value=value), self.assertRaises(ValueError):
                require_digest_reference(value)
