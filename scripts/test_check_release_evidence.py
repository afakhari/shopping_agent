"""Release-gate missing evidence must never be counted as a pass."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_release_evidence import assess_release


class ReleaseEvidenceTests(unittest.TestCase):
    def test_empty_manifest_is_blocked(self):
        failures = assess_release({"checks": [], "other_gates": []})
        self.assertTrue(failures)
        self.assertTrue(any("20 unique" in issue for issue in failures))

    def test_no_video_blocks_even_with_ci(self):
        matrix = {"git_sha": "a" * 40, "production_url": "https://demo.example.org",
                  "ci_url": "https://github.com/example/actions/1",
                  "demo_video_url": None, "checks": [], "other_gates": []}
        self.assertTrue(any("demo_video_url" in issue for issue in assess_release(matrix)))


if __name__ == "__main__":
    unittest.main()
