# Notice: what is licensed, and what is not

This repository holds three kinds of material. Each has a different status.

| Material | Where | Status |
|---|---|---|
| The text of the law (statutes, court rules, judicial opinions) | `states/**` file bodies | **Public domain.** Not licensed by us because no one can own it. |
| Our additions: frontmatter metadata, indexes, manifests, schemas | `states/**` frontmatter, `manifest.json`, `**/index.jsonl`, `schema/` | **CC0 1.0** — dedicated to the public domain. See `LICENSE-DATA`. |
| Code: scrapers, validators, workflows | `scripts/`, `tests/`, `.github/` | **MIT License.** See `LICENSE`. |

## Why the law itself is public domain

- **Government edicts doctrine.** Text created by judges and legislators in the course of their official duties cannot be copyrighted. The U.S. Supreme Court reaffirmed this in *Georgia v. Public.Resource.Org, Inc.*, 590 U.S. 255 (2020), and extended it to annotations prepared for a legislature.
- **Florida specifically.** Florida does not claim copyright in the Florida Statutes. Florida public records are not subject to copyright unless the Legislature specifically provides for it (Fla. Const. art. I, § 24; *Microdecisions, Inc. v. Skinner*, 889 So. 2d 871 (Fla. 2d DCA 2004)). The generic copyright line in the footer of the Legislature's website covers the website, not the law. We republish the law's text, catchlines, and history notes only, re-rendered as plain text. We do not copy the site's design or code.
- **Court rules.** Rule text adopted by the Supreme Court of Florida is a judicial edict. Compilations published by The Florida Bar include editorial matter (indexes, arrangement, front matter, non-court notes) that we do **not** reproduce. We extract rule text and court-adopted committee notes only.
- **Opinions.** Judicial opinions are public domain. Opinion text is obtained through [CourtListener](https://www.courtlistener.com/), a project of the Free Law Project. Free Law Project is not affiliated with this repository and does not endorse it. We include opinion text and basic metadata only, never publisher headnotes or summaries.

## What we will not include

- Commercial annotated codes (West, Lexis) or any privately written annotations.
- Any state material whose copyright status has not been documented in that state's `README.md` (see `CONTRIBUTING.md`).
- The Florida Administrative Code, until its status under Fla. Stat. § 120.55 has been reviewed.
