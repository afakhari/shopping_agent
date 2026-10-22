#!/usr/bin/env python3
"""Safely import this extracted local baseline into the already-created GitHub repo.

This script intentionally never force-pushes, never changes main directly, and
keeps the new repository's current product blueprints. Requires locally
installed Git with GitHub authentication for --push.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = "https://github.com/afakhari/shopping_agent.git"
BRANCH = "bootstrap/import-existing-code"
BLOCK_PARTS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", "dist", "build", ".next", ".idea", ".vscode"}
BLOCK_SUFFIXES = {".pem", ".p12", ".pfx", ".key", ".sqlite3", ".db", ".dump", ".zip", ".csv", ".log"}
ROOT_EXCLUSIONS = {"AGENTS.md", "README.md", "CONTRIBUTING.md", ".gitignore", ".env.example", "LICENSE"}
BLOCKED_FILE = re.compile(r"^(\.env(?!\.example$)|id_rsa|id_ed25519)$", flags=re.I)
SUSPECT_CONTENT = re.compile(rb"(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{32,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)")


def run(*args: str, cwd: Path | None = None) -> None:
    try:
        subprocess.run(args, cwd=cwd, check=True)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"Git operation failed (exit {exc.returncode}): {' '.join(args)}") from exc


def select_files() -> list[tuple[Path, Path]]:
    mapping: list[tuple[Path, Path]] = []
    for src in sorted(ROOT.rglob("*")):
        if not src.is_file():
            continue
        rel = src.relative_to(ROOT)
        if any(part in BLOCK_PARTS for part in rel.parts):
            continue
        if any(part.lower() in {"data", ".secrets", "private"} for part in rel.parts):
            continue
        if BLOCKED_FILE.match(src.name) or src.suffix.lower() in BLOCK_SUFFIXES:
            continue
        if src.name in ROOT_EXCLUSIONS and len(rel.parts) == 1:
            continue
        if rel.parts[0] == "docs":
            # Preserve both generations of documentation without Windows case-collisions.
            dest = Path("docs/legacy-baseline") / Path(*rel.parts[1:])
        elif rel.parts[0] == ".github" and rel.as_posix() in {".github/pull_request_template.md", ".github/ISSUE_TEMPLATE/feature.md"}:
            continue
        elif rel.parts[0] == "scripts" and rel.name == "publish-new-repo.sh":
            continue
        elif rel.name.startswith("APPLY-") or rel.name in {"FIX-INSTRUCTIONS.fa.md", "DESIGN-SYSTEM-APPLY.fa.md", "UX-UI-UPDATE-INSTRUCTIONS.fa.md"}:
            continue
        else:
            dest = rel
        if SUSPECT_CONTENT.search(src.read_bytes()):
            raise SystemExit(f"Potential secret detected in {rel}; audit locally before publishing.")
        mapping.append((src, dest))
    return mapping


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a safe feature branch in afakhari/shopping_agent")
    parser.add_argument("--push", action="store_true", help="Clone, import, commit and push a branch; never force-push or modify main")
    args = parser.parse_args()
    mapping = select_files()
    print(f"Prepared {len(mapping)} files for sanitized source import; default is dry-run.")
    print("Source files:", sum(dest.parts[0] in {"backend", "frontend"} for _, dest in mapping))
    print("Legacy documentation:", sum(dest.parts[:2] == ("docs", "legacy-baseline") for _, dest in mapping))
    if not args.push:
        print("Dry run complete. Run with --push on a Git-authenticated machine to publish branch.")
        return
    if shutil.which("git") is None:
        raise SystemExit("Git is not installed or not in PATH.")
    with tempfile.TemporaryDirectory(prefix="bazaar-github-") as tmp:
        target = Path(tmp) / "shopping_agent"
        run("git", "clone", REPO, str(target))
        run("git", "switch", "-c", BRANCH, cwd=target)
        for src, rel in mapping:
            dest = target / rel
            if dest.exists():
                raise SystemExit(f"Refusing to overwrite an existing remote file: {rel}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
        # IMPORTANT ON WINDOWS: Never run "git -c core.autocrlf=false add -A".
        # A clone made with core.autocrlf=true has CRLF working-tree copies of
        # existing tracked files. Restaging them with autocrlf=false would make
        # ordinary CRLF appear as ^M trailing whitespace in the index.
        # Instead, stage ONLY the files we copied. Normalize staged new files using input conversion without
        # re-staging cloned CRLF tracked files, leaving remote tracked files
        # (including .env.example and issue templates) untouched.
        imported = [rel.as_posix() for _, rel in mapping]
        for offset in range(0, len(imported), 24):
            run("git", "-c", "core.autocrlf=input", "add", "--", *imported[offset:offset + 24], cwd=target)
        run("git", "diff", "--cached", "--check", cwd=target)
        # Ensure we have not accidentally staged an unrelated tracked file.
        staged = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only", "-z"], cwd=target
        ).decode("utf-8", errors="surrogateescape").strip("\0").split("\0")
        extra = set(staged) - set(imported)
        if extra:
            raise SystemExit(f"Refusing unexpected staged files: {sorted(extra)}")
        print("Review changed files before final push:")
        run("git", "diff", "--cached", "--stat", cwd=target)
        run("git", "commit", "-m", "chore: import sanitized Bazaar Compass application baseline", cwd=target)
        run("git", "push", "-u", "origin", BRANCH, cwd=target)
        print("Branch pushed. Create a PR at:")
        print("https://github.com/afakhari/shopping_agent/compare/main...bootstrap/import-existing-code?expand=1")
        print("Merge only after CI and secret review; main was not modified.")


if __name__ == "__main__":
    main()
