"""Evidence-based rubric evaluator.

Scores each answer on 4 rubric dimensions and QUOTES the candidate's own
words as evidence — never invents what wasn't said.
Runs fully offline (demo-safe); an LLM provider can upgrade the rubric text."""
import re
from dataclasses import dataclass, asdict

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

def evaluate(question: dict, answer: str) -> EvalResult:
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

    return EvalResult(
        scores=scores, overall=overall, covered=covered, missing=missing,
        evidence=evidence, strengths=strengths, gaps=gaps,
        better_answer=better, topics_to_revisit=missing[:3] or [question["topic"]],
    )

def evaluation_to_dict(e: EvalResult) -> dict:
    return asdict(e)
