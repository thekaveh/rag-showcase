# Adaptive-RAG n8n workflow

## 1. Overview

Build the Adaptive-RAG workflow once in the n8n UI (`http://localhost:<N8N_PORT>`),
then export it to `adaptive-rag.workflow.json` and re-import on other machines.
The backend wrapper at `backend_plugins/rag/approaches/n8n.py` POSTs `{query}` to
this workflow's webhook and surfaces the chosen `route` in the comparison column.

## 2. Workflow Nodes

1. **Webhook** (POST, path `adaptive-rag`) — receives `{ "query": "..." }`.
2. **LLM Classify** (HTTP Request → `http://litellm:4000/v1/chat/completions`,
   Authorization `Bearer {{ $env.LITELLM_API_KEY }}` — Atlas injects the master
   key into the n8n container under that name — model `qwen3.6:latest`, a name
   LiteLLM registers): prompt "Classify the query as
   `simple` or `complex`. Answer with one word." Output → `route`.
3. **IF** node on `route == "complex"`.
   - **true →** HTTP Request to `http://backend:8000/agentic-rag/v1/chat/completions`.
   - **false →** HTTP Request to `http://backend:8000/vanilla-rag/v1/chat/completions`.
4. **Set** node: build `{ "answer": <chosen answer text>, "route": <route> }`.
5. **Respond to Webhook**: return the Set node's JSON.

After wiring the nodes, **toggle the workflow Active** (top-right switch in the
editor). The backend POSTs to the *production* webhook `/webhook/adaptive-rag`,
which n8n registers only for an active workflow — an inactive one returns 404 and
the `n8n-adaptive-rag` column errors.

## 3. Re-importing on Another Machine

Import `adaptive-rag.workflow.json` via the n8n UI (Workflows → Import from File),
then toggle it **Active** (the production webhook only registers for active
workflows). The checked-in file is an empty placeholder until you export your
built workflow over it.
