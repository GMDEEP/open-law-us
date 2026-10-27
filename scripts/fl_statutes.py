"""Fetch the Florida Statutes from Online Sunshine into states/fl/statutes/.

One request per title index and one per chapter (each chapter page holds every
section), with a polite delay between requests. A full run is ~1,100 requests.

Usage:
  python scripts/fl_statutes.py                     # everything
  python scripts/fl_statutes.py --chapters 61,90    # just these chapters
  python scripts/fl_statutes.py --from-file ch.html --chapter-path 0000-0099/0061  # offline parse
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup, NavigableString, Tag

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, FetchError, PoliteFetcher, today, write_if_changed  # noqa: E402

BASE = "https://www.leg.state.fl.us/statutes/index.cfm"
TITLES_URL = BASE + "?Mode=View%20Statutes&Submenu=1&Tab=statutes"
SOURCE_NAME = "Online Sunshine (The Florida Legislature)"
LEVELS = {"Subsection", "Paragraph", "SubParagraph", "SubSubParagraph", "SubSubSubParagraph"}
ROMAN = re.compile(r"^[IVXLC]+$")


def clean(text: str) -> str:
    text = text.replace(" ", " ").replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def section_url(chapter_path: str, section: str) -> str:
    folder = chapter_path.split("/")[-1]
    whole, _, frac = section.partition(".")
    return f"{BASE}?App_mode=Display_Statute&URL={chapter_path}/Sections/{folder}.{frac}.html"


def classes(el: Tag) -> set[str]:
    return set(el.get("class") or [])


def render_table(table: Tag) -> list[str]:
    rows = []
    for tr in table.find_all("tr"):
        cells = [clean(td.get_text(" ")) for td in tr.find_all(["td", "th"])]
        if any(cells):
            rows.append("| " + " | ".join(cells) + " |")
    if not rows:
        return []
    ncols = rows[0].count("|") - 1
    return [rows[0], "|" + " --- |" * ncols] + rows[1:]


def render_block(el: Tag, out: list[str], prefix: str = "") -> str:
    """Render the children of el into out. Returns any unused prefix."""
    for child in el.children:
        if isinstance(child, NavigableString):
            txt = clean(str(child))
            if txt:
                out.append(prefix + txt)
                prefix = ""
            continue
        if not isinstance(child, Tag):
            continue
        cls = classes(child)
        if child.name == "div" and cls & LEVELS:
            num = child.find("span", class_="Number", recursive=False)
            sub_prefix = clean(num.get_text()) + " " if num else ""
            leftover = render_block_skip_number(child, out, sub_prefix)
            if leftover.strip():
                out.append(leftover.strip())
        elif child.name == "table":
            out.extend(render_table(child))
        elif child.name == "span" and "Number" in cls:
            continue
        elif child.name in ("span", "div", "p"):
            if child.find(["div", "table"]):
                prefix = render_block(child, out, prefix)
            else:
                txt = clean(child.get_text(" "))
                if txt:
                    out.append(prefix + txt)
                    prefix = ""
    return prefix


def render_block_skip_number(el: Tag, out: list[str], prefix: str) -> str:
    return render_block(el, out, prefix)


def body_text(section: Tag) -> str:
    out: list[str] = []
    body = section.find(class_="SectionBody")
    if body is not None:
        render_block(body, out)
    return "\n\n".join(line for line in out if line)


def detect_status(catchline: str, body: str) -> str:
    """The current edition prints only live law, so a section is only marked
    repealed/transferred/renumbered/reserved when it *begins* that way
    (e.g. a catchline of "Repealed by s. 2, ch. 2010-5.")."""
    lead = (catchline or body).strip().lower()
    m = re.match(r"^\[?(repealed|transferred|renumbered)\]?(\s+(by|to|as|effective|in|pursuant)\b|\s*[.,;:\u2014-]|$)", lead)
    if m:
        return m.group(1)
    if re.match(r"^\[?reserved\]?\.?$", lead):
        return "reserved"
    return "active"


def parse_chapter(html: str, chapter_path: str, edition: str, title_num: str,
                  title_name: str) -> list[tuple[str, dict, str]]:
    soup = BeautifulSoup(html, "html.parser")
    chapter_num = str(int(chapter_path.split("/")[-1])) if chapter_path.split("/")[-1].isdigit() \
        else chapter_path.split("/")[-1].lstrip("0")
    cname_el = soup.find(class_="ChapterName")
    chapter_name = clean(cname_el.get_text(" ")) if cname_el else ""
    docs = []
    for sec in soup.find_all("div", class_="Section"):
        num_el = sec.find("span", class_="SectionNumber")
        if num_el is None:
            continue
        number = clean(num_el.get_text())
        if not re.match(r"^\d+[A-Z]?\.\d+", number):
            continue
        cat_el = sec.find(class_="CatchlineText") or sec.find(class_="Catchline")
        catchline = clean(cat_el.get_text(" ")) if cat_el else ""
        body = body_text(sec)
        hist_el = sec.find(class_="HistoryText")
        history = clean(hist_el.get_text(" ")) if hist_el else ""
        notes = [clean(n.get_text(" ")) for n in sec.find_all("div", class_="Note")]
        if not body and not history:
            # A section page with only a catchline (e.g. "Repealed by ...")
            body = catchline
        text = f"# § {number} {catchline}".rstrip() + "\n\n" + body
        if history:
            text += "\n\nHistory: " + history
        if notes:
            text += "\n\n" + "\n\n".join(notes)
        meta = {
            "id": f"fl/statutes/{number}",
            "jurisdiction": "fl",
            "type": "statute",
            "citation": f"Fla. Stat. § {number}",
            "heading": catchline,
            "section": number,
            "title_num": title_num,
            "title_name": title_name,
            "chapter": chapter_num,
            "chapter_name": chapter_name,
            "edition": edition,
            "history": history,
            "source_url": section_url(chapter_path, number),
            "source_name": SOURCE_NAME,
            "official": False,
            "retrieved_at": today(),
            "content_sha256": "",
            "status": detect_status(catchline, body),
        }
        if not meta["history"]:
            del meta["history"]
        rel = f"states/fl/statutes/title-{title_num.lower()}/chapter-{chapter_path.split('/')[-1]}/{number}.md"
        docs.append((rel, meta, text))
    return docs


def list_titles(fetcher: PoliteFetcher) -> list[tuple[str, str]]:
    soup = BeautifulSoup(fetcher.get(TITLES_URL).text, "html.parser")
    titles = []
    for a in soup.find_all("a", href=True):
        q = parse_qs(urlparse(a["href"]).query)
        if q.get("App_mode") == ["Display_Index"] and "Title_Request" in q:
            roman = q["Title_Request"][0]
            if ROMAN.match(roman) and roman not in [t for t, _ in titles]:
                name_td = a.find_parent("td").find_next_sibling("td")
                titles.append((roman, clean(name_td.get_text(" ")) if name_td else ""))
    return titles


def list_chapters(fetcher: PoliteFetcher, roman: str) -> list[tuple[str, str]]:
    url = f"{BASE}?App_mode=Display_Index&Title_Request={roman}"
    soup = BeautifulSoup(fetcher.get(url).text, "html.parser")
    out = []
    for a in soup.find_all("a", href=True):
        m = re.search(r"URL=(\d{4}-\d{4}/[0-9A-Z]+)/[0-9A-Z]+ContentsIndex\.html", a["href"])
        if m:
            year = parse_qs(urlparse(a["href"]).query).get("StatuteYear", [""])[0]
            if m.group(1) not in [c for c, _ in out]:
                out.append((m.group(1), year))
    return out


def run(args) -> dict:
    out_root = Path(args.out).resolve().parent if args.out != "states" else ROOT
    fetcher = PoliteFetcher(delay=args.delay)
    counts = {"added": 0, "changed": 0, "unchanged": 0, "removed": 0, "errors": 0, "chapters": 0}
    errors: list[str] = []
    seen: set[str] = set()
    wanted = {c.strip().zfill(4) for c in args.chapters.split(",")} if args.chapters else None

    for roman, tname in list_titles(fetcher):
        if args.titles and roman not in args.titles.split(","):
            continue
        for chapter_path, year in list_chapters(fetcher, roman):
            folder = chapter_path.split("/")[-1]
            if wanted and folder not in wanted:
                continue
            url = f"{BASE}?App_mode=Display_Statute&URL={chapter_path}/{folder}.html"
            try:
                html = fetcher.get(url).text
            except FetchError as exc:
                counts["errors"] += 1
                errors.append(f"{chapter_path}: {exc}")
                continue
            docs = parse_chapter(html, chapter_path, year or args.edition, roman, tname)
            if not docs:
                counts["errors"] += 1
                errors.append(f"{chapter_path}: no sections parsed")
                continue
            counts["chapters"] += 1
            for rel, meta, text in docs:
                seen.add(rel)
                result = write_if_changed(out_root / rel, meta, text)
                counts[result] += 1

    full_run = not args.chapters and not args.titles
    if full_run and counts["errors"] == 0:
        for path in (out_root / "states/fl/statutes").rglob("*.md"):
            rel = path.relative_to(out_root).as_posix()
            if rel not in seen:
                path.unlink()
                counts["removed"] += 1
    counts["requests"] = fetcher.count
    return {"collection": "fl-statutes", "counts": counts, "errors": errors[:50],
            "full_run": full_run}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapters", help="comma list of chapter numbers, e.g. 61,90")
    ap.add_argument("--titles", help="comma list of title numerals, e.g. VI,VII")
    ap.add_argument("--out", default="states")
    ap.add_argument("--edition", default=str(__import__("datetime").date.today().year))
    ap.add_argument("--delay", type=float, default=3.0)
    ap.add_argument("--summary", help="write a JSON summary here")
    args = ap.parse_args()
    result = run(args)
    text = json.dumps(result, indent=2)
    print(text)
    if args.summary:
        Path(args.summary).write_text(text)


if __name__ == "__main__":
    main()
