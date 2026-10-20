"""AssemblyAI integration.

Key facts (official docs):
- Standalone TTS API does NOT exist; voice output goes through the Voice Agent API
  (WebSocket endpoint wss://api.assemblyai.com/v2/realtime/ws) which bundles
  STT + LLM + spoken response in one real-time pipeline.
- Batch/file transcription uses the REST /v2/transcript endpoint.

This module keeps ALL credentials server-side. The frontend gets only
temporary session instructions — the API key never leaves the backend."""
import httpx
from app.config import settings

ASSEMBLY_BASE = "https://api.assemblyai.com"

def has_key() -> bool:
    return bool(settings.assemblyai_api_key)

async def transcribe_file(audio_url: str) -> dict:
    """Submit a transcription job; returns job id / status. Frontend polls."""
    if not has_key():
        return {"error": "AssemblyAI key not configured — demo mode active"}
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(
            f"{ASSEMBLY_BASE}/v2/transcript",
            headers={"authorization": settings.assemblyai_api_key},
            json={"audio_url": audio_url, "language_code": "en"},
        )
        return r.json()

async def get_transcript(transcript_id: str) -> dict:
    if not has_key():
        return {"error": "AssemblyAI key not configured — demo mode active"}
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(
            f"{ASSEMBLY_BASE}/v2/transcript/{transcript_id}",
            headers={"authorization": settings.assemblyai_api_key},
        )
        return r.json()

def voice_agent_info() -> dict:
    """What the frontend needs to open the Voice Agent WebSocket.

    The real WebSocket (wss://api.assemblyai.com/v2/realtime/ws) needs the API
    key in the Authorization header — so only the backend opens it. This
    endpoint tells the frontend which mode to use."""
    if has_key():
        return {
            "mode": "live",
            "ws_url": "wss://api.assemblyai.com/v2/realtime/ws",
            "note": "Backend proxies the Voice Agent stream; key stays server-side.",
        }
    return {"mode": "demo", "note": "No AssemblyAI key — browser SpeechRecognition/Synthesis demo mode."}
