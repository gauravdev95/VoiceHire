import type { Report } from "../lib/api";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from "recharts";

export function ReportView({ report, onRestart }: { report: Report; onRestart: () => void }) {
  const radar = Object.entries(report.rubric_averages).map(([k, v]) => ({ metric: k.replace(/_/g, " "), score: v }));
  return (
    <div className="card">
      <h2>Interview report — {report.candidate}</h2>
      <p className="tag">{report.role} · {report.topic} · Overall <b>{report.overall_score}/10</b></p>
      <div className="charts">
        <div>
          <h3>Score per question</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={report.per_question}><XAxis dataKey="name" /><YAxis domain={[0, 10]} /><Tooltip /><Bar dataKey="score" fill="#7c6cf0" /></BarChart>
          </ResponsiveContainer>
        </div>
        <div>
          <h3>Rubric averages</h3>
          <ResponsiveContainer width="100%" height={220}>
            <RadarChart data={radar}><PolarGrid /><PolarAngleAxis dataKey="metric" tick={{ fontSize: 11 }} /><PolarRadiusAxis domain={[0, 10]} /><Radar dataKey="score" stroke="#7c6cf0" fill="#7c6cf0" fillOpacity={0.5} /></RadarChart>
          </ResponsiveContainer>
        </div>
      </div>
      <h3>Strengths</h3><ul>{report.strengths.map((s, i) => <li key={i}>{s}</li>)}</ul>
      <h3>Gaps</h3><ul>{report.gaps.map((s, i) => <li key={i}>{s}</li>)}</ul>
      <h3>Voice analytics</h3>
      <p>Avg answer duration: {report.voice_summary.avg_duration_sec}s · Filler words: {report.voice_summary.total_fillers} · Avg thinking time: {report.voice_summary.avg_latency_sec}s
        <br /><i>Speaking rate and accent are presentation signals only — never scored as technical competence.</i></p>
      <h3>Your learning plan</h3><ol>{report.learning_plan.map((s, i) => <li key={i}>{s}</li>)}</ol>
      <h3>Evidence — what you said vs the rubric</h3>
      {report.answers.map((a, i) => (
        <details key={i}><summary>Q{i + 1}: {a.question}</summary>
          <p><b>You said:</b> {a.answer}</p>
          <p><b>Covered:</b> {a.evaluation.covered.join(", ") || "—"} · <b>Missed:</b> {a.evaluation.missing.join(", ") || "—"}</p>
          <p><b>Better answer:</b> {a.evaluation.better_answer}</p>
        </details>
      ))}
      <button className="primary" onClick={onRestart}>Start new interview</button>
    </div>
  );
}
