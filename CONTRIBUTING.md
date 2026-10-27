# Contributing

Thank you for helping make the law free and readable. Florida is the first state. Every other state is open for contribution.

## Ground rules

1. **Official sources only.** Every file must link (`source_url`) to the government body that publishes the law: a legislature, a court, or a court system. The allowed domains are listed in `scripts/allowed_sources.json`. To add one, add it in your pull request and explain why it is official.
2. **Law text only.** No commercial annotations, publisher headnotes, summaries, or editorial matter. See `NOTICE.md`.
3. **Document the copyright position first.** A new state's folder must include a `README.md` that states whether that state claims copyright in its code, with a citation. A pull request without this will not be merged.
4. **No private information.** Never add names of private parties, addresses, phone numbers, or anything from a real person's case.
5. **Machines check, humans approve.** Automated checks run on every pull request. A maintainer reviews and approves every merge, including updates made by our own bots.

## Layout

```
states/<st>/
  README.md                    # sources, copyright position, update schedule
  CHANGELOG.md                 # what changed on each update
  statutes/title-<roman>/chapter-<0000>/<section>.md
  rules/<rule-set>/<rule>.md
  opinions/<court-id>/<year>/<cluster-id>.md
  <collection>/index.jsonl     # generated: one line per document
manifest.json                  # generated: every state and collection
```

Use the two-letter postal code in lowercase (`fl`, `ga`, `tx`).

## File format

Each document is Markdown with YAML frontmatter. The schema is `schema/frontmatter.schema.json`. Example:

```markdown
---
id: fl/statutes/61.13
jurisdiction: fl
type: statute
citation: "Fla. Stat. § 61.13"
heading: "Support of children; parenting and time-sharing; powers of court."
section: "61.13"
title_num: "VI"
chapter: "61"
edition: "2026"
source_url: "https://www.leg.state.fl.us/statutes/index.cfm?App_mode=Display_Statute&URL=0000-0099/0061/Sections/0061.13.html"
source_name: "Online Sunshine (The Florida Legislature)"
official: false
retrieved_at: "2026-10-27"
content_sha256: "<sha256 of the body>"
status: active
---

(text of the law)
```

`content_sha256` is the SHA-256 of the body after the frontmatter, with trailing whitespace stripped from each line. Files are only rewritten when this hash changes, so history shows real changes, not re-downloads.

## Adding a state

1. Open an issue with the "New state" template so others know you are working on it.
2. Write a scraper in `scripts/<st>_<collection>.py` following `scripts/fl_statutes.py`. Use `scripts/common.py` for polite fetching (one request every few seconds, an identifying User-Agent, robots.txt respected).
3. Run it locally, then `python scripts/build_index.py` and `python scripts/validate.py`.
4. Open a pull request. Include the state's `README.md` with its copyright position.

## Running locally

```
pip install -r requirements.txt
python scripts/fl_statutes.py --chapters 61 --out states   # one chapter, for testing
python scripts/build_index.py
python scripts/validate.py
python -m pytest tests
```
