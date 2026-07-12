# Adaptive-RAG n8n workflow

## 1. Overview

The Adaptive-RAG workflow is checked in as `adaptive-rag.workflow.json` and
declared under `n8n_workflows` in `atlas.consumer.yml`. Atlas validates the source,
normalizes its id to `atlas-consumer-adaptive-rag`, imports it idempotently, and
probes its production webhook during startup. The backend wrapper at
`backend_plugins/rag/approaches/n8n.py` POSTs `{query}` to that webhook and surfaces
the chosen `route` in the comparison column.

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
   `vanilla-rag`, and builds the backend route URL.
4. **Call Approach** (HTTP Request) calls
   `http://backend:8000/rag/<approach>/v1/chat/completions`.
5. **Shape** (Code node) builds
   `{ "answer": <chosen answer text>, "route": <route>, "approach": <approach> }`.
6. **Respond to Webhook**: return the Shape node's JSON.

The checked-in workflow has `"active": true`, and the manifest uses
`active: fromJson`. The backend POSTs to the *production* webhook
`/webhook/adaptive-rag`, which n8n registers only for a published workflow.

Atlas owns validation, namespacing, import/update, and the declared readiness probe.
With an operator-issued `N8N_API_KEY`, Atlas can activate the workflow through the
n8n API. n8n 2.28.2 currently imports the workflow as inactive when that key is
absent, despite the normalized JSON carrying `active: true`. Until
[Atlas #514](https://github.com/thekaveh/atlas/issues/514) resolves that upstream,
`scripts/start-all.sh` publishes the Atlas-owned id and reloads n8n once. It also
deletes the exact legacy pre-manifest id `adaptiverag00001`, whose stale webhook
database row otherwise blocks the namespaced workflow even after unpublishing. The
foreign-key cascade removes only that retired route. The wrapper then performs a
real POST and requires a non-empty answer before startup succeeds.

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
