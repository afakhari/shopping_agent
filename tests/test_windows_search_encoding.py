"""Guard Windows PowerShell 5.1 scripts against ANSI-vs-UTF-8 mojibake."""
from pathlib import Path
import unittest
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]


class WindowsSearchEncodingTest(unittest.TestCase):
    def test_default_query_percent_encoding(self):
        self.assertEqual(quote("\u0647\u062f\u0641\u0648\u0646"), "%D9%87%D8%AF%D9%81%D9%88%D9%86")

    def test_powershell_scripts_do_not_embed_non_ascii_strings(self):
        # PowerShell 5.1 treats .ps1 UTF-8 without BOM as an ANSI codepage.
        for path in ("scripts/setup-dataset.ps1", "scripts/diagnose-search.ps1"):
            with self.subTest(path=path):
                content = (ROOT / path).read_text(encoding="utf-8")
                self.assertTrue(content.isascii())
                self.assertIn("%D9%87%D8%AF%D9%81%D9%88%D9%86", content)

    def test_default_diagnostic_query_stays_in_linux_python(self):
        content = (ROOT / "scripts/diagnose-search.ps1").read_text(encoding="utf-8")
        self.assertIn("param([string]$Query = ''", content)
        self.assertIn("docker compose exec -T backend python manage.py diagnose_search\n", content)


if __name__ == "__main__":
    unittest.main()
