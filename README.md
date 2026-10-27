# open-law-us

**Free, open, machine-readable U.S. law, linked to its official source.**

> ⚖️ **Legal information, not legal advice.** Every file is an *unofficial* copy that links to the official source and records when it was retrieved. Always verify against the official source. See [DISCLAIMER.md](DISCLAIMER.md).

The law belongs to everyone, but it is often hard to read, hard to search, and impossible for software to use. This project republishes it as plain Markdown files, one per section, with clean metadata, so that people can read it and developers and AI tools can build on it.

## What's here

| State | Collection | Status | Source |
|---|---|---|---|
| Florida | Statutes (all titles) | ✅ Live, updated weekly | [Online Sunshine](https://www.leg.state.fl.us/statutes/) |
| Florida | Rules of Court (family, general practice & judicial administration) | 🛠️ Parser ready, import in progress | Supreme Court of Florida, via The Florida Bar |
| Florida | Family-law appellate opinions | 🛠️ Ready, waiting on API access | [CourtListener](https://www.courtlistener.com/) |
| *Your state* | — | 🙋 [Help add it](CONTRIBUTING.md) | — |

The Florida Evidence Code is Chapter 90 of the Florida Statutes, so it lives with the statutes.

## How it's organized

```
manifest.json                         ← start here: every state and collection
states/fl/
  README.md                           ← sources, copyright position, schedule
  CHANGELOG.md                        ← what changed on each update
  statutes/index.jsonl                ← one line per section
  statutes/title-vi/chapter-0061/61.13.md
```

Each document is Markdown with YAML frontmatter:

```yaml
---
id: fl/statutes/61.13001
jurisdiction: fl
type: statute
citation: Fla. Stat. § 61.13001
heading: Parental relocation with a child.
chapter: '61'
edition: '2026'
source_url: https://www.leg.state.fl.us/statutes/index.cfm?App_mode=Display_Statute&URL=0000-0099/0061/Sections/0061.13001.html
official: false
retrieved_at: '2026-10-27'
content_sha256: 3f1c…
status: active
---
(1) DEFINITIONS. — As used in this section, the term: …
```

The full field list is in [`schema/frontmatter.schema.json`](schema/frontmatter.schema.json).

## Using it

**Read it:** browse `states/` on GitHub.

**Pull it into code or an AI tool:** read `manifest.json`, then the `index.jsonl` for the collection you want, then fetch the files you need.

```python
import json, urllib.request
BASE = "https://raw.githubusercontent.com/GMDEEP/open-law-us/main/"
manifest = json.load(urllib.request.urlopen(BASE + "manifest.json"))
fl = next(s for s in manifest["states"] if s["code"] == "fl")
statutes = next(c for c in fl["collections"] if c["type"] == "statute")
for line in urllib.request.urlopen(BASE + statutes["index"]):
    row = json.loads(line)
    if row["id"] == "fl/statutes/61.13001":
        print(urllib.request.urlopen(BASE + row["path"]).read().decode())
```

**Clone it:** `git clone --depth 1 https://github.com/GMDEEP/open-law-us`

## How it stays current

A scheduled [GitHub Actions workflow](.github/workflows/update-fl.yml) runs every week. It:

1. Fetches each source politely (one request every few seconds, identified, robots.txt respected).
2. Rewrites a file **only when its text actually changed** (compared by SHA-256).
3. Runs safety checks. A run that looks broken (error pages, mass deletions, huge unexplained changes) is **stopped with no commit**, and an issue is opened.
4. Opens a pull request with a summary of what changed. **A person reviews and approves every merge.**
5. Records a run log and finishes. Every run ends; nothing loops.

## Licensing

- **The law itself** is public domain. Nobody owns it. See [NOTICE.md](NOTICE.md) for why.
- **Our metadata, indexes and schemas:** [CC0 1.0](LICENSE-DATA).
- **Our code:** [MIT](LICENSE).

Court opinions come from CourtListener, a project of the Free Law Project. Free Law Project is not affiliated with this repository and does not endorse it.

## Contributing

Every state is open for contribution. Read [CONTRIBUTING.md](CONTRIBUTING.md), and see the [Code of Conduct](CODE_OF_CONDUCT.md). Report security problems privately ([SECURITY.md](SECURITY.md)).

## Why

So anyone can read the law that governs them, and so the next generation of free legal tools has a trustworthy, open foundation to build on.
