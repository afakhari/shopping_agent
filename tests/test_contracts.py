"""Dependency-free checks for schema files (not full instance validation)."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMAS = (
    "mission-event.v1.schema.json",
    "contact-result.v1.schema.json",
    "visit-plan.v1.schema.json",
)

class ContractStructureTests(unittest.TestCase):
    def test_schemas_are_valid_json_and_have_required_metadata(self):
        for filename in SCHEMAS:
            with self.subTest(filename=filename):
                obj = json.loads((ROOT / "contracts" / filename).read_text(encoding="utf-8"))
                self.assertEqual(obj["$schema"], "https://json-schema.org/draft/2020-12/schema")
                self.assertEqual(obj["type"], "object")
                self.assertIn("schema_version", obj["required"])
                self.assertEqual(obj["properties"]["schema_version"]["const"], 1)

if __name__ == "__main__":
    unittest.main()
