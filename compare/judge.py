#!/usr/bin/env python3
"""Judge panel: score each approach's answer per query using a panel of LOCAL
models on the host Ollama (qwen3.6:latest + gemma4:31b) via the OpenAI-compatible
/v1 endpoint. Answers are shown shuffled and anonymized (Answer A..F) so judges
cannot bias by approach order or name.

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
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "compare" / "results"
OLLAMA = "http://localhost:11434/v1/chat/completions"
JUDGES = ["qwen3.6:latest", "gemma4:31b"]
MAXLEN = 1200  # cap answer length fed to judges


def matrix_file() -> Path:
    return RESULTS / os.environ.get("JUDGE_MATRIX_FILE", "matrix.json")


def judgments_file() -> Path:
    return RESULTS / os.environ.get("JUDGE_RESULTS_FILE", "judgments.json")


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


def ask_judge(client: httpx.Client, model: str, prompt: str) -> dict | None:
    for _ in range(2):  # one retry
        try:
            r = client.post(OLLAMA, json={"model": model, "temperature": 0, "think": False,
                                          "messages": [{"role": "user", "content": prompt}]})
            r.raise_for_status()
            content = r.json()["choices"][0]["message"].get("content") or ""
            parsed = extract_json(content)
            if parsed and isinstance(parsed.get("scores"), dict):
                return parsed
        except Exception:
            continue
    return None


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
        for jm in JUDGES:
            for q in matrix["queries"]:
                qid = q["id"]
                verdict = ask_judge(client, jm, meta[qid]["prompt"])
                if not verdict:
                    print(f"  [{jm}] {qid}: no valid verdict", flush=True)
                    continue
                l2m = meta[qid]["letter_to_model"]
                scores = {l2m[L]: v for L, v in verdict["scores"].items()
                          if L in l2m and isinstance(v, (int, float))}
                raw[(qid, jm)] = {"scores": scores, "best": l2m.get(verdict.get("best", "")),
                                  "reason": verdict.get("reason", "")}
                print(f"  [{jm}] {qid}: best={raw[(qid, jm)]['best']}", flush=True)

    # Aggregate per query: mean score per approach across judges + best-vote tally.
    out: dict = {"judges": JUDGES, "queries": []}
    for q in matrix["queries"]:
        qid = q["id"]
        per_judge = {jm: raw.get((qid, jm), {"error": "no valid verdict"}) for jm in JUDGES}
        agg: dict[str, list[float]] = {}
        votes: dict[str, int] = {}
        for jm in JUDGES:
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
    output.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {output}")


if __name__ == "__main__":
    main()
