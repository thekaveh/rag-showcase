"""Unit tests for the judge panel: JSON extraction, deterministic anonymization
order, verdict normalization, and the aggregation that produces the headline
mean/votes/observed_winner numbers the committed docs snapshots are built from."""
from __future__ import annotations

import json

import httpx
import respx

import compare.judge as judge


def test_extract_json_variants() -> None:
    assert judge.extract_json('{"scores": {"A": 5}}') == {"scores": {"A": 5}}
    fenced = '```json\n{"scores": {"A": 4}, "best": "A"}\n```'
    assert judge.extract_json(fenced) == {"scores": {"A": 4}, "best": "A"}
    assert judge.extract_json('prose before {"scores": {}} prose after') == {"scores": {}}
    assert judge.extract_json("no json here") is None
    assert judge.extract_json("{broken json}") is None


def test_stable_order_is_deterministic_and_input_order_invariant() -> None:
    # The documented reproducibility property: same seed -> same order, regardless
    # of the input ordering (so judges see identical letters across reruns).
    items = ["vanilla-rag", "hybrid-rag", "graph-rag"]
    ordered = judge.stable_order(items, "q1")
    assert judge.stable_order(items, "q1") == ordered
    assert judge.stable_order(list(reversed(items)), "q1") == ordered
    assert sorted(ordered) == sorted(items)
    assert judge.stable_order(items, "q2") != ordered or len(items) == 1


def test_normalize_verdict_tolerates_case_and_strings_rejects_bools() -> None:
    l2m = {"A": "vanilla-rag", "B": "hybrid-rag"}
    verdict = {"scores": {"a": "4", "B": True, "C": 3, "": 2}, "best": "b"}
    norm = judge.normalize_verdict(verdict, l2m)
    # "a" -> A accepted with the string score coerced; B rejected (bool is an int
    # subclass, a true/false reply must not become 1.0/0.0); C/"" unknown -> dropped.
    assert norm["scores"] == {"vanilla-rag": 4.0}
    assert norm["best"] == "hybrid-rag"  # lowercase best letter still maps


def _matrix(tmp_path):
    matrix = {
        "ingestion": {
            "id": "ing-1",
            "profile": "baseline_curated",
            "revision": "rev-1",
            "content_digest": "digest-1",
        },
        "queries": [{"id": "q1", "query": "Q?", "expect_winner": "hybrid-rag",
                     "rationale": "r"}],
        "cells": [
            {"query_id": "q1", "model": "vanilla-rag", "ok": True, "answer": "ans-v"},
            {"query_id": "q1", "model": "hybrid-rag", "ok": True, "answer": "ans-h"},
        ],
    }
    matrix_path = tmp_path / "matrix.json"
    matrix_path.write_text(json.dumps(matrix), encoding="utf-8")
    return matrix_path


@respx.mock
def test_main_aggregates_normalized_verdicts(tmp_path, monkeypatch) -> None:
    matrix_path = _matrix(tmp_path)
    out_path = tmp_path / "judgments.json"
    # RESULTS / <absolute path> resolves to the absolute path (pathlib semantics),
    # so the env seams accept tmp files.
    monkeypatch.setenv("JUDGE_MATRIX_FILE", str(matrix_path))
    monkeypatch.setenv("JUDGE_RESULTS_FILE", str(out_path))

    order = judge.stable_order(["vanilla-rag", "hybrid-rag"], "q1")
    letter = {model: chr(ord("A") + i) for i, model in enumerate(order)}
    hi, lo = letter["hybrid-rag"], letter["vanilla-rag"]
    replies = iter([
        # judge 1 replies sloppily: lowercase letters, string scores, lowercase best
        {"scores": {hi.lower(): "5", lo.lower(): "3"}, "best": hi.lower(), "reason": "x"},
        # judge 2 replies canonically
        {"scores": {hi: 5, lo: 3}, "best": hi, "reason": "y"},
    ])
    respx.post(judge.OLLAMA).mock(side_effect=lambda request: httpx.Response(
        200, json={"choices": [{"message": {"content": json.dumps(next(replies))}}]}))

    judge.main()

    out = json.loads(out_path.read_text(encoding="utf-8"))
    q = out["queries"][0]
    assert q["mean_by_approach"] == {"hybrid-rag": 5.0, "vanilla-rag": 3.0}
    assert q["votes"] == {"hybrid-rag": 2}
    assert q["observed_winner"] == "hybrid-rag"
    assert out["judges"] == judge.JUDGES
    assert out["ingestion"] == {
        "id": "ing-1",
        "profile": "baseline_curated",
        "revision": "rev-1",
        "content_digest": "digest-1",
    }


@respx.mock
def test_main_breaks_mean_ties_by_votes(tmp_path, monkeypatch) -> None:
    matrix_path = _matrix(tmp_path)
    out_path = tmp_path / "judgments.json"
    monkeypatch.setenv("JUDGE_MATRIX_FILE", str(matrix_path))
    monkeypatch.setenv("JUDGE_RESULTS_FILE", str(out_path))

    order = judge.stable_order(["vanilla-rag", "hybrid-rag"], "q1")
    letter = {model: chr(ord("A") + i) for i, model in enumerate(order)}
    hi = letter["hybrid-rag"]
    reply = {"scores": {letter["vanilla-rag"]: 4, hi: 4}, "best": hi, "reason": "tie"}
    respx.post(judge.OLLAMA).mock(return_value=httpx.Response(
        200, json={"choices": [{"message": {"content": json.dumps(reply)}}]}))

    judge.main()

    q = json.loads(out_path.read_text(encoding="utf-8"))["queries"][0]
    assert q["mean_by_approach"] == {"hybrid-rag": 4.0, "vanilla-rag": 4.0}
    assert q["observed_winner"] == "hybrid-rag"  # equal means; votes decide


@respx.mock
def test_main_survives_total_judge_outage_with_empty_verdicts(tmp_path, monkeypatch) -> None:
    # Documents the exit-0 contract on outage (host Ollama down): judgments are
    # still written, with per-judge errors and no means. The dataset ladder's
    # validate_judgments() is the layer that refuses to snapshot such a run.
    matrix_path = _matrix(tmp_path)
    out_path = tmp_path / "judgments.json"
    monkeypatch.setenv("JUDGE_MATRIX_FILE", str(matrix_path))
    monkeypatch.setenv("JUDGE_RESULTS_FILE", str(out_path))
    respx.post(judge.OLLAMA).mock(side_effect=httpx.ConnectError("connection refused"))

    judge.main()

    q = json.loads(out_path.read_text(encoding="utf-8"))["queries"][0]
    assert q["mean_by_approach"] == {}
    assert q["observed_winner"] is None
    assert all("error" in verdict for verdict in q["per_judge"].values())
