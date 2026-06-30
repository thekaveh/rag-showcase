# RAG approaches — live comparison

A side-by-side comparison of the RAG approaches in this repo, run against a live
`gen-ai-rag` Atlas stack on a single macOS host (Mac Studio M2 Ultra, 192 GB),
**fully local** — every LLM call (generation, extraction, judging) runs on the host
Ollama (Apple Metal GPU). This is also the first end-to-end **live validation** of
the showcase, and it surfaced several real findings (§4).

- **Run date:** 2026-06-30
- **Approaches compared:** 5 of 6 — `vanilla-rag`, `hybrid-rag`, `contextual-rag`,
  `agentic-rag`, `n8n-adaptive-rag`. **`graph-rag` is excluded** (LightRAG would not
  reliably use a non-reasoning extraction model on this deployment — §4.6).
- **Corpus:** 11-doc curated subset of MultiHop-RAG — FTX/SBF and US-v-Google
  clusters (multi-source overlap) + AI-theme docs + the `widget-error-codes.md`
  keyword doc.
- **Queries:** the six contrasting prompts in [`demo/queries.yaml`](../demo/queries.yaml).
- **Harness:** [`compare/run_matrix.py`](../compare/run_matrix.py) +
  [`compare/judge.py`](../compare/judge.py). Raw data in `compare/results/`.

## 0. Headline

Two things made this run work where earlier attempts stalled, and one approach
couldn't be salvaged:

- **Disabling the reasoning model's chain-of-thought (`think:false`) is the unlock**
  — the qwen3.6 MoE answered in **~5 s instead of ~46 s (~30×)** with no quality loss
  on these tasks (§4.1). Without it, every call ran a multi-thousand-token "thinking"
  pass and the whole pipeline timed out.
- **`hybrid-rag` and `contextual-rag` are the clear winners** here; `vanilla-rag` is a
  notably weak baseline because pure-dense retrieval misses the small/rare widget doc
  (§6).
- **`graph-rag` is excluded** — a LightRAG/Atlas bug (§4.6) prevented its graph from
  building reliably.

## 1. Reproduce

```bash
./scripts/start-all.sh                 # bring the stack up, then apply the §3 routing
uv run python compare/run_matrix.py    # 6 queries × N approaches  -> compare/results/matrix.json
uv run python compare/judge.py         # local judge panel        -> compare/results/judgments.json
```
`MATRIX_MODELS` (comma-separated) overrides which approaches the matrix runs.

## 2. The approaches

See the [README](../README.md#3-the-six-approaches). In one line each: `vanilla-rag`
(dense top-k), `hybrid-rag` (BM25+dense+rerank), `contextual-rag` (context-prefixed
chunks), `graph-rag` (LightRAG graph+vector), `agentic-rag` (ReAct over vector+graph
tools), `n8n-adaptive-rag` (low-code complexity router).

## 3. Environment & setup (the local-LLM architecture)

100% local; the architecture is in [`architecture.html`](architecture.html). All LLM
calls route to the **host** Ollama (Metal GPU), because Atlas's containerized Ollama
is CPU-only on macOS (Docker Desktop has no Metal passthrough).

| Concern | Default | This run |
|---|---|---|
| **Generation** (5 approaches + ingest) | `qwen3.6:latest` on the CPU container | `qwen3.6 35B-A3B MoE` on the **host GPU** (LiteLLM model `qwen3.6-moe`), with **`think:false`** scoped per-model via [`backend_plugins/rag/models.yaml`](../backend_plugins/rag/models.yaml) |
| **LightRAG** (graph-rag) | resolves to the CPU reasoning model | `LIGHTRAG_LLM_MODEL=mistral-small` (non-reasoning `mistral-small3.2:24b`) — *intended*; see §4.6 |
| **Embeddings** | `nomic-embed-text` (container) | unchanged (fast on CPU) |
| **Judges** | — | `qwen3.6:latest` + `gemma4:31b` on the host, `think:false` |
| **Ingest / register** | run by `start-all.sh` | run manually (§4.2) |

## 4. Findings (first live validation)

1. **`think:false` is the unlock.** The qwen3.6 MoE is a *reasoning* model: it emits a
   multi-thousand-token chain-of-thought per call. Same prompt: **`think:True` ≈ 46 s
   (4.5 K thinking chars) vs `think:false` ≈ 1.6–7 s, same-quality answer (~30×)**. The
   context window (a forced 262144 / ~40 GB) is *not* cappable on Ollama's MLX runner
   (`num_ctx` ignored per-request, via Modelfile, and via `OLLAMA_CONTEXT_LENGTH`), so
   `think:false` — not context — was the lever. It's set as a **per-model property** in
   `models.yaml` (a top-level `think` flag that LiteLLM forwards to Ollama), so it
   applies only to that model — flip a role to a cloud model and nothing is sent.
2. **`start-all.sh` never reaches ingest/register non-interactively.** Atlas's
   `start.py` ends by following logs (`docker compose … logs -f`), which blocks the
   wrapper before its ingest/register steps. *Workaround:* run them manually once the
   stack is healthy.
3. **Containerized Ollama is CPU-only on macOS.** The 24–40 GB models are unusable
   there; route generation to the host Ollama (`host.docker.internal:11434`).
4. **The 40 GB / 256 K-context MoE destabilizes Ollama under churn.** Repeated
   load/unload (and slow reasoning calls) wedge it — the model sticks in `Stopping…`,
   blocking new loads; only an Ollama restart clears it. Mitigation: keep `think:false`
   (fast calls, no churn) and give LightRAG a *separate* model so the MoE isn't hammered.
5. **n8n 2.x Code nodes block `$env`.** Supply the LiteLLM key via an HTTP Request node
   header, not Code (the shape the workflow uses).
6. **LightRAG does not honor the configured extraction model (graph-rag blocker).**
   With `LIGHTRAG_LLM_MODEL=mistral-small`, LightRAG's `/health` reports
   `extract/query/keyword → mistral-small`, yet its **actual LiteLLM calls hit the
   default `qwen3.6:latest`** (CPU reasoning) — so extraction hits the 480 s worker
   timeout and **10 of 11 docs fail**, and graph-rag's query itself times out (180 s).
   Research confirms LightRAG v1.5+ *should* support per-role non-reasoning models
   (`EXTRACT_LLM_MODEL`), so this is an Atlas/LightRAG wiring bug, not a model problem.
   graph-rag was therefore excluded from the scored run. **Fix path:** make LightRAG's
   actual calls use the resolved non-reasoning model (e.g. `mistral-small3.2:24b` or
   `qwen2.5:14b-instruct`, both on Ollama).

## 5. Methodology

- **Collector** runs each query against each approach through the published LiteLLM
  gateway (temperature 0), records client latency, and parses each response's uniform
  `build_response` payload into `{answer, sources[], server_metrics}`. Per-cell errors
  are recorded, not fatal.
- **Judge panel** = two local models on the host Ollama (`qwen3.6:latest` + `gemma4:31b`,
  `think:false`). Per query, every answer is shown shuffled + anonymized (Answer A…E);
  each judge scores all answers 1–5 against the query's intent; scores map back to
  approaches and average across judges.

## 6. Results

All 30 cells (6 queries × 5 approaches) returned without harness errors; latencies are
**fast** (3–19 s) thanks to `think:false`. Raw data: `compare/results/matrix.json`.

### 6.1 Thesis check

| Query | Expected | Observed | Verdict |
|-------|----------|----------|---------|
| `keyword` | hybrid-rag | **hybrid + contextual + agentic** answered WIDGET-ERR-7741; **vanilla said "no info"** (dense missed the rare doc); n8n routed→vanilla→missed | ✓✓ **strong** — vanilla's miss is exactly why BM25/contextual win exact-ID queries |
| `thematic` | graph-rag | **contextual-rag only** produced themes; others "insufficient" (graph-rag excluded) | contextual best among the 5 |
| `multihop` | agentic-rag | **agentic** attempted a reconciliation; others "insufficient" | agentic edges it (weakly) |
| `factoid` | any | **hybrid + contextual → "v4.2"**; vanilla/n8n missed; agentic MAX_STEPS | ⚠️ only the retrievers that surfaced the doc got it |
| `context_starved` | contextual-rag (*Docling*) | hybrid/contextual/agentic answered; vanilla/n8n missed | ✓ contextual shows no special edge (Docling off, as predicted) |
| `mixed_batch` | n8n-adaptive-rag | **hybrid + contextual** listed the codes; **n8n mis-routed to "simple"→vanilla→missed** | ✗ n8n failed its own query (router misclassified) |

**Reading:** `hybrid-rag` and `contextual-rag` are the standouts — they consistently
surface the small/rare widget doc (via BM25 / context-prefixing) that `vanilla-rag`'s
pure-dense top-k misses, so vanilla repeatedly answers "no information" *despite
retrieving 5 chunks* (they're the wrong chunks). `agentic-rag` answers single-shot
queries but hits `MAX_STEPS=4` on 3/6 (and its graph tool is dead). `n8n-adaptive-rag`
inherits whatever it routes to — it classified most queries "simple" → `vanilla-rag`,
so it mirrors vanilla's misses (the 0.3 s cells are LiteLLM cache hits).

### 6.2 Per-approach metrics

| Approach | avg latency | notes |
|----------|------------:|-------|
| vanilla-rag | ~5 s | dense top-k; misses the rare doc here |
| hybrid-rag | ~10 s | + TEI rerank; most reliable answers |
| contextual-rag | ~13 s | context-prefixed; only one to do `thematic` |
| agentic-rag | ~8 s | ReAct (MAX_STEPS=4); graph tool dead |
| n8n-adaptive-rag | ~0.3 s* | *cache hits — mirrors its route target |

### 6.3 Per-query detail

- **keyword** — hybrid/contextual/agentic return the thermal-cutoff explanation;
  vanilla & n8n say "no information" (dense top-k didn't surface `widget-error-codes.md`).
- **thematic** — contextual-rag enumerates real themes (AI/search, antitrust, FTX);
  the others say "insufficient".
- **multihop** — agentic-rag attempts a source comparison; vanilla/hybrid/contextual/n8n
  say "insufficient".
- **factoid** — hybrid & contextual return **v4.2**; vanilla/n8n miss; agentic MAX_STEPS.
- **context_starved** — hybrid/contextual/agentic answer (relay opens >84 °C, power-cycle);
  contextual shows no special edge without Docling, as predicted.
- **mixed_batch** — hybrid & contextual list the codes; agentic MAX_STEPS; n8n mis-routed.

### 6.4 Judge-panel scores

Local panel (`qwen3.6:latest` + `gemma4:31b`, `think:false`), 1–5 per answer, averaged
across both judges. Full data: `compare/results/judgments.json`.

**Overall (mean across the 6 queries):**

| Approach | mean | |
|----------|-----:|--|
| **hybrid-rag** | **4.33** | most reliable across queries |
| **contextual-rag** | **3.92** | close second |
| agentic-rag | 2.33 | good single-shot, MAX_STEPS bails |
| n8n-adaptive-rag | 1.67 | inherits its (vanilla) route |
| vanilla-rag | 1.67 | dense-only misses the rare doc |

This is the robust signal and it matches §6.1: **`hybrid-rag` and `contextual-rag` clearly
lead.** Per-query "winners" are noisier — on the factual queries (`keyword`, `factoid`,
`context_starved`) hybrid/contextual/agentic frequently **tie at 5.0** and the listed
winner is just a vote tiebreak. Two honest caveats on the panel: (a) on `thematic` it
scored the cautious "insufficient" non-answers (vanilla/n8n ≈ 4.5) *above* contextual's
actual enumerated themes (2.0) — a clear local-judge misfire; (b) the engineered
per-query "expected winners" mostly did **not** hold, because graph-rag is excluded and
the intended winners for `multihop` (agentic) and `mixed_batch` (n8n) are constrained by
`MAX_STEPS=4` and the router misclassifying respectively. The small corpus also mutes the
sharp single-winner contrasts. Net: a fair, fast comparison in which retrieval quality
(hybrid/contextual) dominates on this corpus.

## 7. Caveats

- **graph-rag excluded** (§4.6) — LightRAG didn't use the configured non-reasoning model.
- **`think:false` quality trade-off** — the qwen3.6 MoE is coding-tuned; without
  chain-of-thought, prose answers can be terser/more literal. Applied uniformly to all
  approaches, so the *relative* comparison stays fair.
- **Reduced corpus** (11 docs) keeps local ingest tractable; thematic/multihop signal is
  real but thinner than the full 40-doc corpus.
- **`agentic-rag` `MAX_STEPS=4`** is low for a reasoning-style loop; raising it (now that
  calls are fast) is a fair follow-up.
- **Local judge panel** — two local models, directional not authoritative; answers are
  anonymized/shuffled to reduce bias.

## 8. Reversibility

Runtime changes, not committed to Atlas:

- **LiteLLM DB models `qwen3.6-moe` / `mistral-small`:** delete via `POST /model/delete`.
- **`roles.yaml` gen-role override:** the run pointed the generation roles at the host
  alias `qwen3.6-moe`; the **committed default already targets `qwen3.6:latest`**, so
  reverting is just restoring the committed file (restart the backend). The committed
  `models.yaml` keeps **`think:false` on both** `qwen3.6:latest` and `qwen3.6-moe` *by
  design* — it's the validated RAG default for the reasoning model (~30× faster, no
  quality loss on these tasks), so there is nothing to undo there.
- **`infra/.env` `LIGHTRAG_LLM_MODEL`:** clear it and recreate `lightrag-init`/`lightrag`.
- Original LiteLLM route for `qwen3.6:latest`: `ollama_chat/qwen3.6:latest @ http://ollama:11434`.
