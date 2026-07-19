# Adaptive-RAG n8n workflow

## 1. Overview

The Adaptive-RAG workflow is checked in as `adaptive-rag.workflow.json` and
declared under `n8n_workflows` in `atlas.consumer.yml`. Atlas validates the source,
normalizes its id to `atlas-consumer-adaptive-rag`, imports it idempotently, and
probes its production webhook during startup. The backend wrapper at
`backend_plugins/rag/approaches/n8n.py` POSTs `{query}` to that webhook and surfaces
the chosen route as structured metadata while preserving the selected approach's
answer, sources, and metrics.

## 2. Workflow Nodes

1. **Webhook** (POST, path `adaptive-rag`) — receives `{ "query": "..." }`.
2. **Classify** (HTTP Request → `http://litellm:4000/v1/chat/completions`,
   Authorization `Bearer {{ $env.LITELLM_API_KEY }}` — Atlas injects the master
   key into the n8n container under that name — model `qwen3.6:latest`, a name
   LiteLLM registers, called with `temperature: 0`. Atlas's model catalog supplies
   that model's scoped `request_defaults: {think: false}`, which is load-bearing
   inside the node's 60 s timeout): the prompt classifies the *question* as one word —
   `simple`, or `complex` when it needs multi-step reasoning or synthesis across
   sources. Output → `route`.
3. **Route** (Code node) maps `complex` to `agentic-rag`, everything else to
   `vanilla-rag`, and selects that Atlas-managed LiteLLM alias.
4. **Call Approach** (HTTP Request) calls
   `http://litellm:4000/v1/chat/completions` with `model=<approach>`, so workflow
   routing uses the same public model contract as Open WebUI and the evaluator.
5. **Shape** (Code node) builds
   `{ "answer": <unrendered answer>, "route": <route>, "approach": <approach>,
   "rag_showcase": <delegated structured evidence> }`.
6. **Respond to Webhook**: return the Shape node's JSON.

Both HTTP Request nodes use n8n's default fail-fast behavior. Authentication,
environment-expression, timeout, or delegated-approach failures therefore stop
the execution instead of flowing into Shape as a successful-looking placeholder.
The Compose overlay sets `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` on both `n8n` and
`n8n-worker`, which is required for the runtime-injected `LITELLM_API_KEY`
expression in queue mode. The secret remains outside the workflow JSON. See n8n's
[security environment-variable contract](https://docs.n8n.io/hosting/configuration/environment-variables/security/).

The checked-in workflow has `"active": true`, and the manifest uses
`active: fromJson`. The backend POSTs to the *production* webhook
`/webhook/adaptive-rag`, which n8n registers only for a published workflow.

Atlas owns validation, namespacing, import/update, and the declared readiness probe.
With an operator-issued `N8N_API_KEY`, Atlas can activate the workflow through the
n8n API. n8n 2.28.2 currently imports the workflow as inactive when that key is
absent, despite the normalized JSON carrying `active: true`. Until
[Atlas #514](https://github.com/thekaveh/atlas/issues/514) resolves that upstream,
`scripts/start-all.sh` publishes the Atlas-owned id and reloads n8n once. The
wrapper then performs a real POST and requires a non-empty answer, an allowed
delegated approach, and `rag_showcase.schema_version == 1` before startup succeeds.

The wrapper keeps route choice separate from retrieval evidence. It returns the
delegated chunks and metrics, adds one LLM call for classification, and records
`adaptive: {route, approach}` in the common structured extension. A route label is
never submitted to Atlas Ragas as a grounding context.

## 3. Editing the Workflow

If you edit the workflow in the n8n UI, export it back over
`adaptive-rag.workflow.json` before committing. Keep the top-level `id`, `name`,
`active`, and webhook path stable unless you also update the `n8n_workflows`
declaration, `N8N_ADAPTIVE_WEBHOOK_URL`, and its contract tests. Do not manually
import a second production copy: Atlas owns the namespaced runtime identity.

Potential tuning variables live in the workflow JSON rather than Python:

- classifier model;
- classifier prompt;
- simple/complex route mapping;
- backend approach timeout;
- response shaping.
