"""Refuse to commit a suspicious update.

Compares the working tree against HEAD for one collection and aborts (exit 1)
when the change looks like a broken scrape rather than a real change in the law.

Thresholds (per collection):
  * any fetch errors above 2% of requests            -> abort
  * more than 2% of existing files deleted           -> abort
  * more than 15% of existing files changed           -> abort unless --allow-large
  * more than 1% of files (min 25) shrink by over 50% -> abort
Every file that shrank by over 50% is listed in the report for a human to review.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def head_size(path: str) -> int | None:
    try:
        return int(git("cat-file", "-s", f"HEAD:{path}").strip())
    except subprocess.CalledProcessError:
        return None


def check(collection_path: str, summary: dict | None, allow_large: bool) -> dict:
    if summary and summary.get("skipped"):
        return {"collection_path": collection_path, "ok": True, "skipped": summary["skipped"],
                "problems": [], "shrunk_over_half": [], "deleted_files": []}
    if not (ROOT / collection_path).exists():
        return {"collection_path": collection_path, "ok": True, "problems": [],
                "shrunk_over_half": [], "deleted_files": [], "note": "no files yet"}
    git("add", "-A", "--intent-to-add", collection_path)
    existing = [p for p in git("ls-tree", "-r", "--name-only", "HEAD", "--", collection_path).splitlines()
                if p.endswith(".md")]
    n = len(existing)
    status = git("diff", "--name-status", "HEAD", "--", collection_path).splitlines()
    added = [ln.split("\t", 1)[1] for ln in status if ln.startswith("A")]
    deleted = [ln.split("\t", 1)[1] for ln in status if ln.startswith("D")]
    modified = [ln.split("\t", 1)[1] for ln in status if ln.startswith("M")]
    shrunk = []
    for path in modified:
        old = head_size(path)
        new = (ROOT / path).stat().st_size
        if old and new < old * 0.5:
            shrunk.append({"path": path, "old_bytes": old, "new_bytes": new})

    problems = []
    if summary:
        c = summary.get("counts", {})
        reqs = max(c.get("requests", 0), 1)
        if c.get("errors", 0) / reqs > 0.02:
            problems.append(f"fetch errors {c['errors']} of {reqs} requests exceed 2%")
    if n:
        if len(deleted) / n > 0.02:
            problems.append(f"{len(deleted)} of {n} files deleted (over 2%)")
        if (len(modified) + len(deleted)) / n > 0.15 and not allow_large:
            problems.append(f"{len(modified) + len(deleted)} of {n} files changed (over 15%); "
                            "re-run with allow_large if this is a new annual edition")
        if len(shrunk) > max(25, n * 0.01):
            problems.append(f"{len(shrunk)} files shrank by more than half")
    git("reset", "-q", "--", collection_path)
    return {
        "collection_path": collection_path,
        "existing_files": n,
        "added": len(added),
        "modified": len(modified),
        "deleted": len(deleted),
        "shrunk_over_half": shrunk[:100],
        "deleted_files": deleted[:100],
        "ok": not problems,
        "problems": problems,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("collection_path")
    ap.add_argument("--summary", help="scraper JSON summary")
    ap.add_argument("--allow-large", action="store_true")
    ap.add_argument("--report")
    args = ap.parse_args()
    summary = json.loads(Path(args.summary).read_text()) if args.summary and Path(args.summary).exists() else None
    result = check(args.collection_path, summary, args.allow_large)
    text = json.dumps(result, indent=2)
    print(text)
    if args.report:
        Path(args.report).write_text(text)
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
