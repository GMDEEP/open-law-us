"""Split a Florida rules-of-court PDF into one Markdown file per rule.

The Florida Bar publishes the rules adopted by the Supreme Court of Florida as
PDFs, but its servers refuse automated downloads. So this script works from a
PDF that a person downloaded normally:

  python scripts/fl_rules.py --pdf Family-Law-Rules.pdf --rule-set family-law \
      --source-url https://www-media.floridabar.org/uploads/.../Family-Law-Rules....pdf \
      --as-of 2026-10-01

Only rule text and court-adopted notes are kept. The Bar's cover, table of
contents, index and other editorial matter are dropped.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, today, write_if_changed  # noqa: E402

RULE_SETS = {
    "family-law": ("Fla. Fam. L. R. P.", "Florida Family Law Rules of Procedure"),
    "judicial-admin": ("Fla. R. Gen. Prac. & Jud. Admin.", "Florida Rules of General Practice and Judicial Administration"),
    "civil": ("Fla. R. Civ. P.", "Florida Rules of Civil Procedure"),
    "appellate": ("Fla. R. App. P.", "Florida Rules of Appellate Procedure"),
}
HEADING = re.compile(r"^\s*RULE\s+(\d{1,2}\.\d{3}[a-z]?)\.?\s+(.{3,200})$")
JUNK = [
    re.compile(r"^\s*\d+\s*$"),                                  # bare page numbers
    re.compile(r"^\s*-\s*\d+\s*-\s*$"),
    re.compile(r"©|All rights reserved", re.I),                   # Bar copyright lines
    re.compile(r"^\s*(FAMILY LAW RULES OF PROCEDURE|RULES OF GENERAL PRACTICE AND JUDICIAL ADMINISTRATION)\s*$", re.I),
]
STOP = re.compile(r"^\s*(INDEX|APPENDIX OF FORMS|TABLE OF CONTENTS)\s*$", re.I)


def pdf_lines(path: Path) -> list[str]:
    lines: list[str] = []
    for page in PdfReader(str(path)).pages:
        for ln in (page.extract_text() or "").splitlines():
            if not any(p.search(ln) for p in JUNK):
                lines.append(ln.rstrip())
    return lines


def split_rules(lines: list[str]) -> dict[str, tuple[str, str]]:
    """Return {rule_number: (heading, text)}; keeps the longest occurrence of a
    number, so the table of contents (headings with no text) loses to the body."""
    found: dict[str, tuple[str, str]] = {}
    current, heading, buf = None, "", []

    def flush():
        if current:
            text = "\n".join(buf).strip()
            if len(text) > len(found.get(current, ("", ""))[1]):
                found[current] = (heading, text)

    for ln in lines:
        m = HEADING.match(ln)
        if m:
            flush()
            current, heading, buf = m.group(1), m.group(2).strip().rstrip("."), []
        elif STOP.match(ln) and current:
            flush()
            current, buf = None, []
        elif current:
            buf.append(ln)
    flush()
    return found


def reflow(text: str) -> str:
    """Join hard-wrapped PDF lines into paragraphs; keep (a)/(1) items on new lines."""
    out, para = [], []
    for ln in text.splitlines():
        s = ln.strip()
        if not s:
            if para:
                out.append(" ".join(para))
                para = []
            continue
        if para and re.match(r"^(\([a-zA-Z0-9]{1,4}\)|Committee Note|Commentary|Note)", s):
            out.append(" ".join(para))
            para = []
        para.append(s)
    if para:
        out.append(" ".join(para))
    return "\n\n".join(re.sub(r"\s+", " ", p) for p in out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--rule-set", required=True, choices=RULE_SETS)
    ap.add_argument("--source-url", required=True)
    ap.add_argument("--as-of", required=True, help="edition date printed on the PDF, YYYY-MM-DD")
    ap.add_argument("--summary")
    args = ap.parse_args()

    cite_prefix, set_name = RULE_SETS[args.rule_set]
    rules = split_rules(pdf_lines(Path(args.pdf)))
    counts = {"added": 0, "changed": 0, "unchanged": 0, "errors": 0, "requests": 0, "rules": len(rules)}
    for number, (heading, raw) in sorted(rules.items(), key=lambda kv: [int(x) for x in re.findall(r"\d+", kv[0])]):
        meta = {
            "id": f"fl/rules/{args.rule_set}-{number}",
            "jurisdiction": "fl",
            "type": "rule",
            "citation": f"{cite_prefix} {number}",
            "heading": heading.title() if heading.isupper() else heading,
            "section": number,
            "rule_set": set_name,
            "edition": args.as_of,
            "source_url": args.source_url,
            "source_name": "Rules adopted by the Supreme Court of Florida (compiled by The Florida Bar)",
            "official": False,
            "retrieved_at": today(),
            "content_sha256": "",
            "status": "active",
        }
        rel = f"states/fl/rules/{args.rule_set}/{number}.md"
        counts[write_if_changed(ROOT / rel, meta, reflow(raw))] += 1
    result = {"collection": "fl-rules", "rule_set": args.rule_set, "counts": counts}
    print(json.dumps(result, indent=2))
    if args.summary:
        Path(args.summary).write_text(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
