"""Validate every document: schema, official source, body hash, path, privacy patterns.

Exit code 1 if anything fails. Run in CI on every pull request.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import jsonschema

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, check_source, normalize_body, read_doc, sha256  # noqa: E402

SCHEMA = json.loads((ROOT / "schema/frontmatter.schema.json").read_text())
PII = {
    "possible SSN": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
}
OFFICIAL_EMAIL = json.loads((ROOT / "scripts/allowed_sources.json").read_text()).get("official_email_domains", [])
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[a-z]{2,})\b")


def unofficial_emails(text: str) -> list[str]:
    bad = []
    for m in EMAIL.finditer(text):
        dom = m.group(1).lower()
        if not any(dom == d or dom.endswith("." + d) for d in OFFICIAL_EMAIL):
            bad.append(m.group(0))
    return bad


COLLECTION_TYPE = {"statutes": "statute", "rules": "rule", "opinions": "opinion"}


def validate(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    seen_ids: dict[str, str] = {}
    validator = jsonschema.Draft202012Validator(SCHEMA)
    for path in sorted((root / "states").rglob("*.md")):
        rel = path.relative_to(root).as_posix()
        parts = rel.split("/")
        if len(parts) < 4 or path.name in ("README.md", "CHANGELOG.md"):
            continue
        doc = read_doc(path)
        if doc is None:
            errors.append(f"{rel}: missing or malformed frontmatter")
            continue
        meta, body = doc
        for err in validator.iter_errors(meta):
            errors.append(f"{rel}: schema: {err.message}")
        try:
            check_source(meta.get("source_url", ""))
        except ValueError as exc:
            errors.append(f"{rel}: {exc}")
        if meta.get("jurisdiction") != parts[1]:
            errors.append(f"{rel}: jurisdiction does not match folder")
        if COLLECTION_TYPE.get(parts[2]) != meta.get("type"):
            errors.append(f"{rel}: type does not match folder")
        if sha256(normalize_body(body)) != meta.get("content_sha256"):
            errors.append(f"{rel}: content_sha256 does not match body")
        if not body.strip():
            errors.append(f"{rel}: empty body")
        if meta.get("id") in seen_ids:
            errors.append(f"{rel}: duplicate id (also {seen_ids[meta['id']]})")
        seen_ids[meta.get("id")] = rel
        if unofficial_emails(body):
            errors.append(f"{rel}: email address found ({unofficial_emails(body)[0]}); review before publishing")
        for label, pat in PII.items():
            if pat.search(body):
                errors.append(f"{rel}: {label} found; review before publishing")
    return errors


if __name__ == "__main__":
    errs = validate()
    for e in errs[:500]:
        print("ERROR", e)
    print(f"{len(errs)} problem(s) found")
    sys.exit(1 if errs else 0)
