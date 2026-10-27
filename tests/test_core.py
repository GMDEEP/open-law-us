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
