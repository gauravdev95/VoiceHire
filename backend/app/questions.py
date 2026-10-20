"""Question bank — each question carries the concepts a complete answer must cover.
This is what makes evaluation evidence-based and follow-ups adaptive."""
QUESTIONS = {
    "javascript": [
        {
            "id": "js-event-loop",
            "topic": "JavaScript", "difficulty": "intermediate",
            "question": "Can you explain how the JavaScript event loop works?",
            "concepts": ["call stack", "event loop", "callback queue", "task queue", "microtask queue", "asynchronous", "non-blocking"],
            "followups": [
                {"trigger_missing": ["microtask queue"], "question": "Good start. Can you explain the difference between the microtask queue and the task queue?"},
                {"trigger_missing": ["call stack"], "question": "You mentioned async operations — what role does the call stack play in all of this?"},
                {"trigger_missing": [], "question": "Can you walk me through what happens when a setTimeout of 0ms and a resolved Promise are both scheduled?"},
            ],
            "model_points": ["Single-threaded runtime; call stack executes sync code first", "Async callbacks wait in queues", "Microtasks (Promises) run before macrotasks (setTimeout)", "Event loop moves callbacks to the stack only when it is empty"],
        },
        {
            "id": "js-closures",
            "topic": "JavaScript", "difficulty": "intermediate",
            "question": "What is a closure in JavaScript, and where have you used one?",
            "concepts": ["inner function", "outer scope", "lexical scope", "variables", "remember", "data privacy", "encapsulation"],
            "followups": [
                {"trigger_missing": ["lexical scope"], "question": "How does lexical scoping make closures possible?"},
                {"trigger_missing": [], "question": "Can a closure cause a memory leak? When?"},
            ],
            "model_points": ["Function bundled with its lexical environment", "Inner function retains access to outer variables after outer returns", "Used for data privacy, currying, memoization"],
        },
        {
            "id": "js-promises",
            "topic": "JavaScript", "difficulty": "intermediate",
            "question": "How do Promises work, and how is async/await different?",
            "concepts": ["pending", "fulfilled", "rejected", "then", "catch", "async", "await", "error handling"],
            "followups": [
                {"trigger_missing": ["rejected", "catch"], "question": "How do you handle errors in a Promise chain vs in async/await?"},
                {"trigger_missing": [], "question": "What is the difference between Promise.all and Promise.allSettled?"},
            ],
            "model_points": ["Three states: pending, fulfilled, rejected", "async/await is syntax over Promises", "try/catch for await; .catch for chains"],
        },
        {
            "id": "js-hoisting",
            "topic": "JavaScript", "difficulty": "beginner",
            "question": "What is hoisting in JavaScript?",
            "concepts": ["declaration", "moved", "top", "var", "let", "const", "temporal dead zone", "function"],
            "followups": [{"trigger_missing": ["temporal dead zone"], "question": "What is the temporal dead zone, and which declarations does it affect?"}],
            "model_points": ["Declarations are processed before execution", "var is initialized to undefined; let/const stay in TDZ", "Function declarations are fully hoisted"],
        },
        {
            "id": "js-this",
            "topic": "JavaScript", "difficulty": "advanced",
            "question": "How does `this` work in JavaScript?",
            "concepts": ["context", "call site", "bind", "call", "apply", "arrow function", "lexical"],
            "followups": [{"trigger_missing": ["arrow function"], "question": "Why do arrow functions behave differently with `this`?"}],
            "model_points": ["Determined by call site, not definition", "bind/call/apply set it explicitly", "Arrow functions inherit lexical this"],
        },
    ],
    "python": [
        {
            "id": "py-decorators",
            "topic": "Python", "difficulty": "intermediate",
            "question": "What is a decorator in Python and how would you write one?",
            "concepts": ["function", "wrapper", "higher-order", "takes a function", "returns", "functools", "wraps", "@"],
            "followups": [{"trigger_missing": ["wrapper"], "question": "What does the inner wrapper function actually do inside a decorator?"}],
            "model_points": ["Higher-order function taking and returning a function", "Wrapper adds behaviour before/after the original call", "functools.wraps preserves metadata"],
        },
        {
            "id": "py-gil",
            "topic": "Python", "difficulty": "advanced",
            "question": "What is the GIL in Python and how does it affect multithreading?",
            "concepts": ["global interpreter lock", "one thread", "bytecode", "cpu-bound", "io-bound", "multiprocessing"],
            "followups": [{"trigger_missing": ["multiprocessing"], "question": "If the GIL blocks CPU threads, what do you use for CPU-bound work instead?"}],
            "model_points": ["Only one thread executes bytecode at a time", "Fine for I/O-bound work", "Use multiprocessing for CPU-bound work"],
        },
        {
            "id": "py-list-vs-tuple",
            "topic": "Python", "difficulty": "beginner",
            "question": "What is the difference between a list and a tuple in Python?",
            "concepts": ["mutable", "immutable", "hashable", "performance", "use case"],
            "followups": [{"trigger_missing": ["hashable"], "question": "Why does immutability make tuples usable as dictionary keys?"}],
            "model_points": ["Lists are mutable, tuples immutable", "Tuples are hashable, can be dict keys", "Tuples are slightly more memory-efficient"],
        },
    ],
    "react": [
        {
            "id": "react-hooks",
            "topic": "React", "difficulty": "intermediate",
            "question": "How does useEffect work, and what does its dependency array control?",
            "concepts": ["side effect", "render", "dependency", "cleanup", "mount", "re-run"],
            "followups": [{"trigger_missing": ["cleanup"], "question": "When would you return a cleanup function from useEffect?"}],
            "model_points": ["Runs after render for side effects", "Deps array controls re-runs", "Cleanup runs before re-run and on unmount"],
        },
        {
            "id": "react-vdom",
            "topic": "React", "difficulty": "intermediate",
            "question": "What is the Virtual DOM and how does reconciliation work?",
            "concepts": ["virtual dom", "diffing", "reconciliation", "real dom", "keys", "re-render"],
            "followups": [{"trigger_missing": ["keys"], "question": "Why do lists need stable keys during reconciliation?"}],
            "model_points": ["In-memory representation of the UI", "Diffing computes minimal real-DOM updates", "Keys help identify elements across renders"],
        },
    ],
    "system-design": [
        {
            "id": "sd-url-shortener",
            "topic": "System Design", "difficulty": "advanced",
            "question": "How would you design a URL shortener like bit.ly?",
            "concepts": ["hashing", "base62", "database", "cache", "redirect", "301", "scale", "collision"],
            "followups": [{"trigger_missing": ["cache"], "question": "Where would you add caching, and what would you cache?"},
                         {"trigger_missing": ["collision"], "question": "How do you handle collisions in your short-code generation?"}],
            "model_points": ["Base62 encoding of an ID or hash", "Cache hot URLs (Redis)", "301 vs 302 redirect trade-off", "Collision handling strategy"],
        },
    ],
}
ALL_TOPICS = list(QUESTIONS.keys())
def get_questions(topic: str, difficulty: str | None = None, limit: int = 5):
    pool = QUESTIONS.get(topic.lower(), QUESTIONS["javascript"])
    if difficulty:
        filtered = [q for q in pool if q["difficulty"] == difficulty.lower()] or pool
    else:
        filtered = pool
    return filtered[:limit]
