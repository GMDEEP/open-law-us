"""Fetch Florida family-law appellate opinions from the CourtListener API (v4).

Requires a free CourtListener API token in COURTLISTENER_TOKEN. Without one the
script records "skipped: token missing" and exits 0, so the weekly run still
finishes cleanly.

Free accounts are rate-limited (about 5 requests a minute, 50 an hour and 125 a
day), so requests are spaced 75 seconds apart and each run uses a fixed request
budget (default 45, under the hourly limit): newly filed opinions first, then a slice of the
backlog, going back in time. Progress is kept in states/fl/opinions/_state.json.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlencode

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, FetchError, PoliteFetcher, today, write_if_changed  # noqa: E402

API = "https://www.courtlistener.com/api/rest/v4"
COURTS = {"fla": "Supreme Court of Florida", "fladistctapp": "District Court of Appeal of Florida"}
QUERY = ('("dissolution of marriage" OR "parenting plan" OR "time-sharing" OR "timesharing" '
         'OR "child support" OR "alimony" OR "equitable distribution" OR "relocation" '
         'OR "paternity" OR "chapter 61")')
TOPICS = {
    "dissolution": r"dissolution of marriage",
    "parenting-plan": r"parenting plan",
    "time-sharing": r"time-?sharing",
    "child-support": r"child support",
    "alimony": r"\balimony\b",
    "equitable-distribution": r"equitable distribution",
    "relocation": r"\brelocat",
    "paternity": r"\bpaternity\b",
    "domestic-violence": r"domestic violence|injunction for protection",
}
RULE_QUERY = '(caseName:("In re: Amendments" OR "In re Amendments") AND (rule OR rules))'
# Each profile: (state key, courts, query, extra topic tag, share of the run's request budget)
PROFILES = [
    ("family", list(COURTS), QUERY, None, 0.6),
    ("rule-amendments", ["fla"], RULE_QUERY, "rule-amendment", 0.4),
]
STATE_PATH = ROOT / "states/fl/opinions/_state.json"


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "opinion"


def opinion_text(op: dict) -> str:
    if op.get("plain_text"):
        return op["plain_text"]
    for field in ("html_with_citations", "html", "html_lawbox", "html_columbia", "xml_harvard"):
        if op.get(field):
            return BeautifulSoup(op[field], "html.parser").get_text("\n")
    return ""


def tags_for(text: str) -> list[str]:
    low = text.lower()
    return [t for t, pat in TOPICS.items() if re.search(pat, low)]


def cited_statutes(text: str) -> list[str]:
    found = re.findall(r"(?:§+|[Ss]ection)\s*(\d{1,4}\.\d{2,6})", text)
    return sorted(set(found), key=lambda s: [int(p) for p in s.split(".")])[:100]


def search_url(court: str, filed_after: str | None, filed_before: str | None, query: str = QUERY) -> str:
    params = {"type": "o", "court": court, "q": query, "order_by": "dateFiled desc",
              "stat_Published": "on"}
    if filed_after:
        params["filed_after"] = filed_after
    if filed_before:
        params["filed_before"] = filed_before
    return f"{API}/search/?{urlencode(params)}"


def run(budget: int) -> dict:
    token = os.environ.get("COURTLISTENER_TOKEN", "").strip()
    if not token:
        return {"collection": "fl-opinions", "skipped": "token missing (add COURTLISTENER_TOKEN secret)",
                "counts": {"requests": 0, "errors": 0}}
    state = json.loads(STATE_PATH.read_text()) if STATE_PATH.exists() else {}
    fetcher = PoliteFetcher(delay=75.0, retries=4)
    headers = {"Authorization": f"Token {token}"}
    counts = {"added": 0, "changed": 0, "unchanged": 0, "errors": 0, "requests": 0}
    errors: list[str] = []

    def get_json(url: str):
        if fetcher.count >= budget:
            raise StopIteration
        return fetcher.get(url, headers=headers).json()

    try:
        for pname, courts, query, extra_tag, share in PROFILES:
            pstate = state.setdefault(pname, {})
            limit = fetcher.count + max(int(budget * share), 1)
            for court in courts:
                cstate = pstate.setdefault(court, {})
                passes = [("new", cstate.get("newest"), None), ("backlog", None, cstate.get("oldest"))]
                for kind, after, before in passes:
                    if kind == "backlog" and cstate.get("backlog_done"):
                        continue
                    if fetcher.count >= limit:
                        break
                    page = get_json(search_url(court, after, before, query))
                    results = page.get("results", [])
                    if kind == "backlog" and not results:
                        cstate["backlog_done"] = True
                    for res in results:
                        if fetcher.count >= limit:
                            break
                        for op_ref in res.get("opinions", []):
                            try:
                                op = get_json(f"{API}/opinions/{op_ref['id']}/")
                            except FetchError as exc:
                                counts["errors"] += 1
                                errors.append(f"opinion {op_ref.get('id')}: {exc}")
                                continue
                            text = opinion_text(op).strip()
                            if not text:
                                continue
                            filed = res.get("dateFiled") or ""
                            year = filed[:4] or "undated"
                            cid = int(res["cluster_id"])
                            case = res.get("caseName") or "Unknown"
                            tags = tags_for(text) + ([extra_tag] if extra_tag else [])
                            meta = {
                                "id": f"fl/opinions/{cid}",
                                "jurisdiction": "fl",
                                "type": "opinion",
                                "citation": "; ".join(res.get("citation") or []) or f"{case} ({filed})",
                                "heading": case,
                                "court_id": court,
                                "court_name": res.get("court") or COURTS[court],
                                "case_name": case,
                                "docket": res.get("docketNumber") or "",
                                "date_filed": filed,
                                "cl_cluster_id": cid,
                                "precedential_status": res.get("status") or "",
                                "topic_tags": sorted(set(tags)),
                                "cites_statutes": cited_statutes(text),
                                "source_url": "https://www.courtlistener.com" + res.get("absolute_url", f"/opinion/{cid}/"),
                                "source_name": "CourtListener (Free Law Project)",
                                "official": False,
                                "retrieved_at": today(),
                                "content_sha256": "",
                                "status": "active",
                            }
                            folder = "rule-amendments" if extra_tag else court
                            rel = f"states/fl/opinions/{folder}/{year}/{cid}-{slug(case)}.md"
                            counts[write_if_changed(ROOT / rel, meta, f"# {case}\n\n{text}")] += 1
                            break  # lead opinion only
                        filed = res.get("dateFiled")
                        if filed:
                            if not cstate.get("newest") or filed > cstate["newest"]:
                                cstate["newest"] = filed
                            if not cstate.get("oldest") or filed < cstate["oldest"]:
                                cstate["oldest"] = filed
    except StopIteration:
        pass
    except FetchError as exc:
        counts["errors"] += 1
        errors.append(str(exc))
    counts["requests"] = fetcher.count
    state["last_run"] = date.today().isoformat()
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n")
    return {"collection": "fl-opinions", "counts": counts, "errors": errors[:50]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=int, default=45, help="max API requests this run")
    ap.add_argument("--summary")
    args = ap.parse_args()
    result = run(args.budget)
    text = json.dumps(result, indent=2)
    print(text)
    if args.summary:
        Path(args.summary).write_text(text)


if __name__ == "__main__":
    main()
