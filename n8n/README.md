# Adaptive-RAG n8n workflow

Build once in the n8n UI (http://localhost:<N8N_PORT>), then export to
`adaptive-rag.workflow.json` and import on other machines.

Nodes:
1. **Webhook** (POST, path `adaptive-rag`) — receives `{ "query": "..." }`.
2. **LLM Classify** (HTTP Request → `http://litellm:4000/v1/chat/completions`,
   Bearer `LITELLM_MASTER_KEY`, model `qwen3.6`): prompt "Classify the query as
   `simple` or `complex`. Answer with one word." Output → `route`.
3. **IF** node on `route == "complex"`.
   - **true →** HTTP Request to `http://backend:8000/agentic-rag/v1/chat/completions`.
   - **false →** HTTP Request to `http://backend:8000/vanilla-rag/v1/chat/completions`.
4. **Set** node: build `{ "answer": <chosen answer text>, "route": <route> }`.
5. **Respond to Webhook**: return the Set node's JSON.

The wrapper at `backend_plugins/rag/approaches/n8n.py` posts `{query}` here and
surfaces `route` in the comparison column.
