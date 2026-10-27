"""Write the run log, append the changelog, and produce the pull-request body.

Usage: python scripts/record_run.py --state fl --summaries a.json b.json --guards g1.json \
           --run-id 123 --pr-body pr.md
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load(paths):
    out = []
    for p in paths or []:
        path = Path(p)
        if path.exists():
            out.append(json.loads(path.read_text()))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--summaries", nargs="*")
    ap.add_argument("--guards", nargs="*")
    ap.add_argument("--run-id", default="local")
    ap.add_argument("--pr-body")
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    summaries, guards = load(args.summaries), load(args.guards)
    log = {"run_id": args.run_id, "finished_at": now.isoformat(timespec="seconds"),
           "state": args.state, "collections": summaries, "guards": guards}
    runs = ROOT / "runs"
    runs.mkdir(exist_ok=True)
    (runs / f"{now:%Y-%m-%d}-{args.state}-{args.run_id}.json").write_text(json.dumps(log, indent=2) + "\n")

    lines, changed_any = [], False
    for s in summaries:
        c = s.get("counts", {})
        if s.get("skipped"):
            lines.append(f"- **{s['collection']}**: skipped ({s['skipped']})")
            continue
        delta = c.get("added", 0) + c.get("changed", 0) + c.get("removed", 0)
        changed_any |= delta > 0
        lines.append(f"- **{s['collection']}**: {c.get('added', 0)} added, {c.get('changed', 0)} changed, "
                     f"{c.get('removed', 0)} removed, {c.get('unchanged', 0)} unchanged "
                     f"({c.get('requests', 0)} requests, {c.get('errors', 0)} errors)")
    if changed_any:
        cl = ROOT / "states" / args.state / "CHANGELOG.md"
        cl.write_text(cl.read_text().rstrip() + f"\n\n## {now:%Y-%m-%d}\n\n" + "\n".join(lines) + "\n")

    if args.pr_body:
        body = [f"Automated weekly update for **{args.state.upper()}**, run `{args.run_id}`.", ""]
        body += lines + [""]
        for g in guards:
            body.append(f"Safety checks for `{g['collection_path']}`: "
                        f"{'passed' if g['ok'] else 'FAILED'}.")
            if g.get("shrunk_over_half"):
                body.append("Files that shrank by more than half (please review):")
                body += [f"- `{x['path']}` ({x['old_bytes']} → {x['new_bytes']} bytes)"
                         for x in g["shrunk_over_half"][:30]]
            if g.get("deleted_files"):
                body.append("Deleted files:")
                body += [f"- `{p}`" for p in g["deleted_files"][:30]]
        body += ["", "Review the changes, spot-check a few files against their `source_url`, then approve and merge.",
                 "", "_Unofficial copy; not legal advice._"]
        Path(args.pr_body).write_text("\n".join(body) + "\n")
    print("\n".join(lines))
    print("CHANGED" if changed_any else "NO_CHANGES")


if __name__ == "__main__":
    main()
