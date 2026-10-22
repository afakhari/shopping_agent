"""Dependency-free documentation sanity check for the initial planning-only commit."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIRED = [
    "README.md", "AGENTS.md", ".gitignore", ".env.example",
    "docs/PRODUCT.fa.md", "docs/UX.fa.md", "docs/ARCHITECTURE.fa.md",
    "docs/DATA-SEARCH.fa.md", "docs/AGENT.fa.md", "docs/API.fa.md",
    "docs/QUALITY.fa.md", "docs/ROADMAP.fa.md", "docs/REFERENCES.md",
    "docs/IMPORT-BASELINE.fa.md",
]
missing = [name for name in REQUIRED if not (ROOT / name).is_file()]
if missing:
    raise SystemExit("Missing files: " + ", ".join(missing))
print("Blueprint documents present:", len(REQUIRED))
