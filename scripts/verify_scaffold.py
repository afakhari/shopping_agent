"""Static validation for the repository scaffold (not a substitute for runtime tests)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "backend/manage.py",
    "backend/config/settings/base.py",
    "backend/config/settings/local.py",
    "backend/config/settings/production.py",
    "backend/apps/health/views.py",
    "backend/apps/health/tests.py",
    "backend/apps/catalog/models.py",
    "backend/apps/catalog/management/commands/import_dataset.py",
    "backend/apps/catalog/migrations/0003_shop_in_person_credit_flag.py",
    "backend/apps/search/services.py",
    "backend/apps/search/tests/test_search_api.py",
    "backend/apps/missions/views.py",
    "backend/apps/missions/services.py",
    "backend/apps/missions/tests.py",
    "backend/apps/agent/graph.py",
    "backend/apps/agent/llm.py",
    "frontend/package.json",
    "frontend/src/features/search/catalog-api.ts",
    "frontend/src/features/missions/MissionPanel.tsx",
    "frontend/src/features/missions/mission-api.ts",
    "frontend/src/main.tsx",
    "frontend/src/app/App.tsx",
    "frontend/src/shared/lib/persian-normalize.test.ts",
    "frontend/vite.config.ts",
    "compose.yaml",
    "frontend/nginx/default.conf",
    "docs/legacy-baseline/import-and-search.fa.md",
    "docs/legacy-baseline/api-contract.fa.md",
    "docs/legacy-baseline/agent-and-genui.fa.md",
    "docs/legacy-baseline/index.fa.md",
    "docs/legacy-baseline/implementation-status.fa.md",
    "docs/legacy-baseline/windows-setup-and-verification.fa.md",
    "scripts/audit_dataset.py",
    "scripts/verify-local.ps1",
    "docs/legacy-baseline/dataset-audit-snapshot.fa.md",
]
missing = [item for item in REQUIRED if not (ROOT / item).is_file()]
if missing:
    raise SystemExit("Missing required scaffold files:\n- " + "\n- ".join(missing))

package = json.loads((ROOT / "frontend/package.json").read_text(encoding="utf-8"))
all_dependencies = {**package.get("dependencies", {}), **package.get("devDependencies", {})}
unpinned = [
    name for name, version in all_dependencies.items()
    if not version or version[0] in "^~><*"
]
if unpinned:
    raise SystemExit("Direct frontend dependencies must be exact pins: " + ", ".join(unpinned))

print(f"Static scaffold validation passed: {len(REQUIRED)} required paths exist.")
print(f"Frontend direct dependencies pinned exactly: {len(all_dependencies)}.")
if not (ROOT / "frontend/package-lock.json").exists():
    print("WARNING: package-lock.json is missing; registry access is required to generate it.")
print(
    "Note: Django checks, pytest, npm lint/typecheck/test/build and Docker checks "
    "require dependencies/runtime not provided by this validation."
)
