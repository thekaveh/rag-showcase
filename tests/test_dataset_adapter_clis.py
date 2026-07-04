from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from corpus.adapters import cyber_threat_intel


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
