# VoiceHire AI — Demo Script (2–3 minutes)

Goal: in one demonstration, show judges (1) real-time voice interaction,
(2) adaptive AI reasoning, (3) measurable user value.

## Setup (before the judges arrive)
- Open the app, select: Role = Software Developer, Topic = JavaScript, Difficulty = Intermediate.
- Confirm the header pill reads "Live voice (AssemblyAI)" or "Demo voice (browser)".
- Have these two answers ready — one weak, one strong:

**Weak answer** (event loop): *"The event loop handles asynchronous operations and executes callbacks when the call stack is empty."*

**Strong answer** (event loop): *"JavaScript runs on a single thread with a call stack. Synchronous code runs first; async callbacks wait in the task queue, while promise callbacks go to the microtask queue, which always drains before the next macrotask. So a resolved promise runs before a setTimeout of 0ms — that's what makes it non-blocking."*

## Act 1 — The weak answer (0:00–1:00)
1. Click **Start Interview**, let the AI speak the first question.
2. Read the weak answer aloud (or type it).
3. Point at the scorecard: **5.0/10**, and the *missing concepts* list — call out that the AI
   quoted the candidate's own sentence as evidence.
4. The AI now asks the adaptive follow-up: *"Good start. Can you explain the difference between the microtask queue and the task queue?"*
   — **this is the money shot**: it detected the exact gap and drilled into it.

## Act 2 — The strong answer (1:00–1:45)
1. Read the strong answer aloud.
2. Watch the score jump to **~8.5/10** — same rubric, same interviewer, measurable improvement.

## Act 3 — The report (1:45–2:45)
1. Finish the interview, open the **report dashboard**.
2. Show: per-question bar chart, rubric radar (4 dimensions), strengths vs gaps,
   voice analytics (duration, thinking time, filler words), and the **personalized learning plan**.
3. Closing line: *"VoiceHire doesn't grade accent or speed — only reasoning. It hears how you think, finds the gaps, and tells you exactly what to study next."*

## If something breaks
- No mic permission → answers can be typed; every feature still works.
- No network / no API key → demo voice mode runs 100% locally; say so out loud — judges respect graceful degradation.
