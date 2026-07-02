# Adaptive-RAG n8n workflow

## 1. Overview

The Adaptive-RAG workflow is checked in as `adaptive-rag.workflow.json`.
`scripts/start-all.sh` imports it with `--activeState=fromJson`, then restarts n8n
so the production webhook is registered. The backend wrapper at
`backend_plugins/rag/approaches/n8n.py` POSTs `{query}` to this workflow's webhook
and surfaces the chosen `route` in the comparison column.

## 2. Workflow Nodes

1. **Webhook** (POST, path `adaptive-rag`) — receives `{ "query": "..." }`.
2. **Classify** (HTTP Request → `http://litellm:4000/v1/chat/completions`,
   Authorization `Bearer {{ $env.LITELLM_API_KEY }}` — Atlas injects the master
   key into the n8n container under that name — model `qwen3.6:latest`, a name
   LiteLLM registers): prompt "Classify the query as
   `simple` or `complex`. Answer with one word." Output → `route`.
3. **Route** (Code node) maps `complex` to `agentic-rag`, everything else to
   `vanilla-rag`, and builds the backend route URL.
4. **Call Approach** (HTTP Request) calls
   `http://backend:8000/<approach>/v1/chat/completions`.
5. **Shape** (Code node) builds
   `{ "answer": <chosen answer text>, "route": <route>, "approach": <approach> }`.
6. **Respond to Webhook**: return the Shape node's JSON.

The checked-in workflow has `"active": true`. The backend POSTs to the
*production* webhook `/webhook/adaptive-rag`, which n8n registers only for active
workflows. This is why startup imports the workflow and restarts n8n before model
registration.

## 3. Editing the Workflow

If you edit the workflow in the n8n UI, export it back over
`adaptive-rag.workflow.json` before committing. Keep the top-level `id`, `name`,
`active`, and webhook path stable unless you also update
`N8N_ADAPTIVE_WEBHOOK_URL` and the startup import logic.

Potential tuning variables live in the workflow JSON rather than Python:

- classifier model;
- classifier prompt;
- simple/complex route mapping;
- backend approach timeout;
- response shaping.
