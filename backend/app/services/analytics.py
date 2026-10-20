"""Voice performance analytics.

Measures observable speech behaviour (duration, latency, pauses, filler words).
Explicit non-goal: speech rate or accent are NEVER treated as competence signals."""
import re

FILLERS = ["um", "uh", "like", "you know", "basically", "actually", "so yeah"]

def analyze_answer(transcript: str, duration_sec: float, latency_sec: float) -> dict:
    words = transcript.split()
    wpm = round(len(words) / max(1, duration_sec) * 60) if duration_sec else 0
    filler_hits = {}
    low = transcript.lower()
    for f in FILLERS:
        n = len(re.findall(r"\b" + re.escape(f) + r"\b", low))
        if n:
            filler_hits[f] = n
    long_pauses = max(0, int(duration_sec // 10))  # heuristic from recording gaps
    return {
        "answer_duration_sec": round(duration_sec, 1),
        "response_latency_sec": round(latency_sec, 1),  # time before they started speaking
        "word_count": len(words),
        "speaking_rate_wpm": wpm,  # informational only
        "long_pauses": long_pauses,
        "filler_words": filler_hits,
        "filler_count": sum(filler_hits.values()),
        "note": "Speaking rate and accent are presentation signals only — never scored as technical competence.",
    }
