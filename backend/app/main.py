"""VoiceHire AI — Adaptive voice technical interviewer.
FastAPI backend: session management, evaluation, adaptive routing, voice analytics.
In production the built frontend (static/) is served from the same service."""
import os
import time, uuid, secrets
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config import settings
from app.questions import QUESTIONS, ALL_TOPICS, get_questions
from app.services.evaluator import evaluate, evaluation_to_dict
from app.services.adaptive import next_question, pick_followup
from app.services.analytics import analyze_answer
from app.services import assemblyai_service

app = FastAPI(title="VoiceHire AI", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin, "http://localhost:5173"],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

STATIC_DIR = Path(__file__).resolve().parents[2] / "static"  # <root>/static in prod image
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

# In-memory store (demo). Swap for PostgreSQL via SQLAlchemy for production.
SESSIONS: dict[str, dict] = {}
TOKENS: dict[str, float] = {}

class CreateSession(BaseModel):
    role: str = "Software Developer"
    topic: str = "javascript"
    difficulty: str = "intermediate"
    candidate_name: str = "Candidate"

class SubmitAnswer(BaseModel):
    answer: str
    duration_sec: float = 30.0
    latency_sec: float = 2.0

class TranscribeReq(BaseModel):
    audio_url: str

@app.get("/api/health")
def health():
    return {"status": "ok", "assemblyai": "live" if assemblyai_service.has_key() else "demo-mode", "llm": settings.llm_provider}

@app.get("/api/topics")
def topics():
    return {"topics": ALL_TOPICS, "roles": ["Software Developer", "Frontend Developer", "Backend Developer", "Data Scientist"]}

@app.get("/api/voice-agent/config")
def voice_agent_config():
    return assemblyai_service.voice_agent_info()

@app.post("/api/token/assemblyai")
def temp_token():
    """Short-lived frontend token. The real API key stays server-side."""
    tok = secrets.token_urlsafe(24)
    TOKENS[tok] = time.time() + 300  # 5 minutes
    return {"token": tok, "expires_in": 300, "mode": "live" if assemblyai_service.has_key() else "demo"}

@app.post("/api/sessions")
def create_session(body: CreateSession):
    questions = get_questions(body.topic, body.difficulty)
    if not questions:
        raise HTTPException(400, "No questions for this topic/difficulty")
    sid = str(uuid.uuid4())
    SESSIONS[sid] = {
        "id": sid, "role": body.role, "topic": body.topic, "difficulty": body.difficulty,
        "candidate": body.candidate_name, "started_at": time.time(),
        "plan": questions, "index": 0, "answers": [], "followup_pending": None,
    }
    s = SESSIONS[sid]
    q = s["plan"][0]
    return {"session_id": sid, "total_questions": len(s["plan"]),
            "current_question": {"id": q["id"], "question": q["question"], "topic": q["topic"], "difficulty": q["difficulty"]}}

@app.post("/api/sessions/{sid}/answer")
def submit_answer(sid: str, body: SubmitAnswer):
    s = SESSIONS.get(sid)
    if not s:
        raise HTTPException(404, "Session not found")
    pending = s.get("followup_pending")
    if pending:
        # Follow-up answers are recorded on the parent question, not re-scored standalone
        s["answers"][-1]["followup_answer"] = body.answer
        s["followup_pending"] = None
        s["index"] += 1
        finished = s["index"] >= len(s["plan"])
        nq = None if finished else s["plan"][s["index"]]
        return {"kind": "followup_recorded", "finished": finished,
                "next_question": None if not nq else {"id": nq["id"], "question": nq["question"], "topic": nq["topic"], "difficulty": nq["difficulty"]}}

    q = s["plan"][s["index"]]
    ev = evaluate(q, body.answer)
    analytics = analyze_answer(body.answer, body.duration_sec, body.latency_sec)
    record = {"question_id": q["id"], "question": q["question"], "answer": body.answer,
              "evaluation": evaluation_to_dict(ev), "voice_analytics": analytics}
    s["answers"].append(record)

    # Adaptive: strong gap -> squeeze a follow-up before moving on; full score -> move on
    followup = pick_followup(q, ev.missing) if ev.overall < 7.5 and ev.missing else None
    if followup:
        s["followup_pending"] = followup
        return {"kind": "followup", "followup_question": followup, "evaluation": record["evaluation"],
                "voice_analytics": analytics, "finished": False}

    s["index"] += 1
    finished = s["index"] >= len(s["plan"])
    nq = None if finished else s["plan"][s["index"]]
    return {"kind": "scored", "evaluation": record["evaluation"], "voice_analytics": analytics,
            "finished": finished,
            "next_question": None if not nq else {"id": nq["id"], "question": nq["question"], "topic": nq["topic"], "difficulty": nq["difficulty"]}}

@app.get("/api/sessions/{sid}/report")
def report(sid: str):
    s = SESSIONS.get(sid)
    if not s:
        raise HTTPException(404, "Session not found")
    ans = s["answers"]
    if not ans:
        raise HTTPException(400, "No answers yet")
    avgs = {}
    for key in ["technical_correctness", "conceptual_understanding", "explanation_clarity", "completeness"]:
        avgs[key] = round(sum(a["evaluation"]["scores"][key] for a in ans) / len(ans), 1)
    overall = round(sum(avgs.values()) / 4, 1)
    strengths = list({x for a in ans for x in a["evaluation"]["strengths"]})
    gaps = list({x for a in ans for x in a["evaluation"]["gaps"]})
    revisit = list({t for a in ans for t in a["evaluation"]["topics_to_revisit"]})
    funnel = [{"name": f"Q{i+1}", "score": a["evaluation"]["overall"]} for i, a in enumerate(ans)]
    return {
        "session_id": sid, "candidate": s["candidate"], "role": s["role"], "topic": s["topic"],
        "overall_score": overall, "rubric_averages": avgs,
        "per_question": funnel,
        "answers": ans, "strengths": strengths, "gaps": gaps,
        "topics_to_revisit": revisit,
        "learning_plan": [f"Day 1-2: Re-read {t} and write a 5-line explanation from memory" for t in revisit[:3]] +
                         ["Day 3: Re-attempt this interview topic and compare scores", "Day 4-5: Practice one follow-up drill per weak concept out loud"],
        "voice_summary": {
            "avg_duration_sec": round(sum(a["voice_analytics"]["answer_duration_sec"] for a in ans) / len(ans), 1),
            "total_fillers": sum(a["voice_analytics"]["filler_count"] for a in ans),
            "avg_latency_sec": round(sum(a["voice_analytics"]["response_latency_sec"] for a in ans) / len(ans), 1),
        },
    }

@app.post("/api/transcribe")
async def transcribe(body: TranscribeReq):
    return await assemblyai_service.transcribe_file(body.audio_url)

@app.get("/api/transcribe/{tid}")
async def transcript_status(tid: str):
    return await assemblyai_service.get_transcript(tid)

# --- SPA serving (registered LAST so /api routes win) ---
if STATIC_DIR.exists():
    @app.get("/", include_in_schema=False)
    def serve_index():
        return FileResponse(STATIC_DIR / "index.html")

    def _spa(path: str):
        candidate = STATIC_DIR / path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(STATIC_DIR / "index.html")

    app.add_api_route("/favicon.ico", lambda: _spa("favicon.ico"), include_in_schema=False)
    app.get("/{path:path}", include_in_schema=False)(_spa)
