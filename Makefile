.PHONY: docs-build docs-check test

docs-build:
	uv run --group docs python -m scripts.docs.build_docs

docs-check:
	uv run --group docs python -m scripts.docs.check_docs

test:
	uv run pytest tests backend_plugins/rag/tests -q
