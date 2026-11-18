from datetime import date


def build_markdown(table, n_rows, n_cols, score, issues, rule_results, log_findings, ai_text=""):
    r = [f"# Data Quality Report: {table}", f"Date: {date.today()}  |  Rows: {n_rows}  |  Columns: {n_cols}  |  Score: **{score}/100**", "", "## Issues"]
    for i, x in enumerate(issues, 1):
        r += [f"{i}. **[{x['severity'].upper()}] {x['type']}** ({x['column']}): {x['message']}",
              f"   - Business impact: {x['business']}", f"   - Likely causes: {'; '.join(x['causes'])}",
              f"   - Prevention: {x['prevention']}"]
    r += ["", "## Rule results"] + [f"- {x['column']} {x['type']} {x.get('param','')}: {x['status']} ({x['pass_rate']}%)" for x in rule_results]
    if log_findings:
        r += ["", "## Pipeline log analysis"] + [f"- **{f['title']}**: {f['cause']} Action: {f['action']}" for f in log_findings]
    if ai_text:
        r += ["", "## AI root-cause analysis", ai_text]
    return "\n".join(r)