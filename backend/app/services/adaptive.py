"""Adaptive interview logic: pick the next question from the candidate's weak spots."""
from app.questions import QUESTIONS

def next_question(topic: str, history: list[dict], asked_ids: set[str]) -> dict | None:
    """history: [{question_id, missing: [...], overall: float}]"""
    pool = QUESTIONS.get(topic.lower(), QUESTIONS["javascript"])
    remaining = [q for q in pool if q["id"] not in asked_ids]
    if not remaining:
        return None
    # Prefer questions whose concepts overlap with the candidate's missed concepts
    missed = set()
    for h in history:
        missed.update(h.get("missing", []))
    if missed:
        def overlap(q):
            return len(missed.intersection(c.lower() for c in q["concepts"]))
        remaining.sort(key=overlap, reverse=True)
    return remaining[0]

def pick_followup(question: dict, missing: list[str]) -> str | None:
    missing_low = [m.lower() for m in missing]
    for f in question.get("followups", []):
        trig = [t.lower() for t in f["trigger_missing"]]
        if not trig or any(t in missing_low for t in trig):
            return f["question"]
    return None
