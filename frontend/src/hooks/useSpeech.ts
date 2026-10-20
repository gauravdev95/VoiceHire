import { useEffect, useRef, useState } from "react";

/** Voice hook.
 * Live mode: AssemblyAI Voice Agent via backend proxy (key server-side only).
 * Demo mode (no key): browser SpeechRecognition for input + SpeechSynthesis for output,
 * so the project ALWAYS demos — even offline, even without credits. */
export function useSpeech() {
  const [listening, setListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const recRef = useRef<any>(null);
  const startTimeRef = useRef(0);
  const questionShownAt = useRef(Date.now());

  useEffect(() => { questionShownAt.current = Date.now(); }, []);

  function speak(text: string) {
    if (!("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = "en-US"; u.rate = 1.0;
    window.speechSynthesis.speak(u);
  }

  function startListening() {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    setTranscript("");
    if (!SR) { setListening(true); startTimeRef.current = Date.now(); return; }
    const rec = new SR();
    rec.continuous = true; rec.interimResults = true; rec.lang = "en-US";
    rec.onresult = (e: any) => {
      let text = "";
      for (let i = 0; i < e.results.length; i++) text += e.results[i][0].transcript + " ";
      setTranscript(text);
    };
    rec.onend = () => setListening(false);
    rec.start();
    recRef.current = rec;
    startTimeRef.current = Date.now();
    setListening(true);
  }

  function stopListening(): { duration: number; latency: number } {
    try { recRef.current?.stop(); } catch { /* noop */ }
    setListening(false);
    const end = Date.now();
    return {
      duration: Math.max(1, (end - startTimeRef.current) / 1000),
      latency: Math.max(0.2, (startTimeRef.current - questionShownAt.current) / 1000),
    };
  }

  function setQuestionShown() { questionShownAt.current = Date.now(); }
  return { listening, transcript, setTranscript, speak, startListening, stopListening, setQuestionShown };
}
