from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import pytest

from corpus.adapters import cyber_threat_intel, gdelt_events, openalex_scholarly, stark_export


ROOT = Path(__file__).resolve().parents[1]


def test_dataset_adapter_scripts_expose_help() -> None:
    scripts = [
        "corpus/adapters/stark_export.py",
        "corpus/adapters/openalex_scholarly.py",
        "corpus/adapters/gdelt_events.py",
        "corpus/adapters/cyber_threat_intel.py",
    ]

    for script in scripts:
        result = subprocess.run(
            [sys.executable, script, "--help"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        assert "usage:" in result.stdout
        assert "--output" in result.stdout


def test_cyber_adapter_writes_named_relationships(tmp_path) -> None:
    source = {
        "id": "intrusion-set--alpha",
        "type": "intrusion-set",
        "name": "Alpha Group",
        "description": "An example intrusion set.",
        "external_references": [{"external_id": "G0001"}],
    }
    target = {
        "id": "attack-pattern--spearphishing",
        "type": "attack-pattern",
        "name": "Spearphishing Attachment",
        "description": "An example technique.",
        "external_references": [{"external_id": "T1566.001"}],
    }
    rels = [{
        "source_ref": "intrusion-set--alpha",
        "target_ref": "attack-pattern--spearphishing",
        "relationship_type": "uses",
    }]

    cyber_threat_intel._write_object(
        tmp_path,
        1,
        source,
        rels,
        {source["id"]: source, target["id"]: target},
    )

    text = next(tmp_path.glob("*.md")).read_text(encoding="utf-8")
    assert "Alpha Group -> uses -> Spearphishing Attachment" in text
    assert "attack-pattern--spearphishing" not in text


def test_openalex_write_work_renders_authors_concepts_and_abstract(tmp_path) -> None:
    work = {
        "title": "A Study of Widgets",
        "authorships": [
            {"author": {"display_name": "A. Researcher"},
             "institutions": [{"display_name": "Widget University"}]},
        ],
        "topics": [{"display_name": "Widget Engineering"}],
        # keys deliberately out of position order, to prove the abstract is
        # reconstructed by each word's inverted-index POSITION, not dict/insertion
        # order — OpenAlex's inverted index has no guaranteed key ordering.
        "abstract_inverted_index": {"useful": [2], "Widgets": [0], "are": [1]},
        "referenced_works": ["https://openalex.org/W1"],
        "primary_location": {"source": {"display_name": "Journal of Widgets"}},
        "doi": "https://doi.org/10.1/widget",
    }

    openalex_scholarly._write_work(tmp_path, 1, work)

    text = next(tmp_path.glob("*.md")).read_text(encoding="utf-8")
    assert "# A Study of Widgets" in text
    assert "Authors: A. Researcher" in text
    assert "Concepts: Widget Engineering" in text
    assert "Abstract:\nWidgets are useful" in text  # inverted index reconstructed in position order
    assert "A Study of Widgets -> authored_by -> A. Researcher" in text
    assert "A Study of Widgets -> affiliated_with -> Widget University" in text
    assert "A Study of Widgets -> has_concept -> Widget Engineering" in text
    assert "A Study of Widgets -> cites -> https://openalex.org/W1" in text


def test_openalex_write_work_degrades_on_missing_optional_fields(tmp_path) -> None:
    openalex_scholarly._write_work(tmp_path, 1, {"id": "https://openalex.org/W2"})

    text = next(tmp_path.glob("*.md")).read_text(encoding="utf-8")
    assert "# https://openalex.org/W2" in text  # title falls back to id
    assert "Authors: unknown" in text
    assert "Concepts: unknown" in text
    assert "(no abstract in OpenAlex record)" in text


def test_gdelt_write_article_renders_metadata_and_query(tmp_path) -> None:
    article = {
        "title": "Widget Factory Opens",
        "url": "https://news.example/widgets",
        "domain": "news.example",
        "seendate": "20260101T000000Z",
        "sourcecountry": "United States",
        "language": "English",
    }

    gdelt_events._write_article(tmp_path, 1, article, "widget factory")

    text = next(tmp_path.glob("*.md")).read_text(encoding="utf-8")
    assert "# Widget Factory Opens" in text
    assert "Dataset query: widget factory" in text
    assert "Widget Factory Opens -> source_domain -> news.example" in text
    assert "Widget Factory Opens -> matched_query -> widget factory" in text
    assert "Record link: https://news.example/widgets" in text


def test_gdelt_write_article_falls_back_to_url_title_and_none_link(tmp_path) -> None:
    gdelt_events._write_article(tmp_path, 1, {}, "widget factory")

    text = next(tmp_path.glob("*.md")).read_text(encoding="utf-8")
    assert "# GDELT article 1" in text
    assert "Record link: (none)" in text


def test_stark_node_text_prefers_known_fields_over_raw_json() -> None:
    node = {"title": "Widget", "description": "A small widget.", "irrelevant": "noise"}
    assert stark_export._node_text(node) == "title: Widget\ndescription: A small widget."


def test_stark_node_text_falls_back_to_json_dump_for_unknown_shape() -> None:
    assert stark_export._node_text("plain string node") == "plain string node"
    node = {"unmapped_field": "value"}
    assert '"unmapped_field": "value"' in stark_export._node_text(node)


def test_stark_write_doc_renders_dataset_and_node_id(tmp_path) -> None:
    stark_export._write_doc(tmp_path, 1, "prime", "node-42", {"name": "Widget Node"})

    text = next(tmp_path.glob("*.md")).read_text(encoding="utf-8")
    assert "# prime:node-42" in text
    assert "Dataset: prime" in text
    assert "Node ID: node-42" in text
    assert "name: Widget Node" in text
    assert "prime:node-42 -> appears_in -> STaRK-prime" in text


def test_adapter_slugs_normalize_identically() -> None:
    # _slug is deliberately quadruplicated (the adapters are standalone dual-mode
    # scripts); this drift guard keeps the four normalizations byte-identical for
    # non-empty input (only the empty-input fallback word differs by design).
    from corpus.adapters import (cyber_threat_intel, gdelt_events,
                                 openalex_scholarly, stark_export)

    modules = (cyber_threat_intel, gdelt_events, openalex_scholarly, stark_export)
    for text in ["Hello World!", "A--B  c", "Café au lait", "x" * 100, "MITRE ATT&CK"]:
        slugs = {m._slug(text) for m in modules}
        assert len(slugs) == 1, f"slug drift for {text!r}: {slugs}"


@pytest.mark.parametrize("limit", [0, -1, -200])
def test_adapter_limit_rejects_non_positive_values(limit) -> None:
    # A non-positive --limit passes a bare type=int but then misbehaves
    # downstream: list[:limit] with a negative limit silently keeps all-but-
    # |limit| items instead of exporting nothing. _positive_int is deliberately
    # quadruplicated across the four adapters (same rationale as _slug above);
    # this drift guard keeps all four rejecting the same bad inputs.
    from corpus.adapters import (cyber_threat_intel, gdelt_events,
                                 openalex_scholarly, stark_export)

    modules = (cyber_threat_intel, gdelt_events, openalex_scholarly, stark_export)
    for module in modules:
        with pytest.raises(argparse.ArgumentTypeError):
            module._positive_int(str(limit))


def test_adapter_limit_accepts_positive_values() -> None:
    from corpus.adapters import (cyber_threat_intel, gdelt_events,
                                 openalex_scholarly, stark_export)

    modules = (cyber_threat_intel, gdelt_events, openalex_scholarly, stark_export)
    for module in modules:
        assert module._positive_int("5") == 5


class _FailingHttpxClient:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def __enter__(self) -> "_FailingHttpxClient":
        return self

    def __exit__(self, *exc_info) -> None:
        return None

    def get(self, *args, **kwargs):
        raise RuntimeError("simulated network failure")


def test_httpx_adapters_fetch_before_purging_output_dir(tmp_path, monkeypatch) -> None:
    # Each of gdelt_events/openalex_scholarly/cyber_threat_intel deliberately
    # fetches (and parses) before purging output/*.md, so a failed fetch can't
    # empty a previously-populated output dir (comment: "mirrors stark_export's
    # ordering" repeated in all four adapters). This drift guard proves the
    # invariant holds by making the fetch fail and asserting a pre-existing
    # file in output/ survives — i.e. the purge loop was never reached.
    calls = {
        "gdelt_events": lambda output: gdelt_events.export(
            "test query", "20260101000000", "20260102000000", output, 5
        ),
        "openalex_scholarly": lambda output: openalex_scholarly.export("test", output, 5),
        "cyber_threat_intel": lambda output: cyber_threat_intel.export(output, 5),
    }
    modules = {
        "gdelt_events": gdelt_events,
        "openalex_scholarly": openalex_scholarly,
        "cyber_threat_intel": cyber_threat_intel,
    }
    for name, call in calls.items():
        output = tmp_path / name
        output.mkdir()
        sentinel = output / "999-sentinel.md"
        sentinel.write_text("stale content from a prior run\n", encoding="utf-8")

        monkeypatch.setattr(modules[name].httpx, "Client", _FailingHttpxClient)
        with pytest.raises(RuntimeError, match="simulated network failure"):
            call(output)

        assert sentinel.is_file(), f"{name} purged output/ despite the fetch failing"


class _FakeGdeltResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return self._payload


class _SucceedingGdeltHttpxClient:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def __enter__(self) -> "_SucceedingGdeltHttpxClient":
        return self

    def __exit__(self, *exc_info) -> None:
        return None

    def get(self, *args, **kwargs):
        return _FakeGdeltResponse({"articles": [
            {"title": "First Article", "url": "https://example.com/1"},
            {"title": "Second Article", "url": "https://example.com/2"},
        ]})


def test_gdelt_export_purges_after_fetch_succeeds_not_before(tmp_path, monkeypatch) -> None:
    # export()'s purge loop (drop stale *.md before writing this run's docs) runs
    # AFTER the fetch/parse, matching the fetch-before-purge invariant above — but
    # that invariant alone doesn't prove the purge and write loops are correctly
    # ordered RELATIVE TO EACH OTHER on a successful fetch. If purge ran after
    # write instead of before, it would delete the very files this run just wrote
    # (same *.md glob), since count is computed independently of what's left on
    # disk — export() would report success while leaving output/ empty.
    monkeypatch.setattr(gdelt_events.httpx, "Client", _SucceedingGdeltHttpxClient)
    output = tmp_path / "gdelt"
    output.mkdir()
    stale = output / "999-stale.md"
    stale.write_text("stale content from a prior run\n", encoding="utf-8")

    count = gdelt_events.export(
        "test query", "20260101000000", "20260102000000", output, 5
    )

    assert count == 2
    remaining = sorted(p.name for p in output.glob("*.md"))
    assert stale.name not in remaining  # purge did run
    assert len(remaining) == 2  # and both newly-written articles survived it


def test_stark_export_fetches_before_purging_output_dir(tmp_path, monkeypatch) -> None:
    class _FailingStarkQa:
        @staticmethod
        def load_skb(*args, **kwargs):
            raise RuntimeError("simulated download failure")

    monkeypatch.setitem(sys.modules, "stark_qa", _FailingStarkQa)
    output = tmp_path / "stark"
    output.mkdir()
    sentinel = output / "999-sentinel.md"
    sentinel.write_text("stale content from a prior run\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="simulated download failure"):
        stark_export.export("prime", output, 5)

    assert sentinel.is_file(), "stark_export purged output/ despite load_skb failing"
