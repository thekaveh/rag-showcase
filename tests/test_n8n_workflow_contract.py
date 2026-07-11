"""Static contract pin between the committed n8n workflow and its plugin wrapper.

backend_plugins/rag/tests/test_n8n.py mocks the webhook's {answer, route} response —
a mock encodes a belief. These tests pin that belief to the committed workflow JSON,
so an operator edit renaming a Shape field or the webhook path fails here instead of
breaking production with a green suite.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _workflow() -> dict:
    return json.loads(
        (ROOT / "n8n" / "adaptive-rag.workflow.json").read_text(encoding="utf-8"))


def _node(wf: dict, name: str) -> dict:
    return next(n for n in wf["nodes"] if n["name"] == name)


def test_webhook_matches_wrapper_default_url() -> None:
    # approaches/n8n.py defaults to POST http://n8n:5678/webhook/adaptive-rag
    webhook = _node(_workflow(), "Webhook")
    assert webhook["parameters"]["httpMethod"] == "POST"
    assert webhook["parameters"]["path"] == "adaptive-rag"


def test_shape_node_emits_the_fields_the_wrapper_parses() -> None:
    wf = _workflow()
    js = _node(wf, "Shape")["parameters"]["jsCode"]
    # the wrapper reads data.get("answer") and data.get("route"); assert the
    # emitted OBJECT KEYS (colon forms) — the bare word "answer" also appears in
    # the node's fallback error text, which would keep a key rename green.
    assert "answer:" in js and "route:" in js
    respond = _node(wf, "Respond to Webhook")
    # firstIncomingItem returns ONE object (the wrapper also tolerates a list,
    # but the committed workflow should keep the simple shape)
    assert respond["parameters"]["respondWith"] == "firstIncomingItem"


def test_workflow_is_active_for_fromjson_import() -> None:
    # start-all.sh imports with --activeState=fromJson and relies on the file
    # carrying active:true, then restarts n8n to register the production webhook.
    assert _workflow()["active"] is True


def test_classify_node_delegates_model_defaults_to_litellm() -> None:
    # Atlas's qwen3.6 catalog entry owns think:false. The workflow specifies only
    # approach-level request arguments so model defaults stay provider-scoped.
    body = _node(_workflow(), "Classify")["parameters"]["jsonBody"]
    assert "qwen3.6:latest" in body
    assert "think" not in body


def test_route_node_targets_registered_base_approaches() -> None:
    js = _node(_workflow(), "Route")["parameters"]["jsCode"]
    assert "agentic-rag" in js and "vanilla-rag" in js
