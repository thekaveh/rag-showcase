# 7.1 RAG Showcase — Design Spec

- **Date:** 2026-06-25
- **Status:** Historical design artifact — implemented (see deviations below). The code and the [Atlas-reuse assessment](../../atlas-reuse-assessment.md) are authoritative where they differ from this snapshot.
- **Author:** Kaveh (with Claude Code)
- **Numbering:** Appendices A/B keep their as-built letter scheme rather than joining the numbered hierarchy.
- **Related infra:** [Atlas](https://github.com/thekaveh/atlas) — reused as a Git submodule

> **Implementation deviations from this design (the code is authoritative):**
> - The graph approach ships as **`graph-rag`** — a thin wrapper over Atlas's LightRAG server, named to avoid colliding with Atlas's built-in `lightrag` model. (The original design considered reusing Atlas's `lightrag` model as-is.)
> - Ingestion runs **inside the backend container** (`docker exec … python /app/ingest/ingest.py`), not via a `make ingest` target.
> - Registration uses LiteLLM's **`/model/new` admin API** (not `public.llms` rows) and triggers no separate reload — the admin API takes effect immediately.
> - `start-all.sh` passes the full track flags (`--lightrag-source container --tei-reranker-source container-cpu --doc-processor-source disabled`), not just `--track gen-ai-rag`. Docling is disabled by default (Atlas has no CPU-container Docling); ingestion falls back to naive text chunking, with Docling available as an opt-in (`docling-localhost`/`docling-container-gpu`).

---

## 1. Purpose & Goals

This project has **two equally weighted goals**:

1. **A RAG comparison showcase.** A single dashboard where a user fires one question and sees how *six different modern RAG approaches* answer it — side by side, on the **same corpus** and the **same models**, with each approach exposing *why* it answered the way it did (its retrieved chunks / graph hits / agent trace + a uniform metrics footer). The design optimizes for **visible contrast**: every adjacent pair of approaches differs on exactly one axis, so the difference is legible in the output a user reads.

2. **A test-drive of Atlas as reusable infrastructure.** The showcase is a real downstream consumer of Atlas. We deliberately **reuse and minimally extend** existing Atlas services rather than standing up our own, and we capture the friction (or lack of it) as a written assessment that can feed Atlas's roadmap. Where Atlas lacks a clean extension point, we add the *smallest possible generic seam* — never showcase-specific bloat.

### 1.1 Success criteria

- One OpenWebUI multi-model chat shows all six approaches answering the same prompt in parallel columns.
- For each query type in the demo matrix (§3), the intended approach **visibly wins** and the assertion script proves it.
- The whole stack runs **fully local** by default (no cloud key required); cloud is a one-flag upgrade.
- Atlas's tree gains only **two tiny, generic backend hooks** and **no new services**; all RAG logic lives in this (private) repo.
- A written **Atlas-reuse assessment** (§10) exists.

### 1.2 Non-goals (for this iteration)

- A custom comparison dashboard (TUI or web) — **deferred** to a future phase (§12).
- Production hardening, multi-tenant auth, horizontal scale.
- Exhaustive RAG coverage — six approaches chosen for pedagogy, not completeness.
- Promoting any showcase code into Atlas core — **deferred** until a piece proves broadly useful.

---

## 2. The Six Approaches

Each approach is one OpenAI-compatible endpoint, registered as a LiteLLM model so it appears in OpenWebUI's model dropdown. They are implemented as a **self-contained plugin package** mounted into Atlas's backend process (§4).

| Model name | Mechanism | Atlas services used | LLM role (default = local) | Surfaces (the "why") | Distinct axis |
|---|---|---|---|---|---|
| **`vanilla-rag`** | chunk → embed → top-k dense → stuff → 1 call | Weaviate, LiteLLM | `qwen3.6` (gen) + `nomic-embed-text` | retrieved chunks | control: none (baseline) |
| **`hybrid-rag`** | Weaviate native hybrid (BM25+dense, relativeScoreFusion) → TEI rerank → stuff | Weaviate, TEI reranker, LiteLLM | local | reranked top-k chunks | retrieval |
| **`contextual-rag`** | Anthropic's Contextual Retrieval: LLM-written context blurb prepended to each chunk *at ingest*, then hybrid+rerank | Weaviate, TEI, LiteLLM | `gemma4:31b` (blurbs, offline) | the blurb that rescued an ambiguous chunk | context assembly |
| **`graph-rag`** | graph + vector dual retrieval (thin wrapper over Atlas's LightRAG server) | **LightRAG**, Neo4j, pgvector, Redis | `gemma4:31b` (extraction) | entities/relations hit in the KG | index structure |
| **`agentic-rag`** | ReAct loop: decides when/what to retrieve, multi-hop, tool use over Weaviate + LightRAG | LiteLLM, Weaviate, LightRAG | `qwen3.6` (orchestrator) | Thought→Action→Observation trace | control flow (full agent) |
| **`n8n-adaptive-rag`** | semi-agentic **Adaptive-RAG**: route by query complexity (simple → cheap retrieval, complex → multi-step), built visually in n8n | **n8n**, Weaviate, LightRAG, LiteLLM | `qwen3.6` (routing) | the routing decision + path taken | control flow (low-code, routed) |

**LLM routing rationale.** The three retrieval-centric approaches run fully local (cheap, private, latency-tolerant). The two roles where small models historically fail — **graph extraction** (needs reliable structured output) and the **agentic/routing orchestrator** (needs reliable tool-calling) — default to the strongest *local* models available (`gemma4:31b`, `qwen3.6`), with cloud Claude as a one-flag fallback if local quality disappoints. See §7.

**Fairness.** All approaches embed via the same LiteLLM model and read the same source corpus, so vectors are comparable. LightRAG legitimately uses pgvector instead of Weaviate (it's LightRAG's native backend; Weaviate is not a first-class LightRAG vector store) — immaterial to what we contrast (graph vs flat). The **agentic** approach's tools are **corpus-scoped** by default (vector + graph only; web search via SearxNG is an opt-in toggle) so all six answer from the same knowledge.

---

## 3. Visible-Contrast Demo Queries

The corpus (§5) is chosen to support all of these. Each is engineered so one approach visibly wins:

| Query type | Example shape | Who visibly wins | What the user *sees* |
|---|---|---|---|
| **Exact keyword / proper-noun** | "What did *<rare name/date/title>* say about X?" | hybrid, contextual | vanilla retrieves wrong chunks; BM25 leg nails it |
| **Context-starved chunk** | a fact that only resolves with its document context | contextual | the prepended blurb flips a miss into a hit |
| **Thematic / whole-corpus** | "What are the main themes across all the docs?" | graph-rag | flat RAG → shallow list; graph → synthesized themes |
| **Multi-hop / comparative** | "Compare what A and C concluded and reconcile them" | agentic | the trace shows the agent deciding to retrieve (often more than once), then reasoning |
| **Mixed simple+complex batch** | a run of easy and hard queries | n8n-adaptive | routes cheaply on easy, escalates on hard |
| **Simple factoid** | one clean fact | *all tie* | teaches "when is fancy RAG even worth it?" |

This matrix doubles as the **verification assertion set** (§8) and the **demo script**.

---

## 4. Architecture & Reuse Strategy

### 4.1 High-level

```
                          ┌──────────────────────────────────────────────┐
   user ───▶ OpenWebUI ───┤  multi-model chat: one prompt → 6 columns     │
            (reused)      └───────────────────────┬──────────────────────┘
                                                  │ OpenAI /v1 (per model)
                                                  ▼
                                       LiteLLM gateway (reused)
                                       routes each model name to…
                                                  │
                 ┌────────────────────────────────┼───────────────────────────────┐
                 ▼                                 ▼                                ▼
       Atlas backend (reused, + plugin seam)   LightRAG (reused)            n8n (reused)
       backend_plugins/rag/  ◀── mounted        graph+vector RAG            adaptive-RAG
        ├ vanilla  ├ hybrid                      (already a model)          workflow + webhook
        ├ contextual ├ agentic                          │                        │
                 │                                       ▼                        │
                 ├──────────────▶ Weaviate (vectors + BM25)  ◀───────────────────┤
                 ├──────────────▶ TEI reranker                                    │
                 ├──────────────▶ Neo4j (graph) / pgvector  ◀── LightRAG          │
                 └──────────────▶ LiteLLM (embeddings + generation) ◀─────────────┘
```

Everything except `backend_plugins/rag/` and the n8n workflow is **stock Atlas**, brought up by `./start.sh --track gen-ai-rag`.

### 4.2 Reuse mechanism — the backend plugin seam

We reuse and **override/extend** Atlas's backend *without bloating it*, via a generic extension seam (the symmetric analog of Atlas's existing `services/_user/` compose overlay, but for backend routes):

- **Atlas change = two tiny, generic hooks** (added to the backend, on an Atlas feature branch):
  1. **Router plugin loader:** on startup, auto-discover and `include_router()` any routers in a mounted `plugins/` dir. No-op when empty → base Atlas unaffected. ~15 lines, fully general.
  2. **Plugin requirements installer:** `pip install -r plugins/requirements.txt` if present, so `weaviate-client`/`neo4j` never enter Atlas's base deps.
  Both are extension *seams*, not features — they raise cohesion, not lower it, and help any future downstream consumer.
- **Showcase change = a self-contained, high-cohesion package** in *this* repo: `backend_plugins/rag/` (the six approaches + a shared response helper). It runs *inside* the backend process, so it reuses the backend's pre-wired env (`WEAVIATE_URL`, `NEO4J_URI`, `LITELLM_BASE_URL`, `LIGHTRAG_ENDPOINT`, `DOCLING_ENDPOINT`, `REDIS_URL`, …) with **zero re-plumbing**. The package reads the backend's **env**, not its internals → decoupled and portable.
- **Wiring:** a compose override fragment augments the existing `backend` service with the mount + any extra env. It lives in this repo and is exposed to Atlas through the `services/_user/` overlay slot as a **symlink** (showcase owns the file; Atlas auto-discovers it via its existing `_user/*/compose.yml` glob).

This satisfies all four constraints: Atlas stays a submodule; the backend is reused and overridden rather than forked; **no bloat** (RAG logic stays in this repo; Atlas gains only a generic seam); and future promotion-into-Atlas is a copy-paste if a piece proves broadly useful.

### 4.3 Repo shape

```
rag-showcase/                 ← private GitHub repo
├── infra/                    ← Atlas submodule (tracks the RAG feature branch while building; pins a TAG at release)
├── backend_plugins/rag/      ← the six approaches (mounted into Atlas's backend) + requirements.txt
├── corpus/                   ← MultiHop-RAG + hand-picked keyword docs
├── ingest/                   ← loader: corpus → Docling → Weaviate(base+contextual) + LightRAG
├── register/                 ← registers the 6 models via LiteLLM /model/new
├── compose/                  ← backend override fragment (symlinked into infra/services/_user/rag/)
├── n8n/                      ← the adaptive-RAG workflow export + webhook→OpenAI wrapper notes
├── demo/                     ← contrasting query matrix + walkthrough script
├── docs/                     ← this spec, the implementation plan, the Atlas-reuse assessment
├── scripts/{start-all,stop-all}.sh
└── README.md
```

### 4.4 In-network service addresses (stable; independent of `BASE_PORT`)

| Service | In-network address | Auth |
|---|---|---|
| LiteLLM (LLM gateway) | `http://litellm:4000` | `LITELLM_MASTER_KEY` (bearer) |
| Weaviate (vector + BM25) | `http://weaviate:8080` (gRPC `:50051`) | anonymous (in-network) |
| Neo4j (graph) | `bolt://neo4j-graph-db:7687` | `GRAPH_DB_AUTH` |
| LightRAG (graph RAG) | `http://lightrag:9621` | `LIGHTRAG_API_KEY` |
| TEI reranker | `http://tei-reranker:80/rerank` | none |
| Docling (ingest) | `http://docling-gpu:8000/v1/document/convert` | none |
| OpenWebUI (frontend) | `http://open-web-ui:8080` | account |
| Backend (RAG host) | `http://backend:8000` | API key |
| Supabase Postgres (`public.llms`) | `supabase-db:5432` | from `.env` |
| Redis | `redis:6379` | `REDIS_PASSWORD` |

Network: `${PROJECT_NAME}-network` (default `atlas-network`).

---

## 5. Corpus & Ingestion

### 5.1 Corpus — layered, curated, public

- **Backbone: the MultiHop-RAG dataset** (Tang & Yang, 2024) — a news-article corpus plus ready-made multi-hop queries categorized by reasoning type (inference / comparison / temporal / null) with gold answers. Purpose-built for RAG evaluation, so the contrast queries (§3) come largely for free and we inherit a lightweight **eval set** for the future dashboard.
- **Plus a couple of hand-picked keyword-heavy docs** to sharpen the exact-keyword contrast (rare identifiers / titles where the BM25 leg should clearly beat pure dense).

### 5.2 Ingestion — three indexes, one source, one embedding model

```
corpus/ ──▶ Docling (/v1/document/convert) ──▶ structure-aware chunks
                                                 │
        ┌────────────────────────────────────────┼────────────────────────────────┐
        ▼                                          ▼                                ▼
  Weaviate "base"                        Weaviate "contextual"              LightRAG /documents/upload
  (raw chunks, dense + BM25)             (chunks prefixed with a            (builds its own KG in Neo4j
  → vanilla, hybrid                      local-LLM context blurb, offline)  + vectors in pgvector via
  → also the agentic/n8n tool            → contextual-rag                   gemma4:31b extraction)
```

- **vanilla / hybrid** read the Weaviate *base* collection.
- **contextual** reads the *contextual* collection (identical retrieval code; only the chunks differ).
- **graph-rag** delegates to Atlas's LightRAG server, which ingests raw docs and builds the Neo4j graph.
- **agentic / n8n** add **no new index** — they query the existing Weaviate base collection and the LightRAG graph as tools.

Ingestion runs once inside the backend container (`docker exec … python /app/ingest/ingest.py`, driven by `scripts/start-all.sh`). The slow parts (contextual blurbs + LightRAG extraction) are local and offline; expect minutes, gated by health checks.

---

## 6. Model Registration & Frontend Integration

### 6.1 Registration (no Atlas edits beyond the seam)

A `register/` step registers the six approaches as models via LiteLLM's **`/model/new` admin API** (Atlas runs with `STORE_MODEL_IN_DB=True`, so registrations persist), each pointing its `api_base` at the backend plugin's route. They take effect immediately and auto-appear in OpenWebUI (model-list cache TTL ≈ 300 s; set to 0 in dev). The graph approach ships as `graph-rag` — a thin wrapper over Atlas's LightRAG server — rather than reusing Atlas's built-in `lightrag` model.

### 6.2 Frontend — reuse OpenWebUI multi-model chat

OpenWebUI's multi-model chat sends one prompt to N selected models and lays responses out in **parallel columns**; its "Mixture of Agents" mode can additionally merge them via a synthesizer model (a free bonus demo). No custom frontend is built in this iteration.

### 6.3 Uniform "why" surfacing (portable, not OWUI-specific)

Every approach returns its answer plus collapsible structured-markdown sections + a uniform metrics footer, so internals are visible in any OpenAI-compatible client:

```
┌─ hybrid-rag ──────────────────────────────┐
│ <streamed answer>                          │
│ ▸ 🔎 Retrieved context (k=5, reranked)     │
│ ▸ 🧠 Graph entities/relations  (lightrag)  │
│ ▸ 🤖 Agent trace: Thought→Action→Obs (×N)  │
│ ────────────────────────────────────────  │
│ 📊 1.2s · 5 chunks · 1 LLM call · 0 cloud  │
└────────────────────────────────────────────┘
```

The shared response helper guarantees a consistent footer schema across all six (so latency and #calls are eyeball-comparable). The `cloud` count is `0` in the local-first default — an honest placeholder for a future enhancement that would classify cloud-vs-local calls once a role is flipped to a cloud model. OWUI native citations are wired *if cheap*; markdown is the guaranteed-portable baseline.

---

## 7. LLM Roles & Configuration

A single `roles.yaml` maps each role to a LiteLLM model. **Local-first** defaults; flip any value to a cloud model name (once a key is added) to switch — that's the entire local↔cloud change.

```yaml
embed:             nomic-embed-text   # local
light_gen:         qwen3.6            # local — vanilla/hybrid/contextual answers
contextual_blurb:  gemma4:31b         # local, offline ingest
extraction:        gemma4:31b         # local (LightRAG KG)        — cloud fallback: claude-*
agentic:           qwen3.6            # local (orchestrator / n8n) — cloud fallback: claude-*
rerank:            <TEI service>      # not an LLM; mxbai-rerank-base-v1 cross-encoder
```

> **Deviation (corrected in `roles.yaml`):** Atlas's catalog has no `gemma4:31b`, and its LiteLLM registers the default chat model as `qwen3.6:latest` (bare `qwen3.6` does not resolve). The implementation therefore uses `qwen3.6:latest` for the plugin chat roles (`light_gen`, `contextual_blurb`, `agentic`; the LightRAG-side extraction role was later moved to `mistral-small3.2:24b` via Atlas's `LIGHTRAG_*` inputs) and `nomic-embed-text` for `embed`. To use distinct/heavier per-role models, activate them via `start.sh --ollama-models` and name them exactly in `roles.yaml`.

Adding a cloud key is optional and only needed if local extraction/agentic quality is insufficient. (Optional future enhancement: expose `*-local` vs `*-cloud` variants as separate columns to compare *brains*, not just *methods*.)

---

## 8. Startup & Verification

### 8.1 One-command startup (`scripts/start-all.sh`)

1. `cd infra && ./start.sh --track gen-ai-rag` (optional `--cloud` wires a Claude key for the heavy roles).
2. Wait for health on every dependency.
3. `ingest/` loads the corpus into the three indexes.
4. `register/` adds the six models via LiteLLM `/model/new` (effective immediately).
5. Print the OpenWebUI URL.

### 8.2 Verification (evidence, not assertion)

- **Health gate** on every service before ingest.
- **Ingestion smoke test:** object/edge counts in Weaviate + Neo4j are non-zero and plausible.
- **Demo-matrix assertion (§3):** fire each query type and assert the intended approach wins (e.g., on the keyword query, `hybrid-rag` retrieves the gold chunk that `vanilla-rag` misses). This script *is* the demo.
- **Lightweight eval:** run a slice of MultiHop-RAG's gold Q/A through all six and record answer quality + the metrics footer — seeds the future eval dashboard.

---

## 9. Phasing (preview of the implementation plan)

| Phase | Deliverable |
|---|---|
| **P0** | Private GitHub repo + Atlas submodule (Method B) + the two generic backend seams (Atlas feature branch) + `_user/` symlink wiring |
| **P1** | Backend plugin package: `vanilla` → `hybrid` → `contextual` endpoints (local) + shared response helper |
| **P2** | LightRAG ingest + expose as `graph-rag` |
| **P3** | `agentic` endpoint (qwen3.6 orchestrator, corpus-scoped tools) |
| **P4** | n8n adaptive-RAG workflow + webhook→OpenAI wrapper |
| **P5** | Registration + OpenWebUI multi-model wiring + uniform sources/metrics surfacing |
| **P6** | Corpus assembly + demo query matrix + verification + the Atlas-reuse assessment |
| **Deferred (P7+)** | Custom comparison dashboard (TUI or sleek MVVM web); quantitative eval dashboard; promote-to-Atlas decisions |

---

## 10. Atlas Reuse Assessment (a first-class deliverable)

A living document (`docs/atlas-reuse-assessment.md`) capturing, as we build:

- What reused cleanly out of the box (OWUI multi-model, LiteLLM service-as-a-model, gen-ai-rag track, LightRAG-as-a-model, in-network DNS + pre-wired backend env).
- Where friction appeared and what seam we added (the backend router-plugin loader + reqs installer; whether `_user/` overlay merging-into-an-existing-service behaved; first-boot latencies; the `public.llms` registration ergonomics).
- Concrete recommendations for Atlas (e.g., "ship a documented backend plugin seam," "the gen-ai-rag backend should carry vector/graph client libs," "a `--extra-compose` flag would beat the `_user/` symlink").

---

## 11. Risks & Honesty Caveats

- **Local extraction/agentic ceiling.** Graph quality and tool-calling reliability depend on `gemma4:31b` / `qwen3.6`. If a column underperforms on stage, flip that role to cloud (§7). This trade-off is itself part of the showcase's honesty.
- **RAG vs long context.** If the corpus slice is small (<~200k tokens), note that stuffing the whole thing into context is a valid baseline — a teachable "when is RAG worth it?" moment, not a bug.
- **Heterogeneous vector stores.** LightRAG uses pgvector, the others Weaviate. Embeddings + corpus are identical, so the comparison stays fair; we state this explicitly in the demo.
- **In-process plugin.** The RAG package shares the backend's event loop. Fine for a demo; a heavy agentic loop could compete with the backend's other duties. Acceptable at showcase scale; flagged for the assessment.
- **First-boot latency.** LightRAG / TEI / Docling download models on first run (minutes). Startup health-gates before ingest.
- **Cohesion of the seam.** The backend seam must stay generic (load-routers-from-dir). If it accretes RAG-specific logic, that's the bloat we set out to avoid — guard against it in review.

---

## 12. Deferred / Future

- **Custom comparison dashboard** — a TUI or a sleek MVVM-friendly web app: one query → all six, with a metrics table, retrieved-chunk diff, Neo4j graph viz, and an agent-trace timeline. Deferred; OWUI multi-model chat covers the core need now.
- **Quantitative eval dashboard** built on the MultiHop-RAG gold set.
- **More approaches** — RAPTOR (summary tree), full Microsoft GraphRAG, ColPali multimodal (needs a GPU model server outside Ollama).
- **Promote-to-Atlas** — if `backend_plugins/rag/` (or the seam) proves broadly useful, move it into Atlas proper via Atlas's PR/CI flow.

---

## Appendix A — RAG Landscape (research basis)

The six were chosen from a broader survey to maximize *visible* contrast across the four RAG axes (query transform / context assembly / index structure / control flow) while staying self-hostable on Ollama + Weaviate + Neo4j.

- **Naive RAG** — Gao et al. survey, arxiv.org/abs/2312.10997; original RAG, Lewis et al. 2020, arxiv.org/abs/2005.11401.
- **Hybrid + rerank** — Weaviate relativeScoreFusion (the v4 default; RRF — Cormack et al., SIGIR 2009 — is the rank-based alternative); SPLADE, arxiv.org/abs/2107.05720; rerankers: `mxbai-rerank` / `bge-reranker-v2-m3`.
- **Contextual Retrieval** — Anthropic, anthropic.com/news/contextual-retrieval (−35%/−49%/−67% retrieval-failure reductions).
- **LightRAG** — Guo et al., arxiv.org/abs/2410.05779 (HKUDS/LightRAG); dual-level graph+vector, cheap incremental updates.
- **GraphRAG** (context/alternative) — Edge et al., arxiv.org/abs/2404.16130 (microsoft/graphrag); painful to self-host locally → LightRAG chosen instead.
- **Agentic RAG** — survey, arxiv.org/abs/2501.09136; ReAct, arxiv.org/abs/2210.03629.
- **Adaptive-RAG** (the n8n approach) — arxiv.org/abs/2403.14403 (route by query complexity).
- Other surveyed: HyDE (2212.10496), RAG-Fusion (2402.03367), ColBERT/ColPali (2004.12832 / 2407.01449), Self-RAG (2310.11511), CRAG (2401.15884), RAPTOR (2401.18059), Lost-in-the-Middle (2307.03172).
- **Corpus:** MultiHop-RAG (Tang & Yang, 2024) — multi-hop RAG benchmark over a news corpus.

## Appendix B — Key Atlas facts this design relies on

- **Service-as-a-model is built in.** Atlas already registers `lightrag` and `hermes-agent` in LiteLLM as OpenAI-compatible models that appear in OWUI — the existence proof for the whole showcase.
- **`gen-ai-rag` track** enables: open-webui, weaviate, neo4j, lightrag, doc-processor, tei-reranker, searxng, local-deep-researcher (+ always-on LiteLLM, Supabase, Redis, Kong, backend).
- **Backend is live-editable** (source bind-mounted) and **pre-wired** with every RAG dependency's URL + credentials.
- **`public.llms`** (Supabase Postgres) is the LiteLLM model catalog; `litellm-init` renders config from it on startup.
- **`services/_user/` overlay** is auto-discovered (`services/_user/*/compose.yml` added via `-f`) — the mount point for our compose override.
- **LightRAG backends in Atlas:** pgvector (vectors), Neo4j (graph), Redis (KV); LLM/embeddings via LiteLLM.
- **Local models present:** `qwen3.6`, `gemma4:31b`, `nomic-embed-text`, `mxbai-embed-large`, `qwen3-embedding:0.6b`.
