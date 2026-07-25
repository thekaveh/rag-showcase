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
