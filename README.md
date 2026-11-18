# 🛰️ AI Data Quality & Root-Cause Analysis Copilot

An AI-powered copilot that profiles datasets, detects data-quality problems, correlates them with ETL/pipeline error logs, explains the root cause in plain business language, and generates ready-to-run SQL and Python fixes.

Built for **Data Engineers, ETL Developers and Data Quality teams**.

> Screenshot: add `docs/dashboard.png` here

---

## Why this project?

Data pipelines move data from source systems into warehouses and analytics platforms. When something goes wrong (NULLs, duplicates, wrong formats, schema changes, failed loads), business reports quietly become wrong. Finding out *what* broke, *why*, and *how to fix it* is slow and manual.

This copilot automates that investigation.

## Features

| Capability | What it does |
|---|---|
| **Dataset upload** | Upload a CSV/TSV; everything is read as text first so bad values are never hidden |
| **Automated profiling** | Column types, NULL counts, distinct values, min/max/mean, completeness |
| **Issue detection** | NULLs, duplicates, outliers (IQR), invalid emails, wrong date formats, non-numeric values in numeric columns, negative amounts |
| **Schema drift detection** | Compares the dataset against a baseline schema: missing columns, new columns, type changes |
| **Rule engine** | `not_null`, `unique`, `regex`, `min`, `max`, `allowed`, with per-rule pass rates; rules can be added from the UI |
| **ETL log analysis** | Maps WARN/ERROR/FATAL log lines to 8 known failure patterns with cause, business impact and action |
| **Root-cause analysis** | LLM correlates data issues with log errors into a root-cause chain |
| **Business-language explanations** | Every issue includes its business impact and likely causes |
| **Fix generation** | SQL and pandas snippets per issue |
| **Prevention advice** | Recommendation per issue type to avoid repeats |
| **Interactive AI chat** | Ask questions about your data problems; the LLM answers from the detected findings |
| **Reports** | Downloadable Markdown data-quality report |
| **Command-center UI** | Health score, quality-dimension radar, severity mix, pipeline-flow failure point, data health map, alert ticker |

## Architecture

```
CSV ──► load_csv ──► detect_all ──► issues + quality score ─┐
Baseline schema (JSON) ───────────────┘                     │
Rules ──► evaluate ──► pass/fail ───────────────────────────┤
ETL log ──► analyze_log ──► failure patterns ───────────────┤
                                                            ▼
                                        build_context (compact summary)
                                                            ▼
                                        Gemini / Groq  ──► root cause, chat
                                                            ▼
                                              Streamlit UI + Markdown report
```

**Design principle: rule-based first, AI second.** Counts, SQL and root-cause candidates come from deterministic code. The LLM only explains and correlates them. This keeps results reproducible, reduces hallucination, and the app still works without an API key.

**Privacy:** the LLM never receives raw rows, only a compact text summary of findings.

## Tech stack

- Python 3.10+
- pandas, numpy
- Streamlit (UI)
- Google Gemini (`google-genai`) or Groq (`groq`) as the LLM provider

## Project structure

```
.
├── app.py                 # Streamlit UI
├── generate_data.py       # creates sample dataset, baseline schema and ETL log
├── requirements.txt
├── .env                   # API keys (not committed)
├── data/                  # sample files, saved rules (rules.json)
└── src/
    ├── profiler.py        # loading, type inference, profiling
    ├── detector.py        # issue detection, quality score
    ├── rules.py           # rule engine
    ├── log_analyzer.py    # ETL log pattern analysis
    ├── ai_engine.py       # LLM wrapper (Gemini/Groq), context builder, chat
    └── report.py          # Markdown report generator
```

## Getting started

### 1. Clone and create a virtual environment

```bash
git clone <your-repo-url>
cd <project-folder>
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure the LLM

Create a `.env` file in the project root:

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_key
GROQ_API_KEY=your_groq_key
GEMINI_MODEL=gemini-2.5-flash
GROQ_MODEL=llama-3.3-70b-versatile
```

- Set `LLM_PROVIDER` to `gemini` or `groq`.
- Free keys: [Google AI Studio](https://aistudio.google.com) and [Groq Console](https://console.groq.com).
- Model names change over time; check the provider docs and update the `.env` values if needed.
- Without a key, profiling, detection, rules, logs and reports still work. Only the AI root-cause and chat features are unavailable.

> Never commit `.env`. Add it to `.gitignore`.

### 4. Generate sample data

```bash
python generate_data.py
```

Creates `data/orders.csv` (with deliberate problems), `data/baseline_schema.json` and `data/etl.log`.

### 5. Run the app

```bash
streamlit run app.py
```

Click **Load sample scenario** in the sidebar.

## Usage

1. **Load data**: upload a CSV, optionally a baseline schema JSON and an ETL log, or use the sample scenario.
2. **Command Center**: health score, quality dimensions, severity mix, the pipeline stage where failures occur, and the priority-1 issue with its SQL fix.
3. **Profile**: per-column statistics and completeness.
4. **Issues & Fixes**: each finding with business impact, root causes, SQL fix, Python fix and prevention advice. Use the sidebar severity filter.
5. **Rules**: review pass rates and add your own rules.
6. **Pipeline Logs**: colour-coded log view with root-cause cards.
7. **AI Copilot**: generate a root-cause analysis and ask follow-up questions.
8. **Report**: download the Markdown report.

### Baseline schema format

```json
{
  "order_id": "number",
  "customer_email": "email",
  "order_date": "date",
  "amount": "number",
  "country": "text"
}
```

Supported types: `number`, `date`, `email`, `text`.

### Rule types

| Type | Parameter | Example |
|---|---|---|
| `not_null` | none | `customer_email` must not be empty |
| `unique` | none | `order_id` must be unique |
| `regex` | pattern | `order_date` matches `^\d{4}-\d{2}-\d{2}$` |
| `min` / `max` | number | `amount` ≥ 0 |
| `allowed` | comma-separated values | `country` in `IN,US,UK` |

## Sample scenario

The sample dataset deliberately contains:

- NULL and blank values in several columns
- A duplicate order (`order_id` 1005)
- An invalid email (`john@example`)
- A mixed date format (`11/03/2026`)
- A non-numeric amount (`12x`), a negative amount (`-40`) and an outlier (`980000`)
- A missing expected column (`status`) and an unexpected new column (`discount_code`)

The sample ETL log contains matching errors (schema change, duplicate key, NULL constraint, type error, connection timeout), so the copilot can link log failures to the data issues behind them.

## How the quality score works

Starts at 100 and subtracts a penalty per issue: **high −12, medium −6, low −2** (minimum 0). It is a simple heuristic meant for comparing runs, not a certified metric.

## Extending

- **New log patterns**: add an entry to `PATTERNS` in `src/log_analyzer.py`.
- **New detectors**: add a function in `src/detector.py` returning issues via `_issue(...)` and include it in `detect_all`.
- **New LLM provider**: add a branch in `ask_llm` in `src/ai_engine.py`.
- **Database input**: load a table with `pd.read_sql` (SQLAlchemy) and pass the DataFrame into the detectors.

## Limitations

- Column type inference is heuristic (80% rule) and can misjudge edge cases.
- Outlier detection uses IQR only.
- Log analysis covers 8 pattern families; other errors are not classified.
- Datasets are loaded fully in memory, so very large files need sampling or chunking.
- Direct database connections are not built in (CSV only).
- LLM answers depend on the findings passed to it and should be reviewed before applying fixes to production data.

## Roadmap

- Agentic auto-fix: generate a fix, run it in a sandbox, show before/after quality score, apply on approval, with audit log and rollback
- Direct database connectors (PostgreSQL, MySQL, SQLite)
- Multi-agent incident response (log detective, fixer, business communicator)
- Trend tracking of quality score across runs
- PDF report export
- Unit tests and CI

## Author

**Your Name** · [LinkedIn](#) · [GitHub](#)

## License

Add your license (for example MIT).
