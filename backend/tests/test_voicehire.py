"""VoiceHire AI tests. Run: pytest backend/tests -q"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.services.evaluator import evaluate
from app.services.analytics import analyze_answer
from app.services.adaptive import pick_followup
from app.questions import QUESTIONS, get_questions
from fastapi.testclient import TestClient

def test_weak_answer_scores_lower_than_strong():
    q = QUESTIONS["javascript"][0]
    weak = evaluate(q, "The event loop handles asynchronous operations and executes callbacks when the call stack is empty.")
    strong = evaluate(q, "JavaScript is single-threaded. The call stack runs synchronous code first while async callbacks wait in the callback queue and task queue. Promises go to the higher-priority microtask queue. The event loop moves the next callback in only when the stack is empty, making execution non-blocking and asynchronous.")
    assert strong.overall > weak.overall
    assert "microtask queue" in weak.missing
    assert strong.scores["completeness"] >= 9

def test_evidence_quotes_real_words():
    q = QUESTIONS["javascript"][0]
    ev = evaluate(q, "The microtask queue runs before the task queue for promises.")
    assert ev.evidence["microtask queue"] is not None
    assert "microtask" in ev.evidence["microtask queue"].lower()

def test_followup_targets_missing_concept():
    q = QUESTIONS["javascript"][0]
    assert "microtask" in pick_followup(q, ["microtask queue"]).lower()

def test_analytics_counts_fillers():
    a = analyze_answer("um the event loop is basically like a loop um", 12.0, 1.5)
    assert a["filler_count"] >= 3

def test_api_flow():
    from app.main import app
    c = TestClient(app)
    assert c.get("/api/health").json()["status"] == "ok"
    r = c.post("/api/sessions", json={"role": "Software Developer", "topic": "javascript", "difficulty": "intermediate", "candidate_name": "Test"})
    sid = r.json()["session_id"]
    r2 = c.post(f"/api/sessions/{sid}/answer", json={"answer": "The event loop handles asynchronous operations and executes callbacks when the call stack is empty.", "duration_sec": 15, "latency_sec": 2})
    assert r2.json()["kind"] == "followup"  # adaptive behavior on a weak answer
    c.post(f"/api/sessions/{sid}/answer", json={"answer": "Microtasks are promises, tasks are timers, microtasks run first.", "duration_sec": 10, "latency_sec": 1})
    rep = c.get(f"/api/sessions/{sid}/report")
    assert rep.status_code == 200
    assert "learning_plan" in rep.json()

def test_questions_pool():
    assert get_questions("python")
    assert len(get_questions("javascript", "intermediate")) >= 3
