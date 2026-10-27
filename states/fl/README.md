# Florida

## Sources

| Collection | Official source | How we get it |
|---|---|---|
| Statutes | [Online Sunshine](https://www.leg.state.fl.us/statutes/), The Florida Legislature | `scripts/fl_statutes.py`: one request per chapter page, 3 seconds apart |
| Rules of Court | Rules adopted by the Supreme Court of Florida, compiled by [The Florida Bar](https://www.floridabar.org/rules/ctproc/) | `scripts/fl_rules.py`: parses the rule PDF; rule text only |
| Opinions | Florida Supreme Court and District Courts of Appeal, via [CourtListener](https://www.courtlistener.com/) | `scripts/fl_opinions.py`: CourtListener API (token required) |

## Copyright position

- **Statutes: not claimed.** The State of Florida does not claim copyright in the Florida Statutes. Florida public records are not copyrightable unless the Legislature specifically provides for it (Fla. Const. art. I, § 24). Statutes are government edicts, which cannot be copyrighted (*Georgia v. Public.Resource.Org, Inc.*, 590 U.S. 255 (2020)). Section 11.2421 of the Florida Statutes adopts each year's compilation as the official statute law; it does not claim copyright. The copyright line in the Online Sunshine website footer covers the website. We take the text, catchlines, history notes and notes only, and re-render them as plain text.
- **Court rules: rule text is public domain.** Rules adopted by the Supreme Court of Florida are judicial edicts. The Florida Bar's compiled PDFs carry a Bar copyright notice covering its compilation and editorial matter. We include rule text and court-adopted committee notes only, never the Bar's index, front matter or other editorial material.
- **Opinions: public domain.** Judicial opinions are government edicts. We include opinion text and basic metadata only, never publisher headnotes or summaries.
- **Not included:** the Florida Administrative Code (its status under Fla. Stat. § 120.55 has not been reviewed) and any commercial annotated code.

## Update schedule

Checked every week. The Legislature publishes a new statutes edition each year after the regular session, so most weeks will show no statute changes. Rules change when the Supreme Court amends them. New opinions are filed every week.
