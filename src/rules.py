import json, pathlib
import pandas as pd

RULE_TYPES = ["not_null", "unique", "regex", "min", "max", "allowed"]
DEFAULT_RULES = [
    {"column": "order_id", "type": "unique", "param": ""},
    {"column": "customer_email", "type": "not_null", "param": ""},
    {"column": "amount", "type": "min", "param": "0"},
    {"column": "country", "type": "not_null", "param": ""},
    {"column": "order_date", "type": "regex", "param": r"^\d{4}-\d{2}-\d{2}$"},
]


def load_rules(path="data/rules.json", columns=None):
    p = pathlib.Path(path)
    rules = json.loads(p.read_text()) if p.exists() else DEFAULT_RULES
    return [r for r in rules if columns is None or r["column"] in columns]


def save_rules(rules, path="data/rules.json"):
    pathlib.Path(path).write_text(json.dumps(rules, indent=2))


def evaluate(df, rules):
    out = []
    for r in rules:
        c, t, p = r["column"], r["type"], str(r.get("param", ""))
        res = {**r, "total": len(df), "passed": 0, "pass_rate": 0.0, "status": "ERROR", "failed_rows": []}
        try:
            s = df[c]
            if t == "not_null": ok = s.notna()
            elif t == "unique": ok = s.notna() & ~s.duplicated(keep=False)
            elif t == "regex": ok = s.fillna("").str.match(p)
            elif t == "min": ok = pd.to_numeric(s, errors="coerce") >= float(p)
            elif t == "max": ok = pd.to_numeric(s, errors="coerce") <= float(p)
            elif t == "allowed": ok = s.isin([x.strip() for x in p.split(",")])
            else: raise ValueError(t)
            ok = ok.fillna(False)
            res.update(passed=int(ok.sum()), pass_rate=float(round(ok.mean() * 100, 1)),
                       status="PASS" if ok.all() else "FAIL", failed_rows=df.index[~ok][:5].tolist())
        except Exception as e:
            res["note"] = str(e)
        out.append(res)
    return out