"""LLM rubric-upgrade tests for VoiceHire evaluator.

All provider calls are stubbed with httpx.MockTransport — no network, no
real API keys. The deterministic evaluator is the baseline; the LLM may
only rewrite the prose (strengths / gaps / better_answer), never scores
or quoted evidence, and any provider failure must fall back silently.
Run: pytest backend/tests/test_llm_evaluator.py -q
"""
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx

from app.questions import QUESTIONS
from app.services.evaluator import (
    evaluate,
    llm_feedback,
    resolve_llm_provider,
)

Q = QUESTIONS["javascript"][0]
ANSWER = (
    "JavaScript is single-threaded. The call stack runs synchronous code first "
    "while async callbacks wait in the callback queue and task queue. Promises "
    "go to the higher-priority microtask queue. The event loop moves the next "
    "callback in only when the stack is empty."
)

FEEDBACK = {
    "strengths": ["LLM: clear microtask explanation"],
    "gaps": ["LLM: missed the task queue ordering"],
    "better_answer": "LLM: a stronger answer would contrast microtasks and tasks.",
}


def _stub_client(payload=None, *, text=None, status=200, exc=None, capture=None):
    def handler(request: httpx.Request) -> httpx.Response:
        if capture is not None:
            capture.append(str(request.url))
        if exc is not None:
            raise exc
        if text is not None:
            return httpx.Response(status, text=text)
        return httpx.Response(status, json=payload)

    return httpx.Client(transport=httpx.MockTransport(handler))


def _gemini_payload():
    return {"candidates": [{"content": {"parts": [{"text": json.dumps(FEEDBACK)}]}}]}


def _openai_payload():
    return {"choices": [{"message": {"content": json.dumps(FEEDBACK)}}]}


def test_deterministic_default_unchanged():
    strong_answer = (
        "JavaScript is single-threaded. The call stack runs synchronous code first "
        "while async callbacks wait in the callback queue and task queue. Promises "
        "go to the higher-priority microtask queue. The event loop moves the next "
        "callback in only when the stack is empty, making execution non-blocking "
        "and asynchronous."
    )
    ev = evaluate(Q, strong_answer)
    assert ev.scores["completeness"] >= 9
    assert ev.evidence["microtask queue"] is not None
    assert "microtask" in ev.evidence["microtask queue"].lower()
    assert any("7/7 key concepts" in s for s in ev.strengths)


def test_llm_feedback_merges_valid_gemini():
    capture = []
    client = _stub_client(_gemini_payload(), capture=capture)
    llm = lambda q, a, r: llm_feedback(q, a, r, provider="gemini",
                                       api_key="test-key", client=client)
    base = evaluate(Q, ANSWER)
    upgraded = evaluate(Q, ANSWER, llm=llm)
    assert upgraded.strengths == FEEDBACK["strengths"]
    assert upgraded.gaps == FEEDBACK["gaps"]
    assert upgraded.better_answer == FEEDBACK["better_answer"]
    # Scores and quoted evidence are never rewritten by the LLM.
    assert upgraded.scores == base.scores
    assert upgraded.overall == base.overall
    assert upgraded.evidence == base.evidence
    assert upgraded.covered == base.covered
    assert capture and "generativelanguage.googleapis.com" in capture[0]


def test_llm_feedback_merges_valid_openai():
    capture = []
    client = _stub_client(_openai_payload(), capture=capture)
    llm = lambda q, a, r: llm_feedback(q, a, r, provider="openai",
                                       api_key="test-key", client=client)
    upgraded = evaluate(Q, ANSWER, llm=llm)
    assert upgraded.strengths == FEEDBACK["strengths"]
    assert capture and "api.openai.com" in capture[0]


def test_llm_feedback_falls_back_on_bad_json():
    client = _stub_client(text="not json at all")
    llm = lambda q, a, r: llm_feedback(q, a, r, provider="gemini",
                                       api_key="test-key", client=client)
    base = evaluate(Q, ANSWER)
    assert evaluate(Q, ANSWER, llm=llm).strengths == base.strengths


def test_llm_feedback_falls_back_on_http_error():
    client = _stub_client(exc=httpx.ConnectError("boom", request=httpx.Request("POST", "https://x")))
    llm = lambda q, a, r: llm_feedback(q, a, r, provider="gemini",
                                       api_key="test-key", client=client)
    base = evaluate(Q, ANSWER)
    assert evaluate(Q, ANSWER, llm=llm).strengths == base.strengths


def test_llm_feedback_rejects_bad_shape():
    bad = {"strengths": ["ok"], "gaps": []}  # missing better_answer
    client = _stub_client(_gemini_payload() | {"candidates": [{"content": {"parts": [{"text": json.dumps(bad)}]}}]})
    assert llm_feedback(Q, ANSWER, evaluate(Q, ANSWER),
                        provider="gemini", api_key="test-key", client=client) is None
    # Unknown provider / missing key -> None without any request.
    assert llm_feedback(Q, ANSWER, evaluate(Q, ANSWER),
                        provider="mock", api_key="x") is None
    assert llm_feedback(Q, ANSWER, evaluate(Q, ANSWER),
                        provider="gemini", api_key="") is None


def test_resolve_llm_provider():
    assert resolve_llm_provider("mock") is None
    assert resolve_llm_provider("gemini", gemini_api_key="") is None
    assert resolve_llm_provider("unknown", gemini_api_key="x") is None
    provider = resolve_llm_provider("gemini", gemini_api_key="test-key")
    assert callable(provider)
    client = _stub_client(_gemini_payload())
    fb = provider(Q, ANSWER, evaluate(Q, ANSWER), client=client)
    assert fb == FEEDBACK
