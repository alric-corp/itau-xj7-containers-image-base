import unittest
from validate_inputs import validate


class InputTests(unittest.TestCase):
    def test_catalog_and_zero_soak(self):
        self.assertEqual(validate('["go1-26","java21"]', {'go1-26', 'java21'}, '0'), ['go1-26', 'java21'])

    def test_malformed_unknown_duplicate_and_injection(self):
        for raw in ('null', '{}', '[]', '"go1-26"', 'invalid', '[1]',
                    '["../go1-26"]', '["go1-26\\n"]', '["$(id)"]',
                    '["go1-26","go1-26"]', '["unknown"]'):
            with self.subTest(raw=raw), self.assertRaises((ValueError, TypeError)):
                validate(raw, {'go1-26', 'java21'})

    def test_invalid_soak(self):
        for soak in ('-1', 'nan', 'inf', '1e999', 'false', '$(id)', ''):
            with self.subTest(soak=soak), self.assertRaises(ValueError):
                validate('["go1-26"]', {'go1-26'}, soak)
