"""Offline contract tests for the public release smoke command."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from predeploy_smoke import validate_base_url


class PublicURLValidationTests(unittest.TestCase):
    def test_requires_https_and_origin_only(self):
        self.assertEqual(validate_base_url("https://demo.example.com/"), "https://demo.example.com")
        with self.assertRaises(ValueError):
            validate_base_url("http://demo.example.com")
        with self.assertRaises(ValueError):
            validate_base_url("https://demo.example.com/api/v1/")
        with self.assertRaises(ValueError):
            validate_base_url("https://user:password@demo.example.com")
        with self.assertRaises(ValueError):
            validate_base_url("https://demo.example.com/?token=x")

    def test_local_development_is_explicit_only(self):
        self.assertEqual(validate_base_url("http://127.0.0.1:8080", True),
                         "http://127.0.0.1:8080")
        with self.assertRaises(ValueError):
            validate_base_url("http://192.168.1.3:8080", True)


if __name__ == "__main__":
    unittest.main()
