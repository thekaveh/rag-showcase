#!/usr/bin/env python3
"""Judge panel: score each approach's answer per query through a configurable
OpenAI-compatible endpoint. Answers are shown shuffled and anonymized (one letter per answer —
A, B, C, …) so judges cannot bias by approach order or name.

Batched by judge model — all of a dataset's queries for one judge before switching —
so each ~20-38 GB model loads ONCE instead of swapping every call (Ollama keeps only
a couple models resident, so per-call alternation thrashes/stalls). Reads
compare/results/matrix.json, writes compare/results/judgments.json by default.

    uv run python compare/judge.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from compare.evaluation import load_manifest  # noqa: E402

RESULTS = ROOT / "compare" / "results"
OLLAMA = "http://localhost:11434/v1/chat/completions"
JUDGES = ["qwen3.6:latest", "gemma4:31b"]
MAXLEN = 1200  # cap answer length fed to judges
DEFAULT_MANIFEST = ROOT / "compare" / "evaluation.yaml"


def matrix_file() -> Path:
    return RESULTS / os.environ.get("JUDGE_MATRIX_FILE", "matrix.json")


def judgments_file() -> Path:
    return RESULTS / os.environ.get("JUDGE_RESULTS_FILE", "judgments.json")


def judge_models() -> list[str]:
    if configured := os.environ.get("JUDGE_MODELS"):
        return list(dict.fromkeys(model.strip() for model in configured.split(",") if model.strip()))
    path = Path(os.environ.get("JUDGE_MANIFEST_FILE", str(DEFAULT_MANIFEST)))
    if not path.is_absolute():
        path = ROOT / path
    panel = load_manifest(path).metrics.judge_panel
    return list(panel.models) if panel.enabled else []


def judge_runtime() -> tuple[str, float, bool | None, dict[str, str]]:
    path = Path(os.environ.get("JUDGE_MANIFEST_FILE", str(DEFAULT_MANIFEST)))
    if not path.is_absolute():
        path = ROOT / path
    panel = load_manifest(path).metrics.judge_panel
    endpoint = os.environ.get("JUDGE_ENDPOINT") or panel.endpoint
    if not endpoint:
        raise ValueError("judge endpoint is required when the judge panel is enabled")

    thinking = panel.thinking
    if configured := os.environ.get("JUDGE_THINK"):
        normalized = configured.strip().lower()
        if normalized == "omit":
            thinking = None
        elif normalized in {"true", "false"}:
            thinking = normalized == "true"
        else:
            raise ValueError("JUDGE_THINK must be true, false, or omit")

    headers: dict[str, str] = {}
    if api_key := os.environ.get("JUDGE_API_KEY"):
        headers["Authorization"] = f"Bearer {api_key}"
    return endpoint, panel.temperature, thinking, headers


def stable_order(items: list[str], seed: str) -> list[str]:
    """Deterministic shuffle: order by hash(seed+item). Reproducible across runs."""
    return sorted(items, key=lambda x: hashlib.sha1((seed + x).encode()).hexdigest())


def extract_json(text: str) -> dict | None:
    t = re.sub(r"```(?:json)?", "", text).strip()
    i, j = t.find("{"), t.rfind("}")
    if i != -1 and j > i:
        try:
            return json.loads(t[i:j + 1])
        except Exception:
            return None
    return None


def ask_judge(
    client: httpx.Client,
    model: str,
    prompt: str,
    *,
    endpoint: str,
    temperature: float,
    thinking: bool | None,
    headers: dict[str, str],
) -> tuple[dict | None, str]:
    """One judge call with one retry. Returns (verdict, failure_detail).

    The detail matters operationally: connection-refused (host Ollama not running),
    timeouts, HTTP errors, and unparseable replies previously all collapsed into the
    same silent None, leaving "no valid verdict" undiagnosable.
    """
    last = ""
    for _ in range(2):  # one retry
        try:
            payload = {
                "model": model,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}],
            }
            if thinking is not None:
                payload["think"] = thinking
            r = client.post(endpoint, headers=headers, json=payload)
            r.raise_for_status()
            content = r.json()["choices"][0]["message"].get("content") or ""
            parsed = extract_json(content)
            if parsed and isinstance(parsed.get("scores"), dict):
                return parsed, ""
            last = "reply contained no scores JSON"
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
    return None, last


def normalize_verdict(verdict: dict, letter_to_model: dict[str, str]) -> dict:
    """Map a raw judge verdict onto model names, tolerantly.

    Judges reply with letter keys that may be lowercased and scores that may be
    numeric strings — accept both. Booleans are rejected explicitly (bool is an int
    subclass; a judge answering true/false must not become a 1.0/0.0 score).
    """
    scores: dict[str, float] = {}
    for letter, value in verdict.get("scores", {}).items():
        model = letter_to_model.get(str(letter).strip().upper())
        if model is None or isinstance(value, bool):
            continue
        try:
            scores[model] = float(value)
        except (TypeError, ValueError):
            continue
    best = letter_to_model.get(str(verdict.get("best") or "").strip().upper())
    return {"scores": scores, "best": best, "reason": verdict.get("reason", "")}


def build_prompt(query: str, rationale: str, labeled: list[tuple[str, str]]) -> str:
    blocks = "\n\n".join(f"Answer {L}:\n\"\"\"\n{a[:MAXLEN]}\n\"\"\"" for L, a in labeled)
    letters = ", ".join(f'"{L}": <1-5>' for L, _ in labeled)
    return (
        "You are judging answers from different retrieval-augmented systems to ONE question.\n\n"
        f"QUESTION:\n{query}\n\n"
        f"WHAT A STRONG ANSWER REQUIRES HERE:\n{rationale}\n\n"
        "Score EACH answer from 1 to 5 on how well it satisfies THIS question "
        "(5 = excellent: directly answers, specific, grounded in real detail; "
        "3 = partial/generic; 1 = irrelevant, empty, or an error message).\n\n"
        f"{blocks}\n\n"
        "Respond with ONLY this JSON and nothing else:\n"
        f'{{"scores": {{{letters}}}, "best": "<letter>", "reason": "<one short sentence>"}}'
    )


def main() -> None:
    matrix = json.loads(matrix_file().read_text(encoding="utf-8"))
    panel = judge_models()
    if not panel:
        out = {
            "status": "disabled",
            "dataset_id": matrix.get("dataset_id"),
            "judges": [],
            "queries": [],
        }
        if matrix.get("ingestion"):
            out["ingestion"] = matrix["ingestion"]
        output = judgments_file()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"wrote {output} (judge panel disabled)")
        return
    endpoint, temperature, thinking, headers = judge_runtime()
    by_q: dict[str, dict[str, dict]] = {}
    for c in matrix["cells"]:
        by_q.setdefault(c["query_id"], {})[c["model"]] = c

    # Pre-build the anonymized, shuffled answer set per query (stable across judges).
    meta: dict[str, dict] = {}
    for q in matrix["queries"]:
        qid = q["id"]
        cells = by_q.get(qid, {})
        models = stable_order(list(cells.keys()), qid)
        labeled, letter_to_model = [], {}
        for n, model in enumerate(models):
            L = chr(ord("A") + n)
            letter_to_model[L] = model
            ans = cells[model].get("answer") if cells[model].get("ok") else None
            labeled.append((L, ans or "(no answer — this approach returned an error)"))
        meta[qid] = {"q": q, "labeled": labeled, "letter_to_model": letter_to_model,
                     "prompt": build_prompt(q["query"], q.get("rationale") or "A direct, correct answer.", labeled)}

    # Batch by judge model: each big model loads once, then scores every query in the matrix.
    raw: dict[tuple[str, str], dict] = {}
    with httpx.Client(timeout=httpx.Timeout(200.0, connect=10.0)) as client:
        for jm in panel:
            for q in matrix["queries"]:
                qid = q["id"]
                verdict, err = ask_judge(
                    client,
                    jm,
                    meta[qid]["prompt"],
                    endpoint=endpoint,
                    temperature=temperature,
                    thinking=thinking,
                    headers=headers,
                )
                if not verdict:
                    print(f"  [{jm}] {qid}: no valid verdict ({err})", flush=True)
                    continue
                raw[(qid, jm)] = normalize_verdict(verdict, meta[qid]["letter_to_model"])
                print(f"  [{jm}] {qid}: best={raw[(qid, jm)]['best']}", flush=True)

    # Aggregate per query: mean score per approach across judges + best-vote tally.
    out: dict = {
        "status": "ok",
        "dataset_id": matrix.get("dataset_id"),
        "judges": panel,
        "queries": [],
    }
    if matrix.get("ingestion"):
        out["ingestion"] = matrix["ingestion"]
    for q in matrix["queries"]:
        qid = q["id"]
        per_judge = {jm: raw.get((qid, jm), {"error": "no valid verdict"}) for jm in panel}
        agg: dict[str, list[float]] = {}
        votes: dict[str, int] = {}
        for jm in panel:
            v = raw.get((qid, jm))
            if not v:
                continue
            for model, s in v["scores"].items():
                agg.setdefault(model, []).append(float(s))
            if v.get("best"):
                votes[v["best"]] = votes.get(v["best"], 0) + 1
        mean = {m: round(sum(xs) / len(xs), 2) for m, xs in agg.items() if xs}
        winner = max(mean, key=lambda m: (mean[m], votes.get(m, 0))) if mean else None
        out["queries"].append({
            "query_id": qid, "query": q["query"], "expect_winner": q.get("expect_winner"),
            "per_judge": per_judge, "mean_by_approach": mean, "votes": votes,
            "observed_winner": winner,
        })
        print(f"  [{qid}] winner={winner} mean={mean}", flush=True)

    output = judgments_file()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {output}")


if __name__ == "__main__":
    import argparse

    # Zero-option parser: config is env-var-only, but this makes --help safe and
    # informative (it used to start a real judging run) and rejects stray arguments.
    argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Configured via env vars: JUDGE_MATRIX_FILE, JUDGE_RESULTS_FILE, "
               "JUDGE_MANIFEST_FILE, JUDGE_MODELS, JUDGE_ENDPOINT, JUDGE_API_KEY, "
               "JUDGE_THINK (true, false, or omit).",
    ).parse_args()
    main()
