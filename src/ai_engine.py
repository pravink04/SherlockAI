import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()

SYSTEM = ("You are a senior data-quality and ETL expert. Use ONLY the findings provided. "
          "Explain in simple business language, be concise, and never invent facts or numbers.")


@lru_cache(maxsize=1)
def _client(provider):
    if provider == "gemini":
        from google import genai
        return genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    from groq import Groq
    return Groq(api_key=os.getenv("GROQ_API_KEY"))


def ask_llm(prompt, system=SYSTEM, history=None):
    provider = os.getenv("LLM_PROVIDER", "groq").lower()
    try:
        c = _client(provider)
        if provider == "gemini":
            hist = "".join(f"{m['role']}: {m['content']}\n" for m in (history or []))
            r = c.models.generate_content(model=os.getenv("GROQ_MODEL"),
                                          contents=f"{system}\n\n{hist}{prompt}")
            return r.text
        msgs = [{"role": "system", "content": system}] + (history or []) + [{"role": "user", "content": prompt}]
        r = c.chat.completions.create(model=os.getenv("GROQ_MODEL"), messages=msgs, temperature=0.2)
        return r.choices[0].message.content
    except Exception as e:  # app keeps working without the LLM
        return f"⚠️ AI unavailable ({type(e).__name__}: {e}). Rule-based results above are still valid."


def build_context(table, n_rows, score, issues, rule_results, log_findings):
    """Compact summary so the LLM gets facts, not the raw data (cheap + private)."""
    L = [f"Table {table}: {n_rows} rows, quality score {score}/100", "ISSUES:"]
    L += [f"- [{i['severity']}] {i['type']} in {i['column']}: {i['message']}" for i in issues]
    L.append("RULES:")
    L += [f"- {r['column']} {r['type']} {r.get('param','')}: {r['status']} ({r['pass_rate']}%)" for r in rule_results]
    L.append("LOG FINDINGS:")
    L += [f"- {f['title']}: {f['lines'][0]}" for f in log_findings] or ["- none"]
    return "\n".join(L)


def root_cause_report(context):
    return ask_llm(
        f"{context}\n\nWrite: 1) Executive summary (3 lines, no jargon) 2) Most likely root cause chain "
        "linking data issues with log errors 3) Top 3 fixes in priority order, each with a SQL or Python snippet "
        "4) Prevention checklist.")


def chat(question, context, history):
    return ask_llm(f"Context:\n{context}\n\nQuestion: {question}", history=history[-6:])