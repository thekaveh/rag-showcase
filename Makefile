.PHONY: docs-build docs-check test lint sortable-tables-test eval-check

docs-build:
	uv run --group docs python -m scripts.docs.build_docs

docs-check:
	uv run --group docs python -m scripts.docs.check_docs

test:
	uv run pytest tests backend_plugins/rag/tests -q

lint:
	uv run ruff check .

sortable-tables-test:
	node --test tests/docs/test_sortable_tables.cjs

# Read-only preflight: confirm the evaluation's Atlas-infra dependencies are up
# and in order (LiteLLM aliases, Weaviate + collections, LightRAG, TEI reranker,
# n8n) WITHOUT running ingestion, any approach, or the LLM judge. Needs a running
# stack for the live probes; the Atlas doctor phase is static.
eval-check:
	uv run python -m scripts.eval_preflight
