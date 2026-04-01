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