import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import common  # noqa: E402
import fl_statutes  # noqa: E402

HTML = (ROOT / "tests/fixtures/chapter_sample.html").read_text()


def parse():
    return fl_statutes.parse_chapter(HTML, "0900-0999/0999", "2026", "XLIX", "SAMPLE")


def test_parses_sections_and_numbering():
    docs = parse()
    assert [m["section"] for _, m, _ in docs] == ["999.01", "999.02"]
    rel, meta, text = docs[0]
    assert rel == "states/fl/statutes/title-xlix/chapter-0999/999.01.md"
    assert meta["heading"] == "Purpose."
    assert meta["chapter"] == "999"
    assert meta["chapter_name"] == "SAMPLE CHAPTER FOR TESTS"
    assert "(2) Its purposes are:" in text
    assert "(b) To keep nesting." in text
    assert text.startswith("# § 999.01 Purpose.")
    assert text.strip().endswith("History: s. 1, ch. 2000-1.")
    assert meta["source_url"].endswith("URL=0900-0999/0999/Sections/0999.01.html")


def test_repealed_status():
    _, meta, text = parse()[1]
    assert meta["status"] == "repealed"
    assert text.strip()


def test_write_if_changed_is_idempotent(tmp_path):
    rel, meta, text = parse()[0]
    path = tmp_path / rel
    assert common.write_if_changed(path, dict(meta), text) == "added"
    meta2 = dict(meta, retrieved_at="2099-01-01")
    assert common.write_if_changed(path, meta2, text) == "unchanged"
    assert "2099" not in path.read_text()
    assert common.write_if_changed(path, dict(meta), text + "\nNew sentence.") == "changed"


def test_rejects_unofficial_source():
    import pytest
    with pytest.raises(ValueError):
        common.check_source("https://example.com/law")


def test_status_only_from_leading_words():
    assert fl_statutes.detect_status("Repealed statute not revived by implication.", "No statute...") == "active"
    assert fl_statutes.detect_status("Transfer of tax certificates.", "may be transferred") == "active"
    assert fl_statutes.detect_status("Repealed by s. 3, ch. 2019-1.", "") == "repealed"


def test_email_check_allows_only_government_domains():
    import validate
    assert validate.unofficial_emails("Write to SAMH.jitp@myflfamilies.com or clerk@flcourts.gov") == []
    assert validate.unofficial_emails("contact jane@gmail.com") == ["jane@gmail.com"]


def _opinion_result(cid, case, court="fla"):
    return {"cluster_id": cid, "caseName": case, "dateFiled": "2026-05-01", "court": "Supreme Court of Florida",
            "absolute_url": f"/opinion/{cid}/x/", "citation": [], "docketNumber": "SC26-1", "status": "Published"}


def test_redacts_private_emails_but_keeps_government_ones():
    assert common.redact_emails("Served: malaimo@porterwright.com, clerk@flcourts.org") == \
        "Served: [email removed], clerk@flcourts.org"


def test_opinion_found_by_both_searches_is_saved_once(tmp_path):
    import fl_opinions
    import validate
    (tmp_path / "states").mkdir()
    res = _opinion_result(11035060, "In re: Amendments to Florida Probate Rules 5.171 and 5.205")
    text = "Relocation of the ward. Comments from malaimo@porterwright.com."
    # family search first (court folder), then the rule-amendment search
    assert fl_opinions.save_opinion(res, text, "fla", False, root=tmp_path) == "added"
    assert fl_opinions.save_opinion(res, text, "fla", True, root=tmp_path) == "unchanged"
    files = list((tmp_path / "states/fl/opinions").rglob("*.md"))
    assert [f.parent.parent.name for f in files] == ["rule-amendments"]
    meta, body = common.read_doc(files[0])
    assert "rule-amendment" in meta["topic_tags"] and "relocation" in meta["topic_tags"]
    assert "porterwright" not in body
    assert validate.validate(tmp_path) == []


def test_existing_court_copy_is_moved_into_rule_amendments(tmp_path):
    import fl_opinions
    import validate
    (tmp_path / "states").mkdir()
    # a name the rule regex does not match, so the family pass files it under fla/
    res = _opinion_result(42, "Amendments to the Florida Family Law Rules")
    fl_opinions.save_opinion(res, "Parenting plan forms.", "fla", False, root=tmp_path)
    fl_opinions.save_opinion(res, "Parenting plan forms.", "fla", True, root=tmp_path)
    files = list((tmp_path / "states/fl/opinions").rglob("*.md"))
    assert [f.parent.parent.name for f in files] == ["rule-amendments"]
    assert common.read_doc(files[0])[0]["topic_tags"] == ["parenting-plan", "rule-amendment"]
    assert validate.validate(tmp_path) == []
