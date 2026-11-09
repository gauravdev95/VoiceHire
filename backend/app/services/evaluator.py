"""Evidence-based rubric evaluator.

Scores each answer on 4 rubric dimensions and QUOTES the candidate's own
words as evidence — never invents what wasn't said.
Runs fully offline (demo-safe). When an LLM provider is configured (see
``resolve_llm_provider``), the rubric *prose* — strengths, gaps and the
better-answer text — is upgraded by the model; scores, coverage and quoted
evidence always stay deterministic, and any provider failure falls back to
the built-in text silently (the interview never breaks for an LLM outage).
"""
import json
import re
from collections.abc import Callable
from dataclasses import dataclass, asdict, replace

import httpx

RUBRICS = [
    ("technical_correctness", "Technical correctness", "Are the stated facts right?"),
    ("conceptual_understanding", "Conceptual understanding", "Does the answer show the 'why', not just the words?"),
    ("explanation_clarity", "Explanation clarity", "Is it structured and understandable?"),
    ("completeness", "Completeness", "Are the key concepts covered?"),
]

def _normalize(t: str) -> str:
    return re.sub(r"\s+", " ", t.strip().lower())

def _find_evidence(answer: str, concepts: list[str]) -> dict[str, str | None]:
    """For each concept, quote the sentence that mentions it (evidence), else None."""
    sentences = re.split(r"(?<=[.!?])\s+", answer.strip())
    found = {}
    low = answer.lower()
    for c in concepts:
        if c.lower() in low:
            for s in sentences:
                if c.lower() in s.lower():
                    found[c] = s.strip()[:220]
                    break
            else:
                found[c] = "(mentioned)"
        else:
            found[c] = None
    return found

def _quote(answer: str, n: int = 110) -> str:
    s = answer.strip()
    return s[:n] + ("…" if len(s) > n else "")

@dataclass
class EvalResult:
    scores: dict[str, int]
    overall: float
    covered: list[str]
    missing: list[str]
    evidence: dict[str, str | None]
    strengths: list[str]
    gaps: list[str]
    better_answer: str
    topics_to_revisit: list[str]

def evaluate(question: dict, answer: str, *, llm: Callable | None = None) -> EvalResult:
    concepts = question["concepts"]
    evidence = _find_evidence(answer, concepts)
    covered = [c for c, e in evidence.items() if e]
    missing = [c for c, e in evidence.items() if not e]
    words = len(answer.split())
    coverage = len(covered) / max(1, len(concepts))

    # Completeness is directly coverage-driven
    completeness = round(min(10, 2 + coverage * 8))
    # Technical correctness: penalize very short answers, reward concept density
    correctness = round(min(10, 2 + coverage * 7 + min(1.5, words / 120)))
    # Conceptual understanding: needs >half coverage + some length
    understanding = round(min(10, 2 + coverage * 6 + min(2, words / 150)))
    # Clarity: structure signals — sentences, no huge filler ratio
    filler_ratio = len(re.findall(r"\b(um+|uh+|like|you know|basically)\b", answer.lower())) / max(1, words)
    # Clarity: base 5; rewards length, multi-sentence structure; penalizes filler-word density
    num_sentences = max(1, len([s for s in re.split(r"(?<=[.!?])\s+", answer.strip()) if s.strip()]))
    clarity = round(min(10, 5 + min(3, words / 40) + (1 if num_sentences >= 2 else 0) - filler_ratio * 20))
    clarity = max(2, clarity)

    scores = {
        "technical_correctness": correctness,
        "conceptual_understanding": understanding,
        "explanation_clarity": clarity,
        "completeness": completeness,
    }
    overall = round(sum(scores.values()) / 4, 1)

    strengths, gaps = [], []
    if covered:
        top = covered[0]
        strengths.append(f"Correctly covered '{top}' — {_quote(evidence[top] or '', 90)}")
    if coverage >= 0.6:
        strengths.append(f"Strong coverage: {len(covered)}/{len(concepts)} key concepts mentioned")
    if missing:
        gaps.append(f"Missed: {', '.join(missing[:3])} — these are core to a complete answer")
    if words < 25:
        gaps.append("Answer was quite short — interviewers expect the reasoning, not just one line")

    better = ("A stronger answer would say: " + " ".join(question["model_points"]) +
              " — tied together in your own words, e.g. " + _quote(question["model_points"][0], 120))

    result = EvalResult(
        scores=scores, overall=overall, covered=covered, missing=missing,
        evidence=evidence, strengths=strengths, gaps=gaps,
        better_answer=better, topics_to_revisit=missing[:3] or [question["topic"]],
    )
    # LLM (if configured) upgrades only the prose; scores/evidence stay put.
    return _upgrade_with_llm(question, answer, result, llm)


# --- Optional LLM rubric upgrade -------------------------------------------
# The LLM only rewrites the *prose* (strengths / gaps / better_answer).
# Scores, coverage and quoted evidence are computed above and never handed
# to the model to invent. Provider config comes from app.config.settings:
# LLM_PROVIDER=mock (default, deterministic) | gemini | openai, with the
# matching API key in the backend .env. Any failure returns None and the
# caller keeps the deterministic text.

LLM_TIMEOUT_S = 20.0
_LLM_MAX_ITEMS = 5
_LLM_MAX_CHARS = 500

_LLM_SYSTEM = (
    "You are a technical interview coach. Given a question, its key concepts, "
    "the candidate's answer, and the deterministic rubric scores, write concise "
    "feedback. Reply with JSON ONLY, no markdown, no extra text, with keys: "
    '"strengths" (list of short strings), "gaps" (list of short strings), '
    '"better_answer" (one short paragraph). Ground every claim in the answer; '
    "never invent concepts the candidate did not mention. Do not restate scores."
)


def _llm_prompt(question: dict, answer: str, result: EvalResult) -> str:
    return (
        f"Question: {question['question']}\n"
        f"Key concepts: {', '.join(question['concepts'])}\n"
        f"Candidate answer: {answer}\n"
        f"Deterministic scores (0-10): {result.scores}, overall {result.overall}\n"
        f"Concepts covered: {result.covered or 'none'}; missing: {result.missing or 'none'}"
    )


def _parse_llm_feedback(text: str) -> dict | None:
    """Validate LLM JSON into {strengths, gaps, better_answer} or None."""
    if not text or not text.strip():
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    strengths = data.get("strengths")
    gaps = data.get("gaps")
    better = data.get("better_answer")
    if (not isinstance(strengths, list) or not strengths
            or not all(isinstance(s, str) and s.strip() for s in strengths)):
        return None
    if (not isinstance(gaps, list)
            or not all(isinstance(s, str) for s in gaps)):
        return None
    if not isinstance(better, str) or not better.strip():
        return None
    return {
        "strengths": [s.strip()[:_LLM_MAX_CHARS] for s in strengths[:_LLM_MAX_ITEMS]],
        "gaps": [s.strip()[:_LLM_MAX_CHARS] for s in gaps[:_LLM_MAX_ITEMS]],
        "better_answer": better.strip()[:1000],
    }


def llm_feedback(question: dict, answer: str, result: EvalResult, *,
                 provider: str, api_key: str,
                 client: httpx.Client | None = None) -> dict | None:
    """Ask the configured LLM for rubric prose. None on any failure.

    ``client`` is injectable for tests (pass an httpx.Client with a
    MockTransport); otherwise a short-lived client is created here.
    """
    if provider not in ("gemini", "openai") or not api_key:
        return None
    prompt = _llm_prompt(question, answer, result)
    own_client = client is None
    if own_client:
        client = httpx.Client(timeout=LLM_TIMEOUT_S)
    try:
        if provider == "gemini":
            resp = client.post(
                "https://generativelanguage.googleapis.com/v1beta/models/"
                "gemini-2.0-flash:generateContent",
                headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
                json={"contents": [{"parts": [{"text": _LLM_SYSTEM + "\n\n" + prompt}]}],
                      "generationConfig": {"responseMimeType": "application/json",
                                           "temperature": 0.3}},
            )
            resp.raise_for_status()
            text = (resp.json().get("candidates", [{}])[0]
                    .get("content", {}).get("parts", [{}])[0].get("text", ""))
        else:  # openai
            resp = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}",
                         "Content-Type": "application/json"},
                json={"model": "gpt-4o-mini",
                      "messages": [{"role": "system", "content": _LLM_SYSTEM},
                                   {"role": "user", "content": prompt}],
                      "response_format": {"type": "json_object"},
                      "temperature": 0.3},
            )
            resp.raise_for_status()
            text = (resp.json().get("choices", [{}])[0]
                    .get("message", {}).get("content", ""))
        return _parse_llm_feedback(text)
    except Exception:
        return None
    finally:
        if own_client:
            client.close()


def resolve_llm_provider(provider: str, *, gemini_api_key: str = "",
                         openai_api_key: str = "") -> Callable | None:
    """Build the ``llm`` callable for ``evaluate()`` from settings, or None.

    None means deterministic-only: unknown provider, "mock", or a provider
    selected without its API key configured. Never raises.
    """
    p = (provider or "mock").strip().lower()
    key = ""
    if p == "gemini":
        key = gemini_api_key
    elif p == "openai":
        key = openai_api_key
    if not key:
        return None

    def _call(question: dict, answer: str, result: EvalResult, *,
              client: httpx.Client | None = None) -> dict | None:
        return llm_feedback(question, answer, result,
                            provider=p, api_key=key, client=client)

    return _call


def evaluation_to_dict(e: EvalResult) -> dict:
    return asdict(e)


def _upgrade_with_llm(question: dict, answer: str, result: EvalResult,
                      llm: Callable | None) -> EvalResult:
    """Replace only the prose fields with LLM feedback when available."""
    if llm is None:
        return result
    try:
        fb = llm(question, answer, result)
    except Exception:
        return result
    if not fb:
        return result
    return replace(result, strengths=fb["strengths"], gaps=fb["gaps"],
                   better_answer=fb["better_answer"])
