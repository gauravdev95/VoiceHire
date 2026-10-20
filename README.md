# VoiceHire AI — The AI Interviewer That Understands How You Think

> Don't just read the resume. Hear the reasoning.

An adaptive voice technical-interview coach: a candidate speaks answers aloud, the AI asks
adaptive follow-ups based on concept gaps, and ends with evidence-based rubric feedback +
a personalized learning plan.

Built for **AssemblyAI Voice Hackathon Week** (deadline 24 Oct 2026).

## What makes it different
- **Adaptive interview** — follow-ups target the concepts the candidate missed, not a fixed script.
- **Evidence-based feedback** — every score quotes the candidate's own words as evidence; nothing is invented.
- **Voice performance analytics** — duration, response latency, pauses, filler words. Speech rate / accent are measured for information only and are *never* scored as technical competence.

## Technical note (verified against official docs)
AssemblyAI has **no standalone TTS API** — voice output goes through the **Voice Agent API**
(`wss://api.assemblyai.com/v2/realtime/ws`, STT + LLM + speech output in one pipeline).
This project uses:
- AssemblyAI **Speech-to-Text** (`/v2/transcript`) for transcription,
- AssemblyAI **Voice Agent API** for real-time spoken interaction (proxied through the backend so the API key never reaches the browser),
- **Browser SpeechRecognition/SpeechSynthesis demo mode** when no key is set — the demo always works, even without credits.

## Repo layout
```
voicehire-ai/
  backend/          # FastAPI: sessions, rubric evaluation, adaptive routing, AssemblyAI proxy
    app/main.py
    app/questions.py            # question bank with concepts + follow-ups
    app/services/evaluator.py   # evidence-based rubric scoring
    app/services/adaptive.py    # adaptive question/follow-up selection
    app/services/analytics.py   # voice performance metrics
    app/services/assemblyai_service.py
  frontend/         # React + Vite + TypeScript, Recharts dashboard
  docker-compose.yml
```

## Run locally (2 minutes)
```bash
# backend
cd backend && cp .env.example .env   # optional: add ASSEMBLYAI_API_KEY
pip install -r requirements.txt
uvicorn app.main:app --reload          # http://localhost:8000

# frontend
cd frontend && npm install && npm run dev   # http://localhost:5173
```
No API key? It runs in demo voice mode out of the box — interview, evaluation, dashboard, everything.

Or with Docker: `docker compose up --build`

## Demo script (judges)
1. Give a **weak** answer to the event-loop question ("it handles async stuff").
2. Watch the AI detect the missing microtask-queue concept and ask an adaptive follow-up.
3. Give a **better** answer and watch the evaluation jump.
4. Open the report: per-question scores, rubric radar, quoted evidence, learning plan.

## API (key endpoints)
- `POST /api/sessions` — start interview (role, topic, difficulty)
- `POST /api/sessions/{id}/answer` — submit answer → scored + adaptive follow-up or next question
- `GET /api/sessions/{id}/report` — full report + learning plan
- `GET /api/voice-agent/config` — live vs demo voice mode
- `POST /api/token/assemblyai` — short-lived frontend token (key stays server-side)

## Roadmap
- Phase 1 (done): core MVP — voice interview, 12+ questions, transcript, rubric evaluation
- Phase 2 (done): adaptive follow-ups, evidence-based feedback, analytics, dashboard
- Phase 3: PostgreSQL persistence, LLM-upgraded rubric text (OpenAI/Gemini), user accounts, interview history

## Tests
```bash
cd backend && pip install pytest && pytest tests -q   # 6 tests: evaluator, evidence, adaptive, analytics, API flow
```
Verified demo numbers: weak event-loop answer = **5.0/10** (adaptive follow-up on microtask queue fires) · strong answer = **8.5/10**.
