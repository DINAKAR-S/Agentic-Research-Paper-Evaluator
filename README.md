# 🔬 Agentic Research Paper Evaluator

An AI-powered multi-agent system that performs automated peer-review of arXiv research papers.
Paste an arXiv ID / URL — or upload a PDF — and receive a structured **Judgement Report** in under 3 minutes.

---

## Features

- **Web scraping** — downloads and parses arXiv PDFs automatically
- **Section decomposition** — extracts Abstract, Methodology, Results, Conclusion
- **5 specialized CrewAI agents** running sequentially:
  - **Consistency Agent** — checks if methodology supports the claimed results (0–100)
  - **Grammar Agent** — evaluates writing quality and academic tone (High / Medium / Low)
  - **Novelty Agent** — compares against existing literature (Novel / Incremental / Derivative)
  - **Fact-Check Agent** — verifies constants, formulas, and cited data (✓ / ⚠ / ✗)
  - **Authenticity Agent** — detects fabrication red flags, calculates risk % (0–100%)
- **PDF upload** — evaluate any local PDF, not just arXiv papers
- **Judgement Report** — overall score, recommendation (ACCEPT / NEEDS REVISION / REJECT), download as JSON or Markdown

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Multi-agent framework | [CrewAI](https://crewai.com) 1.12.2 |
| LLM | OpenAI **GPT-4o-mini** |
| PDF parsing | PyMuPDF |
| arXiv integration | arxiv Python library |
| Web UI | Streamlit |
| Token management | tiktoken (16 k limit enforced per call) |

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/your-username/arxiv-evaluator.git
cd arxiv-evaluator
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure your OpenAI API key

Copy `.env.example` to `.env` and fill in your key:

```bash
cp .env.example .env
```

Edit `.env`:

```env
OPENAI_API_KEY=sk-proj-your-key-here
PRIMARY_MODEL=gpt-4o-mini
MAX_TOKENS_PER_CALL=16000
```

> Get an API key at [platform.openai.com](https://platform.openai.com)

### 4. Run the app

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---
## Demo Video 

Check Demo here [Video Link](https://drive.google.com/file/d/1yKjOoLSWrOSEJ4f51zaskQVUnTcE35cS/view?usp=sharing)

---

## Usage

### Option A — arXiv paper
1. Enter an arXiv ID (e.g. `2303.08774`) or full URL
2. Click **Evaluate Paper**
3. Wait ~1–3 minutes for all agents to finish
4. View scores, recommendation, and detailed findings per agent
5. Download the report as **JSON** or **Markdown**

### Option B — Upload a PDF
1. Click the **Upload PDF** tab
2. Select any research paper PDF from your computer
3. Click **Evaluate PDF**

### Quick example papers (built into the UI)

| Paper | arXiv ID |
|-------|----------|
| GPT-4 Technical Report | `2303.08774` |
| Attention Is All You Need | `1706.03762` |
| BERT | `1810.04805` |
| ResNet | `1512.03385` |

---

## Scoring

| Metric | Weight | Scale |
|--------|--------|-------|
| Consistency | 30% | 0–100 |
| Authenticity (inverse risk) | 30% | `100 − Fabrication%` |
| Grammar | 20% | HIGH=100, MEDIUM=60, LOW=20 |
| Novelty | 20% | Novel=100, Incremental=60, Derivative=20 |

**Recommendation thresholds:**

| Result | Condition |
|--------|-----------|
| ✅ ACCEPT | Consistency ≥ 75 **and** Fabrication Risk ≤ 30 **and** Overall ≥ 70 |
| ❌ REJECT | Consistency < 40 **or** Fabrication Risk > 70 **or** Overall < 40 |
| ⚠️ NEEDS REVISION | Everything else |

---

## Project Structure

```
arxiv-evaluator/
├── app.py                  # Streamlit web UI
├── main.py                 # CLI interface
├── evaluator.py            # Main orchestrator (CrewAI crew + report compiler)
├── agents/
│   ├── __init__.py
│   ├── consistency_agent.py
│   ├── grammar_agent.py
│   ├── novelty_agent.py
│   ├── factcheck_agent.py
│   └── authenticity_agent.py
├── core/
│   ├── __init__.py
│   ├── arxiv_client.py     # arXiv download + PDF text extraction
│   └── llm_manager.py      # LLM provider abstraction (OpenAI / OpenRouter / Gemini)
├── tests/
│   └── test_system.py
├── .env.example            # Environment variable template
├── .gitignore
└── requirements.txt
```

---

## CLI Usage

```bash
# Evaluate by arXiv ID
python main.py --arxiv-id 2303.08774

# Evaluate by URL
python main.py --url https://arxiv.org/abs/2303.08774

# Save report to a file
python main.py --arxiv-id 2303.08774 --output report.json   --format json
python main.py --arxiv-id 2303.08774 --output report.md     --format markdown
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | **Yes** | — | OpenAI API key |
| `PRIMARY_MODEL` | No | `gpt-4o-mini` | Model used by CrewAI agents |
| `MAX_TOKENS_PER_CALL` | No | `16000` | Token cap per LLM call |
| `OPENROUTER_API_KEY` | No | — | Optional: route via OpenRouter |
| `GOOGLE_API_KEY` | No | — | Optional: use Google Gemini |
| `CACHE_DIR` | No | `./cache/papers` | Local PDF cache directory |

---

## Notes

- **Token limit**: every LLM call is capped at 16 000 tokens (assignment requirement)
- **Cost**: GPT-4o-mini is very cheap — one full evaluation typically costs < $0.05
- **PDF cache**: downloaded arXiv PDFs are saved in `cache/papers/` to avoid re-downloading the same paper
- **⚠️ Disclaimer**: results are AI-generated and should be validated by human domain experts

---

## License

MIT
