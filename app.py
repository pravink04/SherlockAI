import io, json, math, os, re
from collections import Counter
from html import escape as esc

import pandas as pd
import streamlit as st

from src.profiler import load_csv, profile
from src.detector import detect_all, quality_score
from src.rules import RULE_TYPES, load_rules, save_rules, evaluate
from src.log_analyzer import analyze_log
from src.ai_engine import build_context, root_cause_report, chat
from src.report import build_markdown

st.set_page_config(page_title="DQ·RCA Command Center", page_icon="🛰️", layout="wide", initial_sidebar_state="expanded")
SEV = {"high": "#fb2c5f", "medium": "#ffb020", "low": "#64748b"}


def H(html: str):
    """Render raw HTML on one line so Markdown never turns it into a code block."""
    st.markdown(re.sub(r"\n\s*", "", html), unsafe_allow_html=True)


H("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=JetBrains+Mono:wght@400;600;800&display=swap');
:root{--cy:#22d3ee;--pu:#a78bfa;--pk:#f472b6;--gr:#10f0a0;--bg:#050816;--card:#0b1226cc;--bd:#1b2a4a}
.stApp{background:radial-gradient(1100px 600px at 8% -10%,#3b2a8f40,transparent),radial-gradient(900px 520px at 100% 0%,#0891b240,transparent),radial-gradient(800px 500px at 50% 120%,#be185d30,transparent),var(--bg);color:#e2e8f0;font-family:Inter,sans-serif}
.stApp:before{content:"";position:fixed;inset:0;background-image:linear-gradient(#ffffff06 1px,transparent 1px),linear-gradient(90deg,#ffffff06 1px,transparent 1px);background-size:44px 44px;pointer-events:none;mask-image:radial-gradient(circle at 50% 30%,#000,transparent 75%)}
[data-testid="stHeader"]{background:transparent}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#0a1230,#070b1c);border-right:1px solid var(--bd)}
code,pre{font-family:'JetBrains Mono',monospace!important}
@keyframes fadeup{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
@keyframes shine{to{background-position:200% center}}
@keyframes float{0%,100%{transform:translate(0,0) scale(1)}50%{transform:translate(-18px,14px) scale(1.12)}}
@keyframes pulse{0%,100%{box-shadow:0 0 0 0 var(--c)}50%{box-shadow:0 0 26px 4px var(--c)}}
@keyframes tick{to{transform:translateX(-50%)}}
@keyframes scan{from{transform:translateY(-100%)}to{transform:translateY(100%)}}
.hero{position:relative;overflow:hidden;padding:30px 32px;border-radius:22px;border:1px solid #2b3f7a;background:linear-gradient(125deg,#0a1433,#150f3d 55%,#0a2a3d);box-shadow:0 0 60px #22d3ee1a,inset 0 0 60px #7c3aed12;margin-bottom:12px;animation:fadeup .7s}
.hero .orb{position:absolute;right:-60px;top:-80px;width:340px;height:340px;border-radius:50%;background:radial-gradient(circle at 35% 35%,#22d3ee99,#7c3aed66 45%,transparent 70%);filter:blur(8px);animation:float 9s ease-in-out infinite}
.hero .scan{position:absolute;inset:0;background:linear-gradient(transparent,#22d3ee14,transparent);height:40%;animation:scan 5s linear infinite;pointer-events:none}
.hero .eyebrow{font:600 11px 'JetBrains Mono',monospace;letter-spacing:.3em;color:var(--cy);margin-bottom:6px}
.hero h1{position:relative;margin:0;font-size:40px;line-height:1.1;font-weight:800;letter-spacing:-.03em;background:linear-gradient(90deg,#fff,#22d3ee,#a78bfa,#f472b6,#fff);background-size:250% auto;-webkit-background-clip:text;-webkit-text-fill-color:transparent;animation:shine 6s linear infinite}
.hero p{position:relative;margin:8px 0 14px;color:#9fb0d0;font-size:15px;max-width:720px}
.chip{position:relative;display:inline-block;margin:0 6px 6px 0;padding:4px 12px;border-radius:20px;font:600 11px 'JetBrains Mono',monospace;border:1px solid #2a3a5e;color:#c3d0ea;background:#0a1226aa}
.chip.on{border-color:#22d3ee77;color:var(--cy);box-shadow:0 0 14px #22d3ee2a}
.ticker{overflow:hidden;white-space:nowrap;border:1px solid var(--bd);border-radius:12px;background:#080e22;margin-bottom:14px;padding:8px 0}
.ticker div{display:inline-block;animation:tick 32s linear infinite;font:600 12px 'JetBrains Mono',monospace;color:#9fb0d0}
.ticker span{margin:0 28px}
.kpi{position:relative;padding:16px 18px;border-radius:16px;background:var(--card);border:1px solid var(--bd);backdrop-filter:blur(8px);overflow:hidden;animation:fadeup .6s both}
.kpi:before{content:"";position:absolute;left:0;top:0;height:3px;width:100%;background:linear-gradient(90deg,var(--c),transparent)}
.kpi .l{color:#8da0c4;font-size:11px;text-transform:uppercase;letter-spacing:.16em}
.kpi .v{font:800 34px 'JetBrains Mono',monospace;color:var(--c);text-shadow:0 0 22px var(--c)}
.kpi .s{color:#64769a;font-size:12px}
.panel{padding:18px;border-radius:18px;background:var(--card);border:1px solid var(--bd);margin-bottom:14px;backdrop-filter:blur(8px);animation:fadeup .7s both}
.panel h4{margin:0 0 12px;font:600 12px 'JetBrains Mono',monospace;color:#8da0c4;text-transform:uppercase;letter-spacing:.2em}
.gauge{width:178px;height:178px;border-radius:50%;margin:auto;display:grid;place-items:center;background:conic-gradient(var(--c) calc(var(--p)*1%),#16213d 0);box-shadow:0 0 40px var(--c)}
.gauge div{width:140px;height:140px;border-radius:50%;background:#070d20;display:grid;place-items:center;font:800 42px 'JetBrains Mono',monospace;color:var(--c);text-shadow:0 0 20px var(--c)}
.gl{text-align:center;color:#8da0c4;font-size:12px;margin-top:10px}
.bar{display:flex;align-items:center;gap:10px;margin:9px 0;font-size:13px}
.bar b{width:140px;font-weight:600;color:#cbd5e1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.bar .t{flex:1;height:8px;border-radius:6px;background:#16213d;overflow:hidden}
.bar .t i{display:block;height:100%;border-radius:6px;background:linear-gradient(90deg,var(--c),#fff3);box-shadow:0 0 12px var(--c)}
.bar span{font:600 12px 'JetBrains Mono',monospace;color:#9fb0d0;width:34px;text-align:right}
.donut{width:150px;height:150px;border-radius:50%;margin:6px auto 10px;display:grid;place-items:center}
.donut div{width:96px;height:96px;border-radius:50%;background:#070d20;display:grid;place-items:center;font:800 26px 'JetBrains Mono',monospace}
.flow{display:flex;align-items:center;justify-content:space-between;gap:6px;flex-wrap:wrap}
.node{flex:1;min-width:120px;text-align:center;padding:16px 8px;border-radius:16px;border:1px solid var(--c);background:linear-gradient(180deg,#0e1730,#0a1126);--c:#10f0a0}
.node .ic{font-size:26px}.node b{display:block;margin-top:4px}.node small{color:#8da0c4;font:600 11px 'JetBrains Mono',monospace}
.node.fail{--c:#fb2c5f;animation:pulse 1.8s infinite}.node.warn{--c:#ffb020}.node.ok{--c:#10f0a0}
.arrow{color:#3b4f80;font-size:22px}
.badge{display:inline-block;padding:2px 10px;border-radius:6px;font:700 10px 'JetBrains Mono',monospace;text-transform:uppercase;color:#fff;background:var(--c);box-shadow:0 0 12px var(--c)}
.icard{padding:16px 18px;border-radius:14px;background:var(--card);border:1px solid var(--bd);border-left:4px solid var(--c);margin:12px 0 4px;animation:fadeup .5s both}
.icard .t{font-weight:700;font-size:16px}.icard .c{color:var(--cy);font:600 12px 'JetBrains Mono',monospace}
.icard p{margin:6px 0 0;color:#cbd5e1;font-size:14px}.icard .b{color:#8da0c4}
.prio{border:1px solid #fb2c5f66;background:linear-gradient(120deg,#2a0b1c,#0b1226);box-shadow:0 0 40px #fb2c5f22}
.hm{display:grid;gap:3px;font:600 9px 'JetBrains Mono',monospace}
.hm div{height:15px;border-radius:3px;background:#10f0a01c}
.hm .h{height:auto;background:none;color:#8da0c4;padding:0 0 4px;overflow:hidden;text-overflow:ellipsis}
.hm .nl{background:#fb2c5f;box-shadow:0 0 8px #fb2c5f}.hm .bd{background:#ffb020;box-shadow:0 0 8px #ffb020}.hm .dp{background:#a78bfa;box-shadow:0 0 8px #a78bfa}
.leg span{margin-right:16px;font-size:12px;color:#8da0c4}.leg i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:6px}
.log{font:12px/1.75 'JetBrains Mono',monospace;background:#03050f;border:1px solid var(--bd);border-radius:12px;padding:14px;max-height:280px;overflow:auto;white-space:pre}
.log .ERROR,.log .FATAL{color:#ff6b8b}.log .WARN{color:#ffc857}.log .INFO{color:#5b6b8c}
.stTabs [data-baseweb="tab-list"]{gap:6px;border-bottom:1px solid var(--bd)}
.stTabs [data-baseweb="tab"]{background:transparent;border-radius:10px 10px 0 0;color:#8da0c4;padding:10px 16px;font-weight:600}
.stTabs [aria-selected="true"]{color:var(--cy)!important;background:#22d3ee14}
.stButton>button,.stDownloadButton>button{background:linear-gradient(90deg,#0891b2,#7c3aed,#db2777);background-size:200% auto;color:#fff;border:0;border-radius:12px;font-weight:700;padding:.5rem 1.1rem;transition:.3s}
.stButton>button:hover{background-position:right center;box-shadow:0 0 28px #22d3ee66;transform:translateY(-1px)}
[data-testid="stExpander"]{border:1px solid var(--bd);border-radius:14px;background:#0b122688}
[data-testid="stChatMessage"]{background:#0b1226aa;border:1px solid var(--bd);border-radius:14px}
</style>""")


@st.cache_data(show_spinner=False)
def analyse(csv_bytes, baseline_json, table):
    df = load_csv(io.BytesIO(csv_bytes))
    issues, types = detect_all(df, json.loads(baseline_json) if baseline_json else None, table=table)
    return df, profile(df, types), issues, types


def kpi(label, value, sub, color, delay=0):
    return f"<div class='kpi' style='--c:{color};animation-delay:{delay}s'><div class='l'>{label}</div><div class='v'>{value}</div><div class='s'>{sub}</div></div>"


def bars(items, color_fn):
    mx = max([v for _, v in items] or [1]) or 1
    return "".join(f"<div class='bar' style='--c:{color_fn(k)}'><b>{esc(str(k))}</b><div class='t'><i style='width:{v/mx*100:.0f}%'></i></div><span>{v}</span></div>" for k, v in items)


def dims(df, issues, rules, has_base):
    n = max(len(df), 1)
    bad = sum(i["count"] for i in issues if i["type"] in ("Invalid records", "Format inconsistency", "Outliers"))
    drift = sum({"high": 30, "medium": 12, "low": 4}[i["severity"]] for i in issues if i["type"] == "Schema drift")
    rr = [r["pass_rate"] for r in rules] or [100]
    return [100 * (1 - df.isna().sum().sum() / max(df.size, 1)), 100 * (1 - df.duplicated().sum() / n),
            100 * (1 - min(bad, n) / n), 100 - min(drift, 100) if has_base else 100, sum(rr) / len(rr)]


def radar(vals, labels, size=270):
    cx = cy = size / 2; R = size / 2 - 52; n = len(vals)
    pt = lambda i, r: (cx + r * math.cos(-math.pi / 2 + 2 * math.pi * i / n), cy + r * math.sin(-math.pi / 2 + 2 * math.pi * i / n))
    grid = "".join("<polygon points='%s' fill='none' stroke='#1b2a4a'/>" % " ".join("%.1f,%.1f" % pt(i, R * k / 4) for i in range(n)) for k in range(1, 5))
    axes = "".join("<line x1='%.1f' y1='%.1f' x2='%.1f' y2='%.1f' stroke='#1b2a4a'/>" % (cx, cy, *pt(i, R)) for i in range(n))
    poly = " ".join("%.1f,%.1f" % pt(i, R * v / 100) for i, v in enumerate(vals))
    dots = "".join("<circle cx='%.1f' cy='%.1f' r='4' fill='#22d3ee'/>" % pt(i, R * v / 100) for i, v in enumerate(vals))
    labs = "".join("<text x='%.1f' y='%.1f' fill='#9fb0d0' font-size='11' text-anchor='middle' font-family='JetBrains Mono'>%s %d%%</text>" % (*pt(i, R + 26), l, vals[i]) for i, l in enumerate(labels))
    return (f"<svg viewBox='0 0 {size} {size}' width='100%' style='max-width:{size}px;display:block;margin:auto'>{grid}{axes}"
            f"<polygon points='{poly}' fill='#22d3ee33' stroke='#22d3ee' stroke-width='2' style='filter:drop-shadow(0 0 8px #22d3ee)'/>{dots}{labs}</svg>")


STAGES = [("📥", "Extract"), ("🛡️", "Validate"), ("⚙️", "Transform"), ("🗄️", "Load"), ("📊", "Publish")]
LOG_STAGE = {"Schema change": 0, "Access issue": 0, "NULL in required field": 1, "Format / data-type error": 2,
             "Resource exhaustion": 2, "Duplicate records": 3, "Connectivity / performance": 3, "Storage full": 3}
ISSUE_STAGE = {"Schema drift": 0, "NULL values": 1, "Invalid records": 1, "Outliers": 1, "Format inconsistency": 2, "Duplicates": 3}


def pipeline_flow(issues, log_findings):
    fails, warns = Counter(), Counter()
    for f in log_findings:
        fails[LOG_STAGE.get(f["title"], 2)] += len(f["lines"])
    for i in issues:
        warns[ISSUE_STAGE.get(i["type"], 1)] += 1
    nodes = []
    for k, (ic, name) in enumerate(STAGES):
        if k == 4:
            st_, txt = ("fail", "blocked") if fails else ("warn", "at risk") if warns else ("ok", "healthy")
        else:
            st_, txt = ("fail", f"{fails[k]} errors") if fails[k] else ("warn", f"{warns[k]} issues") if warns[k] else ("ok", "healthy")
        nodes.append(f"<div class='node {st_}'><div class='ic'>{ic}</div><b>{name}</b><small>{txt}</small></div>")
    return "<div class='arrow'>➜</div>".join(nodes)


def same(v, ex):
    try:
        return float(v) == float(ex)
    except (TypeError, ValueError):
        return str(v) == str(ex)


def health_map(df, issues, n=36):
    sub, bad = df.head(n), {}
    for i in issues:
        if i["type"] in ("Invalid records", "Format inconsistency", "Outliers") and i["column"] in df.columns:
            bad.setdefault(i["column"], []).extend(i["examples"])
    dup = df.duplicated(keep=False).head(n).tolist()
    cells = [f"<div class='h'>{esc(c)}</div>" for c in df.columns]
    for ri, (_, r) in enumerate(sub.iterrows()):
        for c in df.columns:
            v = r[c]
            cls = "nl" if pd.isna(v) else "bd" if any(same(v, e) for e in bad.get(c, [])) else "dp" if dup[ri] else ""
            cells.append(f"<div class='{cls}' title='{esc(str(v))}'></div>")
    return f"<div class='hm' style='grid-template-columns:repeat({len(df.columns)},1fr)'>{''.join(cells)}</div>"


# ───────────── Sidebar ─────────────
with st.sidebar:
    H("<div style='font:800 22px Inter;background:linear-gradient(90deg,#22d3ee,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent'>🛰️ DQ·RCA</div><div style='color:#64769a;font-size:12px;margin-bottom:14px'>Command Center</div>")
    up = st.file_uploader("📂 Dataset (CSV)", type=["csv", "tsv", "txt"])
    base_up = st.file_uploader("🧬 Baseline schema (JSON)", type="json")
    log_up = st.file_uploader("📜 ETL log", type=["log", "txt"])
    if st.button("⚡ Load sample scenario", use_container_width=True):
        st.session_state.sample = True
    sev_filter = st.multiselect("Severity filter", ["high", "medium", "low"], default=["high", "medium", "low"])
    prov = os.getenv("LLM_PROVIDER", "gemini").lower()
    has_key = bool(os.getenv("GEMINI_API_KEY" if prov == "gemini" else "GROQ_API_KEY"))
    H(f"<span class='chip {'on' if has_key else ''}'>LLM · {prov.upper()} {'● online' if has_key else '○ no key'}</span>")

sample = st.session_state.get("sample")
if up:
    csv_bytes, table = up.getvalue(), up.name.rsplit(".", 1)[0]
elif sample:
    csv_bytes, table = open("data/orders.csv", "rb").read(), "orders"
else:
    H("<div class='hero'><div class='orb'></div><div class='scan'></div><div class='eyebrow'>GENAI · DATA ENGINEERING</div><h1>AI Data Quality &<br>Root-Cause Command Center</h1><p>Profile datasets, detect anomalies and schema drift, trace pipeline failures to their root cause and get ready-to-run SQL and Python fixes. Upload a file or load the sample scenario from the sidebar.</p><span class='chip on'>profiling</span><span class='chip on'>anomaly detection</span><span class='chip on'>schema drift</span><span class='chip on'>log RCA</span><span class='chip on'>GenAI copilot</span></div>")
    st.stop()

use_sample_files = bool(sample and not up)
baseline_json = base_up.getvalue().decode() if base_up else (open("data/baseline_schema.json").read() if use_sample_files else "")
log_text = log_up.getvalue().decode(errors="ignore") if log_up else (open("data/etl.log").read() if use_sample_files else "")

df, prof, issues, types = analyse(csv_bytes, baseline_json, table)
log_findings = analyze_log(log_text) if log_text else []

if st.session_state.get("table") != table:
    st.session_state.update(table=table, rules=load_rules(columns=set(df.columns)), ai="", chat=[])
rule_results = evaluate(df, st.session_state.rules)
score = quality_score(issues)
context = build_context(table, len(df), score, issues, rule_results, log_findings)
sc_col = "#10f0a0" if score >= 80 else "#ffb020" if score >= 50 else "#fb2c5f"
passed = sum(r["status"] == "PASS" for r in rule_results)
sev_count = Counter(i["severity"] for i in issues)

# ───────────── Hero, ticker, KPIs ─────────────
H(f"""<div class='hero'><div class='orb'></div><div class='scan'></div><div class='eyebrow'>LIVE ANALYSIS · {esc(table.upper())}</div>
<h1>AI Data Quality &<br>Root-Cause Command Center</h1>
<p>{len(df):,} records scanned · {len(issues)} findings · {len(log_findings)} pipeline failure patterns correlated</p>
<span class='chip on'>● PROFILED</span><span class='chip {'on' if baseline_json else ''}'>SCHEMA {'MONITORED' if baseline_json else 'NO BASELINE'}</span>
<span class='chip {'on' if log_text else ''}'>LOG {'CORRELATED' if log_text else 'NONE'}</span><span class='chip on'>{len(rule_results)} RULES ACTIVE</span></div>""")
alerts = "".join(f"<span style='color:{SEV[i['severity']]}'>● {esc(i['type'])} · {esc(i['column'])}</span><span>{esc(i['message'][:90])}</span>" for i in issues[:8]) or "<span style='color:#10f0a0'>● All systems healthy</span>"
H(f"<div class='ticker'><div>{alerts}{alerts}</div></div>")
k = st.columns(5)
for n, (col, (l, v, s, c)) in enumerate(zip(k, [("Records", f"{len(df):,}", "rows scanned", "#22d3ee"), ("Fields", df.shape[1], "columns profiled", "#a78bfa"),
                                                ("Findings", len(issues), f"{sev_count['high']} critical", "#fb2c5f"), ("Rules passed", f"{passed}/{len(rule_results)}", "quality rules", "#10f0a0"),
                                                ("Health score", score, "out of 100", sc_col)])):
    col.markdown(kpi(l, v, s, c, n * .08), unsafe_allow_html=True)
st.write("")

t_ov, t_pr, t_is, t_ru, t_lg, t_ai, t_rp = st.tabs(["🧭 Command Center", "📊 Profile", "🚨 Issues & Fixes", "✅ Rules", "📜 Pipeline Logs", "🧠 AI Copilot", "📄 Report"])

with t_ov:
    a, b, c = st.columns([1, 1.15, 1])
    with a:
        H(f"<div class='panel'><h4>Health score</h4><div class='gauge' style='--p:{score};--c:{sc_col}'><div>{score}</div></div><div class='gl'>{'Excellent' if score >= 80 else 'Needs attention' if score >= 50 else 'Critical'}</div></div>")
    with b:
        H("<div class='panel'><h4>Quality dimensions</h4>" + radar(dims(df, issues, rule_results, bool(baseline_json)), ["Complete", "Unique", "Valid", "Consistent", "Rules"]) + "</div>")
    with c:
        tot = max(sum(sev_count.values()), 1); h, m = sev_count["high"] / tot * 100, sev_count["medium"] / tot * 100
        grad = f"conic-gradient(#fb2c5f 0 {h}%,#ffb020 {h}% {h + m}%,#64748b {h + m}% 100%)" if issues else "conic-gradient(#10f0a0 0 100%)"
        H(f"<div class='panel'><h4>Severity mix</h4><div class='donut' style='background:{grad}'><div>{len(issues)}</div></div>"
          + bars([(s, sev_count.get(s, 0)) for s in ("high", "medium", "low")], lambda s: SEV[s]) + "</div>")
    H("<div class='panel'><h4>Pipeline flow · failure point</h4><div class='flow'>" + pipeline_flow(issues, log_findings) + "</div></div>")
    if issues:
        top = issues[0]
        H(f"""<div class='icard prio' style='--c:{SEV[top["severity"]]}'><span class='badge' style='--c:{SEV[top["severity"]]}'>priority #1</span>
        &nbsp;<span class='t'>{esc(top["type"])}</span> <span class='c'>· {esc(top["column"])}</span>
        <p>{esc(top["message"])}</p><p class='b'>💼 {esc(top["business"])}</p><p>🛡️ {esc(top["prevention"])}</p></div>""")
        st.code(top["sql"], language="sql")
    H("<div class='panel'><h4>Data health map · first 36 rows</h4>" + health_map(df, issues) +
      "<div class='leg' style='margin-top:12px'><span><i style='background:#10f0a03a'></i>valid</span><span><i style='background:#fb2c5f'></i>NULL</span><span><i style='background:#ffb020'></i>invalid / outlier</span><span><i style='background:#a78bfa'></i>duplicate row</span></div></div>")

with t_pr:
    p = prof.copy(); p.insert(3, "completeness", 100 - p["null_pct"])
    st.dataframe(p, use_container_width=True, hide_index=True,
                 column_config={"completeness": st.column_config.ProgressColumn("completeness", min_value=0, max_value=100, format="%.0f%%"), "null_pct": None})
    with st.expander("Raw data preview"):
        st.dataframe(df.head(50), use_container_width=True)

with t_is:
    shown = [i for i in issues if i["severity"] in sev_filter]
    if not shown:
        st.success("No issues for the selected filter 🎉")
    for i in shown:
        H(f"""<div class='icard' style='--c:{SEV[i["severity"]]}'><span class='badge' style='--c:{SEV[i["severity"]]}'>{i["severity"]}</span>
        &nbsp;<span class='t'>{esc(i["type"])}</span> <span class='c'>· {esc(i["column"])} · {i["count"]}</span>
        <p>{esc(i["message"])}</p><p class='b'>💼 {esc(i["business"])}</p></div>""")
        with st.expander("Root causes · SQL · Python · Prevention"):
            st.markdown("**Likely root causes**\n" + "\n".join(f"- {x}" for x in i["causes"]))
            s1, s2 = st.tabs(["SQL fix", "Python fix"])
            s1.code(i["sql"], language="sql"); s2.code(i["python"], language="python")
            st.info(f"🛡️ Prevention: {i['prevention']}")

with t_ru:
    with st.form("add_rule", clear_on_submit=True):
        x, y, z, w = st.columns([1.2, 1, 1.4, .6])
        col, typ, par = x.selectbox("Column", df.columns), y.selectbox("Rule", RULE_TYPES), z.text_input("Parameter")
        if w.form_submit_button("➕ Add"):
            st.session_state.rules.append({"column": col, "type": typ, "param": par})
            save_rules(st.session_state.rules); st.rerun()
    if rule_results:
        st.dataframe(pd.DataFrame(rule_results).drop(columns=["total"], errors="ignore"), use_container_width=True, hide_index=True,
                     column_config={"pass_rate": st.column_config.ProgressColumn("pass %", min_value=0, max_value=100, format="%.1f%%")})
    else:
        st.info("No rules yet for this dataset. Add one using the form above.")

with t_lg:
    if not log_text:
        st.info("Upload an ETL log in the sidebar.")
    else:
        lines = "<br>".join(f"<span class='{(re.search(r'WARN|ERROR|FATAL|INFO', l) or [None])[0] or ''}'>{esc(l)}</span>" for l in log_text.splitlines()[:200])
        H(f"<div class='panel'><h4>Pipeline log</h4><div class='log'>{lines}</div></div>")
        for f in log_findings:
            H(f"""<div class='icard' style='--c:#22d3ee'><span class='t'>{esc(f["title"])}</span> <span class='c'>· {len(f["lines"])} line(s)</span>
            <p><b>Cause:</b> {esc(f["cause"])}</p><p class='b'>💼 {esc(f["business"])}</p><p>🔧 {esc(f["action"])}</p></div>""")

with t_ai:
    if st.button("🧠 Generate root-cause analysis"):
        with st.spinner("Correlating data issues with pipeline errors..."):
            st.session_state.ai = root_cause_report(context)
    if st.session_state.ai:
        st.markdown(st.session_state.ai)
    st.divider()
    for m_ in st.session_state.chat:
        st.chat_message(m_["role"]).write(m_["content"])
    if q := st.chat_input("Ask: why did the load fail? how do I fix duplicates?"):
        st.chat_message("user").write(q)
        with st.spinner("Thinking..."):
            ans = chat(q, context, st.session_state.chat)
        st.chat_message("assistant").write(ans)
        st.session_state.chat += [{"role": "user", "content": q}, {"role": "assistant", "content": ans}]

with t_rp:
    md = build_markdown(table, len(df), df.shape[1], score, issues, rule_results, log_findings, st.session_state.ai)
    st.download_button("⬇️ Download report (.md)", md, f"{table}_dq_report.md")
    st.markdown(md)