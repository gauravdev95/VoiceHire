export interface EvalScores {
  technical_correctness: number; conceptual_understanding: number;
  explanation_clarity: number; completeness: number;
}
export interface Evaluation {
  scores: EvalScores; overall: number; covered: string[]; missing: string[];
  evidence: Record<string, string | null>; strengths: string[]; gaps: string[];
  better_answer: string; topics_to_revisit: string[];
}
export interface Question { id: string; question: string; topic: string; difficulty: string; }
export interface Report {
  session_id: string; candidate: string; role: string; topic: string;
  overall_score: number; rubric_averages: EvalScores;
  per_question: { name: string; score: number }[];
  strengths: string[]; gaps: string[]; topics_to_revisit: string[];
  learning_plan: string[];
  voice_summary: { avg_duration_sec: number; total_fillers: number; avg_latency_sec: number };
  answers: { question: string; answer: string; evaluation: Evaluation }[];
}
const BASE = import.meta.env.VITE_API_URL || "";
async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { headers: { "Content-Type": "application/json" }, ...options });
  if (!r.ok) throw new Error(await r.text());
  return r.json() as Promise<T>;
}
export const createSession = (body: { role: string; topic: string; difficulty: string; candidate_name: string }) =>
  api<{ session_id: string; total_questions: number; current_question: Question }>("/api/sessions", { method: "POST", body: JSON.stringify(body) });
export const submitAnswer = (sid: string, body: { answer: string; duration_sec: number; latency_sec: number }) =>
  api<{ kind: string; finished: boolean; followup_question?: string; next_question?: Question | null; evaluation?: Evaluation }>(`/api/sessions/${sid}/answer`, { method: "POST", body: JSON.stringify(body) });
export const fetchReport = (sid: string) => api<Report>(`/api/sessions/${sid}/report`);
export const voiceAgentConfig = () => api<{ mode: string; note: string }>("/api/voice-agent/config");
