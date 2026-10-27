"""Spot-check: re-download random sections from the official site and compare
them word for word with the stored copies. Exit 1 if any differ.

  python scripts/verify_sample.py --state fl --n 40
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, PoliteFetcher, read_doc  # noqa: E402

WORD = re.compile(r"[A-Za-z0-9]+")
SKIP = {"History", "Note"}


def words(text: str) -> list[str]:
    return [w for w in WORD.findall(text) if w not in SKIP]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default="fl")
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--seed", type=int)
    ap.add_argument("--report")
    args = ap.parse_args()
    rows = [json.loads(l) for l in (ROOT / f"states/{args.state}/statutes/index.jsonl").open()]
    rng = random.Random(args.seed)
    sample = rng.sample(rows, min(args.n, len(rows)))
    fetcher = PoliteFetcher(delay=3.0)
    results, failures = [], 0
    for row in sample:
        meta, body = read_doc(ROOT / row["path"])
        html = fetcher.get(meta["source_url"]).text
        sec = BeautifulSoup(html, "html.parser").find("div", class_="Section")
        official = words(sec.get_text(" ")) if sec else []
        stored = words(body)
        ok = official == stored
        failures += not ok
        item = {"id": row["id"], "ok": ok, "stored_words": len(stored), "official_words": len(official)}
        if not ok:
            for i, (a, b) in enumerate(zip(stored, official)):
                if a != b:
                    item["first_difference"] = {"at_word": i, "stored": stored[i:i + 8], "official": official[i:i + 8]}
                    break
        results.append(item)
        print(("OK  " if ok else "DIFF"), row["id"], item.get("first_difference", ""))
    summary = {"checked": len(results), "matched": len(results) - failures, "results": results}
    if args.report:
        Path(args.report).write_text(json.dumps(summary, indent=2))
    print(f"{summary['matched']}/{summary['checked']} sections match the official text word for word")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
