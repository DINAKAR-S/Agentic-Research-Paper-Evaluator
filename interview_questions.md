Here are all interview Q&As in short, based on our full conversation:

Project Basics
Q: What does this project do?

AI-powered automated peer review of arXiv papers using 5 specialized agents. Outputs ACCEPT / NEEDS REVISION / REJECT with a score.

Q: What tech stack did you use?

CrewAI (agents), GPT-4o-mini (LLM), PyMuPDF (PDF parsing), arxiv library (download), Streamlit (UI), tiktoken (token counting), Python dotenv.

Agents
Q: Why 5 agents instead of 1 prompt?

Each agent has a focused role and persona. One prompt mixing 5 tasks gives diluted output. Separate agents give specialized, higher quality results.

Q: Name the 5 agents and what they do.

Consistency — methodology vs results alignment (0–100 score)
Grammar — writing quality (HIGH/MEDIUM/LOW)
Novelty — originality vs existing literature (Novel/Incremental/Derivative)
Fact-check — verifies formulas, constants, data (✓/⚠/✗)
Authenticity — fabrication risk percentage (0–100%)
Q: Why sequential not parallel?

Avoids API rate limits. Later agents can benefit from earlier context. Process.sequential in CrewAI handles this cleanly.

Code Flow
Q: What happens when you run evaluate_paper("2303.08774")?

arxiv library fetches metadata + downloads PDF
PyMuPDF extracts text + detects sections
_create_tasks() builds 5 tasks with sliced text
crew.kickoff() runs 5 agents sequentially
_compile_report() parses scores → final JSON report
Q: How does PDF upload work?

Streamlit reads raw bytes → tempfile.mkstemp() writes to disk → PyMuPDF parses it → temp file deleted in finally block.

Q: How are sections detected from PDF?

PyMuPDF extracts text page by page. Regex patterns match headers like Introduction, Methodology, Results. Each section's text is stored in a dict.

Token Management
Q: How is the 16k token limit enforced?

Character slicing in _create_tasks() — [:8000] chars ≈ 2,000 tokens per task. This cuts text before it ever reaches the LLM.

Q: Is token counting the same across OpenAI and Anthropic?

No. Each model has its own tokenizer. Same text can be 10k tokens in OpenAI and 9,200 or 10,800 in Anthropic. Your project uses cl100k_base (OpenAI tokenizer) which matches GPT-4o-mini exactly.

Q: What is tiktoken used for here?

It's OpenAI's tokenizer used in LLMManager to count tokens. But in practice the agents never call LLMManager — so tiktoken is unused in the live pipeline.

LLMManager
Q: What is LLMManager and is it used?

It's a utility class for direct LLM calls with token counting, chunking, and multi-provider fallback (OpenAI → OpenRouter → Gemini). But CrewAI handles its own LLM calls internally, so LLMManager is never called in the actual pipeline.

Q: How does chunking work in LLMManager?

tiktoken encodes text to tokens → splits at 15,000 tokens (16k minus 1k buffer) → 200-token overlap between chunks → each chunk sent as a separate API call → results concatenated or summarized.

Q: If you called LLMManager with an 18k token text, what happens?

It splits into 2 chunks: tokens[0:15000] and tokens[14800:18000] (200 overlap). Two separate API calls, outputs joined.

Scoring
Q: How is the overall score calculated?

Consistency×0.30 + (100−Fabrication%)×0.30 + Grammar×0.20 + Novelty×0.20

Q: How is the recommendation decided?

ACCEPT: consistency ≥ 75, fabrication ≤ 30, overall ≥ 70
REJECT: consistency < 40, fabrication > 70, overall < 40
Else: NEEDS REVISION

Q: How are scores extracted from LLM output?

String marker search — finds CONSISTENCY SCORE: in raw text, grabs the line, filters digits. If not found → returns safe default (50).

Scalability
Q: How would you scale this to 1000 papers/day?

Async parallel agents, Celery + Redis task queue, PostgreSQL instead of file cache, Docker + cloud auto-scaling, exponential backoff on API calls.

Q1: If a paper has 5 chunks, how many total API calls are made?

Answer:

Agent calls:
5 agents × 5 chunks each = 25 calls
Aggregation (if aggregation_strategy="summarize"):
+1 synthesis call per agent = 5 calls
Total:
Concatenate mode: 25 calls
Summarize mode: 30 calls
Q2: In the actual pipeline, how many API calls happen per paper?

Answer:

Exactly 5 API calls.

One call per agent:
Consistency
Grammar
Novelty
Fact-check
Authenticity

Reason:

_create_tasks() slices input using character limits ([:6000–8000])
Each agent receives ~500–2000 tokens
Chunking logic is never triggered
Q3: What happens for a large paper (e.g., 18,000 tokens)?

Answer:

Still exactly 5 LLM calls.

Flow:
18,000 token paper
        │
        ▼
_create_tasks() slices BEFORE LLM
        │
        ├── methodology[:8000 chars] → ~2k tokens → Agent 1 → 1 call
        ├── full_text[:6000 chars]   → ~1.5k tokens → Agent 2 → 1 call
        ├── abstract                → ~500 tokens  → Agent 3 → 1 call
        ├── full_text[:8000 chars]  → ~2k tokens → Agent 4 → 1 call
        └── results[:6000 chars]    → ~1.5k tokens → Agent 5 → 1 call

Key Insight:

The full 18k tokens are never sent to the LLM
Hard slicing trims input before inference
Q4: Does LLMManager handle chunking in the current pipeline?

Answer:

No — it is not used.

Evidence:
Only referenced:
Import statement
Initialization in constructor
Never called in:
evaluate_paper()
_create_tasks()
evaluate_from_pdf()
Actual Flow:
Raw paper text
      │
      ▼
_create_tasks() → slicing
      │
      ▼
CrewAI agents
      │
      ▼
LLM (5 calls)
Q5: What was LLMManager designed for?

Answer:

To support:

Token-based chunking
Overlap handling
Aggregation strategies:
concatenate
summarize

⚠️ Status: Implemented but not wired into pipeline

Q6: If LLMManager were integrated, how would it work?

Answer:

Designed Flow:
18,000 token paper
        │
        ▼
llm_manager.call_with_chunking()
        │
        ├── Chunk 1 → LLM → result 1
        ├── Chunk 2 → LLM → result 2
        │
        ├── concatenate → combine results
        │       OR
        └── summarize → extra LLM call
        │
        ▼
Final summarized text (~2k tokens)
        │
        ▼
_create_tasks()
        │
        ▼
5 agents → 5 calls
Q7: Total LLM calls with LLMManager enabled?
Step	Calls
Chunk processing (2 chunks)	2
Optional summarization	1
Agent evaluations	5
Total	7–8
Q8: Current vs Designed Pipeline Comparison
Aspect	Current Pipeline	With LLMManager
Preprocessing	Character slicing	Token chunking + LLM
Input quality	Truncated	Full coverage
Agent context	Partial paper	Summarized full paper
Total calls	5	7–8
Cost	Low	Moderate
Accuracy	Lower (lossy)	Higher
Q9: Key Engineering Insight
Current system is cost-optimized but lossy
Designed system is context-complete but higher cost
LLMManager enables:
Scalability for large documents
Better reasoning across full context
Controlled token usage
