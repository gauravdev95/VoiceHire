import { useEffect, useState } from "react";
import { useSpeech } from "./hooks/useSpeech";
import { createSession, submitAnswer, fetchReport, voiceAgentConfig } from "./lib/api";
import type { Question, Evaluation, Report } from "./lib/api";
import { ReportView } from "./pages/ReportView";

type Screen = "setup" | "interview" | "report";

export default function App() {
  const [screen, setScreen] = useState<Screen>("setup");
  const [name, setName] = useState("Gaurav Yadav");
  const [role, setRole] = useState("Software Developer");
  const [topic, setTopic] = useState("javascript");
  const [difficulty, setDifficulty] = useState("intermediate");
  const [sessionId, setSessionId] = useState("");
  const [question, setQuestion] = useState<Question | null>(null);
  const [followup, setFollowup] = useState<string | null>(null);
  const [answer, setAnswer] = useState("");
  const [lastEval, setLastEval] = useState<Evaluation | null>(null);
  const [qNum, setQNum] = useState(1);
  const [qTotal, setQTotal] = useState(5);
  const [busy, setBusy] = useState(false);
  const [report, setReport] = useState<Report | null>(null);
  const [voiceMode, setVoiceMode] = useState("...");
  const speech = useSpeech();

  useEffect(() => { voiceAgentConfig().then(c => setVoiceMode(c.mode === "live" ? "Live voice (AssemblyAI)" : "Demo voice (browser)")).catch(() => setVoiceMode("Demo voice (browser)")); }, []);

  async function start() {
    setBusy(true);
    try {
      const s = await createSession({ role, topic, difficulty, candidate_name: name });
      setSessionId(s.session_id); setQuestion(s.current_question);
      setQTotal(s.total_questions); setQNum(1);
      speech.setQuestionShown(); speech.speak(`Welcome! Let's begin with a ${topic} question. ${s.current_question.question}`);
      setScreen("interview");
    } finally { setBusy(false); }
  }

  function beginRecording() { setAnswer(""); speech.startListening(); }
  function endRecording() { const { duration, latency } = speech.stopListening(); submit(answer || speech.transcript, duration, latency); }

  async function submit(text: string, duration: number, latency: number) {
    if (!text.trim()) return;
    setBusy(true);
    try {
      const r = await submitAnswer(sessionId, { answer: text, duration_sec: duration, latency_sec: latency });
      if (r.kind === "followup" && r.followup_question) {
        setFollowup(r.followup_question); setLastEval(r.evaluation ?? null);
        speech.speak(r.followup_question);
      } else if (r.kind === "followup_recorded") {
        setFollowup(null); setLastEval(null);
        if (r.finished) { await finish(); return; }
        if (r.next_question) { setQuestion(r.next_question); setQNum(q => q + 1); speech.setQuestionShown(); speech.speak(r.next_question.question); }
      } else {
        setLastEval(r.evaluation ?? null); setFollowup(null);
        if (r.finished) { await finish(); return; }
        if (r.next_question) { setQuestion(r.next_question); setQNum(q => q + 1); speech.setQuestionShown(); speech.speak(r.next_question.question); }
      }
      setAnswer("");
    } finally { setBusy(false); }
  }

  async function finish() {
    const rep = await fetchReport(sessionId);
    setReport(rep); setScreen("report");
    speech.speak(`Interview complete. Your overall score is ${rep.overall_score} out of 10.`);
  }

  return (
    <div className="vh">
      <header className="vh-header">
        <div><h1>VoiceHire AI</h1><p className="tag">The AI Interviewer That Understands How You Think</p></div>
        <span className="pill">{voiceMode}</span>
      </header>

      {screen === "setup" && (
        <div className="card">
          <h2>Start an interview</h2>
          <label>Name <input value={name} onChange={e => setName(e.target.value)} /></label>
          <div className="row">
            <label>Role
              <select value={role} onChange={e => setRole(e.target.value)}>
                <option>Software Developer</option><option>Frontend Developer</option>
                <option>Backend Developer</option><option>Data Scientist</option>
              </select></label>
            <label>Topic
              <select value={topic} onChange={e => setTopic(e.target.value)}>
                <option value="javascript">JavaScript</option><option value="python">Python</option>
                <option value="react">React</option><option value="system-design">System Design</option>
              </select></label>
            <label>Difficulty
              <select value={difficulty} onChange={e => setDifficulty(e.target.value)}>
                <option>beginner</option><option>intermediate</option><option>advanced</option>
              </select></label>
          </div>
          <button className="primary" disabled={busy} onClick={start}>{busy ? "Starting…" : "Start Interview"}</button>
        </div>
      )}

      {screen === "interview" && question && (
        <div className="card">
          <div className="qmeta">Question {qNum} of {qTotal} · {question.difficulty}</div>
          <h2 className="qq">{question.question}</h2>
          {followup && <div className="followup"><b>Adaptive follow-up:</b> {followup}</div>}
          <div className="controls">
            {!speech.listening
              ? <button className="primary" onClick={beginRecording}>Start speaking</button>
              : <button className="danger" onClick={endRecording}>Stop &amp; submit</button>}
            <button className="ghost" onClick={() => speech.speak(followup ?? question.question)}>Replay question</button>
          </div>
          <textarea rows={6} placeholder="Your transcript appears here — you can also type your answer."
            value={speech.listening ? speech.transcript : answer}
            onChange={e => { setAnswer(e.target.value); speech.setTranscript(e.target.value); }} />
          {!speech.listening && (
            <button className="primary" disabled={busy || !(answer || speech.transcript).trim()}
              onClick={() => submit(answer || speech.transcript, 30, 2)}>
              {busy ? "Evaluating…" : "Submit answer (typed)"}
            </button>
          )}
          {lastEval && <ScoreCard ev={lastEval} />}
        </div>
      )}

      {screen === "report" && report && <ReportView report={report} onRestart={() => { setScreen("setup"); setReport(null); setLastEval(null); setFollowup(null); setAnswer(""); }} />}
    </div>
  );
}

function ScoreCard({ ev }: { ev: Evaluation }) {
  return (
    <div className="scorecard">
      <h3>Evaluation · {ev.overall}/10</h3>
      <div className="bars">
        {Object.entries(ev.scores).map(([k, v]) => (
          <div key={k} className="bar"><span>{k.replace(/_/g, " ")}</span>
            <div className="track"><div className="fill" style={{ width: `${v * 10}%` }} /></div><b>{v}</b></div>
        ))}
      </div>
      {ev.strengths.length > 0 && <p><b>Strengths:</b> {ev.strengths.join(" ")}</p>}
      {ev.gaps.length > 0 && <p><b>Gaps:</b> {ev.gaps.join(" ")}</p>}
    </div>
  );
}
