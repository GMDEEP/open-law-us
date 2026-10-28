# Florida

## Sources

| Collection | Official source | How we get it |
|---|---|---|
| Statutes | [Online Sunshine](https://www.leg.state.fl.us/statutes/), The Florida Legislature | `scripts/fl_statutes.py`: one request per chapter page, 3 seconds apart |
| Rules of Court | Rules adopted by the Supreme Court of Florida, compiled by [The Florida Bar](https://www.floridabar.org/rules/ctproc/) | `scripts/fl_rules.py`: parses each rule PDF (downloaded by a person; the Bar blocks automated downloads); rule text and court notes only |
| Opinions | Florida Supreme Court and District Courts of Appeal, via [CourtListener](https://www.courtlistener.com/) | `scripts/fl_opinions.py`: family-law opinions, plus Supreme Court opinions adopting or amending rules (`opinions/rule-amendments/`); CourtListener API, about 100 requests a week |

## Copyright position

- **Statutes: not claimed.** The State of Florida does not claim copyright in the Florida Statutes. Florida public records are not copyrightable unless the Legislature specifically provides for it (Fla. Const. art. I, § 24). Statutes are government edicts, which cannot be copyrighted (*Georgia v. Public.Resource.Org, Inc.*, 590 U.S. 255 (2020)). Section 11.2421 of the Florida Statutes adopts each year's compilation as the official statute law; it does not claim copyright. The copyright line in the Online Sunshine website footer covers the website. We take the text, catchlines, history notes and notes only, and re-render them as plain text.
- **Court rules: rule text is public domain.** Rules adopted by the Supreme Court of Florida are judicial edicts. The Florida Bar's compiled PDFs carry a Bar copyright notice covering its compilation and editorial matter. We include rule text and court-adopted committee notes only, never the Bar's index, front matter or other editorial material.
- **Opinions: public domain.** Judicial opinions are government edicts. We include opinion text and basic metadata only, never publisher headnotes or summaries.
- **Not included:** the Florida Administrative Code (its status under Fla. Stat. § 120.55 has not been reviewed) and any commercial annotated code.

## Update schedule

Checked every week. The Legislature publishes a new statutes edition each year after the regular session, so most weeks will show no statute changes. Rules change when the Supreme Court amends them. New opinions are filed every week.

## Rules of Court: what is and isn't included

All ten rule sets the Bar publishes are included, one file per rule (812 rules):
civil (ch. 1), general practice and judicial administration (ch. 2), criminal (ch. 3),
civil procedure for involuntary commitment of sexually violent predators (ch. 4), probate (ch. 5),
traffic court (ch. 6), small claims (ch. 7), juvenile (ch. 8), appellate (ch. 9), and family law (ch. 12).
Each file records the edition date printed on its PDF.

Not included yet:
- **Court forms** (for example the forms appendices, Form 1.901 onward, and the sentencing guidelines scoresheets, rules 3.988 to 3.992). They are forms rather than rules, and will be added later as a separate, clearly labeled collection.
- **Standard jury instructions** and other reference material.
- **Historical rule editions.** Only the current edition is included. Past editions will go in a separate `historical/` area so they are never mistaken for current law.

### Updating the rules
The Bar's site refuses automated downloads, so rule PDFs are downloaded by a person and imported with `scripts/fl_rules.py`. The weekly opinions pull includes Supreme Court rule-amendment opinions, so an amendment shows up there as a signal that a rule set needs re-importing.
