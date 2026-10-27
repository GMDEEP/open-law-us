"""Build states/<st>/<collection>/index.jsonl and the root manifest.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, read_doc  # noqa: E402

SCHEMA_VERSION = "1.0"


def collection_docs(cdir: Path):
    for path in sorted(cdir.rglob("*.md")):
        if path.name in ("README.md", "CHANGELOG.md"):
            continue
        doc = read_doc(path)
        if doc:
            yield path, doc[0]


def sort_key(meta: dict):
    sec = meta.get("section") or meta.get("id")
    parts = []
    for p in str(sec).replace("-", ".").split("."):
        parts.append((0, int(p), "") if p.isdigit() else (1, 0, p))
    return parts


def build(root: Path = ROOT) -> dict:
    states = []
    for sdir in sorted((root / "states").iterdir()):
        info_path = sdir / "state.json"
        if not info_path.exists():
            continue
        info = json.loads(info_path.read_text())
        collections = []
        for name, cinfo in info["collections"].items():
            cdir = sdir / name
            rows = []
            if cdir.exists():
                for path, meta in collection_docs(cdir):
                    rows.append({
                        "id": meta["id"],
                        "citation": meta["citation"],
                        "heading": meta.get("heading", ""),
                        "path": path.relative_to(root).as_posix(),
                        "status": meta.get("status", "active"),
                        "retrieved_at": meta.get("retrieved_at"),
                        "sha256": meta.get("content_sha256"),
                        "_sort": meta,
                    })
            rows.sort(key=lambda r: sort_key(r.pop("_sort")) if "_sort" in r else [])
            index_rel = f"states/{sdir.name}/{name}/index.jsonl"
            if rows:
                (root / index_rel).write_text(
                    "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
            collections.append({
                **cinfo,
                "path": f"states/{sdir.name}/{name}",
                "index": index_rel if rows else None,
                "item_count": len(rows),
                "last_changed": max((r["retrieved_at"] for r in rows if r["retrieved_at"]), default=None),
            })
        states.append({"code": info["code"], "name": info["name"], "path": f"states/{sdir.name}",
                       "collections": collections})
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "description": "Index of every jurisdiction and collection in open-law-us. Unofficial; see DISCLAIMER.md.",
        "frontmatter_schema": "schema/frontmatter.schema.json",
        "states": states,
    }
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    return manifest


if __name__ == "__main__":
    m = build()
    for s in m["states"]:
        for c in s["collections"]:
            print(f"{c['id']}: {c['item_count']} documents")
