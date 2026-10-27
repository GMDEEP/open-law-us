"""Shared helpers: polite fetching, frontmatter, hashing, change-only writes."""
from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.robotparser
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import requests
import yaml

USER_AGENT = (
    "open-law-us/1.0 (+https://github.com/GMDEEP/open-law-us; "
    "contact: stewart@leadmachinellc.com)"
)
ROOT = Path(__file__).resolve().parent.parent
ALLOWED = json.loads((ROOT / "scripts" / "allowed_sources.json").read_text())["domains"]


class FetchError(RuntimeError):
    pass


class PoliteFetcher:
    """One request at a time, a fixed delay between requests, robots.txt honored."""

    def __init__(self, delay: float = 3.0, retries: int = 3, timeout: int = 60):
        self.delay = delay
        self.retries = retries
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self._robots: dict[str, urllib.robotparser.RobotFileParser] = {}
        self._last = 0.0
        self.count = 0

    def _allowed(self, url: str) -> bool:
        parts = urlparse(url)
        base = f"{parts.scheme}://{parts.netloc}"
        if base not in self._robots:
            rp = urllib.robotparser.RobotFileParser()
            try:
                resp = self.session.get(base + "/robots.txt", timeout=self.timeout)
                rp.parse(resp.text.splitlines() if resp.ok else [])
            except requests.RequestException:
                rp.parse([])
            self._robots[base] = rp
        return self._robots[base].can_fetch(USER_AGENT, url)

    def get(self, url: str, headers: dict | None = None) -> requests.Response:
        if not self._allowed(url):
            raise FetchError(f"robots.txt disallows {url}")
        last_err = None
        for attempt in range(1, self.retries + 1):
            wait = self.delay - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()
            self.count += 1
            try:
                resp = self.session.get(url, timeout=self.timeout, headers=headers)
            except requests.RequestException as exc:
                last_err = exc
            else:
                if resp.status_code == 200:
                    return resp
                last_err = FetchError(f"HTTP {resp.status_code} for {url}")
                if resp.status_code in (401, 403, 404):
                    break
            time.sleep(self.delay * attempt * 2)
        raise FetchError(str(last_err))


def normalize_body(text: str) -> str:
    lines = [ln.rstrip() for ln in text.strip().splitlines()]
    out, blank = [], False
    for ln in lines:
        if not ln:
            if not blank:
                out.append("")
            blank = True
        else:
            out.append(ln)
            blank = False
    return "\n".join(out).strip() + "\n"


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def today() -> str:
    return date.today().isoformat()


def check_source(url: str) -> None:
    host = urlparse(url).netloc.lower()
    if not any(host == d or host.endswith("." + d) for d in ALLOWED):
        raise ValueError(f"source host not on allowlist: {host}")


def read_doc(path: Path) -> tuple[dict, str] | None:
    if not path.exists():
        return None
    raw = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n\n?(.*)$", raw, re.S)
    if not m:
        return None
    return yaml.safe_load(m.group(1)) or {}, m.group(2)


def render_doc(meta: dict, body: str) -> str:
    fm = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True, width=1000).strip()
    return f"---\n{fm}\n---\n\n{body}"


def write_if_changed(path: Path, meta: dict, body: str) -> str:
    """Write the document only if its body or key metadata changed.

    Returns 'added', 'changed' or 'unchanged'. retrieved_at is kept from the old
    file when nothing else changed, so re-downloads never create noise.
    """
    check_source(meta["source_url"])
    body = normalize_body(body)
    meta["content_sha256"] = sha256(body)
    old = read_doc(path)
    if old:
        old_meta, _ = old
        compare = {k: v for k, v in meta.items() if k != "retrieved_at"}
        old_compare = {k: v for k, v in old_meta.items() if k != "retrieved_at"}
        if compare == old_compare:
            return "unchanged"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_doc(meta, body), encoding="utf-8")
    return "changed" if old else "added"
