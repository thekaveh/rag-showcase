import sys

import corpus.fetch_corpus as fc


def test_fetch_corpus_purges_stale_docs(tmp_path, monkeypatch) -> None:
    # Re-assembly must be idempotent: a prior run's orphaned higher-index doc
    # (e.g. after a smaller MAX_DOCS) must not survive into corpus/raw for ingest's
    # **/*.md glob to mix in. Guards the purge added in fetch_corpus.main().
    raw = tmp_path / "raw"
    keyword = tmp_path / "keyword_docs"
    raw.mkdir()
    keyword.mkdir()
    (keyword / "kw.md").write_text("durable keyword doc", encoding="utf-8")
    (raw / "999-stale.md").write_text("orphan from a prior larger run", encoding="utf-8")

    monkeypatch.setattr(fc, "RAW", raw)
    monkeypatch.setattr(fc, "KEYWORD", keyword)
    # Force the offline (keyword-docs-only) path so the test does no network I/O.
    monkeypatch.setitem(sys.modules, "datasets", None)

    fc.main()

    assert not (raw / "999-stale.md").exists()  # stale orphan purged
    assert (raw / "kw.md").exists()              # durable keyword doc re-copied


def test_fetch_corpus_online_writes_sanitized_slice(tmp_path, monkeypatch) -> None:
    # The online path: rows from the datasets library land as NNN-<title>.md with
    # '/' sanitized out of filenames and the body preferring body > text > json.
    import sys
    import types

    import corpus.fetch_corpus as fetch

    raw = tmp_path / "raw"
    keyword = tmp_path / "keyword"
    keyword.mkdir()
    (keyword / "kw.md").write_text("# kw", encoding="utf-8")
    monkeypatch.setattr(fetch, "RAW", raw)
    monkeypatch.setattr(fetch, "KEYWORD", keyword)
    rows = [{"title": "A/B: story", "body": "the body"},
            {"title": "second", "text": "text field"}]
    monkeypatch.setitem(sys.modules, "datasets",
                        types.SimpleNamespace(load_dataset=lambda *a, **k: rows))

    fetch.main()

    names = sorted(p.name for p in raw.glob("*.md"))
    assert names == ["000-A-B: story.md", "001-second.md", "kw.md"]
    assert (raw / "000-A-B: story.md").read_text(encoding="utf-8") == "# A-B: story\n\nthe body"
    assert (raw / "001-second.md").read_text(encoding="utf-8") == "# second\n\ntext field"
