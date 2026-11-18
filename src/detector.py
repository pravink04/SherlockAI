import pandas as pd
from .profiler import schema_of

EMAIL_RE = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
ISO_RE = r"^\d{4}-\d{2}-\d{2}$"
MONEY_HINT = ("amount", "price", "qty", "quantity", "total")
WEIGHT = {"high": 12, "medium": 6, "low": 2}


def _issue(sev, typ, col, count, msg, biz, causes, sql="", py="", prevent="", examples=None):
    return dict(severity=sev, type=typ, column=col, count=int(count), message=msg, business=biz,
                causes=causes, sql=sql, python=py, prevention=prevent, examples=(examples or [])[:5])


def _nulls(df, types, t):
    out = []
    for c in df.columns:
        n = int(df[c].isna().sum())
        if n:
            pct = n / len(df) * 100
            out.append(_issue(
                "high" if pct >= 20 else "medium", "NULL values", c, n,
                f"{n} of {len(df)} rows ({pct:.0f}%) have no value in '{c}'.",
                f"Reports using '{c}' will under-count or skip these records.",
                ["Source allows blank/optional field", "Upstream join or lookup found no match",
                 "Extract dropped values (encoding, delimiter, truncation)"],
                f"SELECT * FROM {t} WHERE {c} IS NULL;\nUPDATE {t} SET {c} = 'UNKNOWN' WHERE {c} IS NULL;",
                f'df["{c}"] = df["{c}"].fillna("UNKNOWN")   # or df.dropna(subset=["{c}"])',
                f"Add a NOT NULL constraint / validation rule on '{c}' at ingestion."))
    return out


def _duplicates(df, key, t):
    full = int(df.duplicated().sum())
    kd = int(df[key].dropna().duplicated().sum()) if key in df else 0
    if not (full or kd):
        return []
    ex = df[df[key].duplicated(keep=False) & df[key].notna()][key].unique().tolist()
    return [_issue(
        "high", "Duplicates", key, max(full, kd),
        f"{full} fully duplicate rows and {kd} repeated values of key '{key}'.",
        "Revenue and counts are inflated because the same record is counted twice.",
        ["Pipeline re-ran/retried without idempotent load", "Overlapping extract windows",
         "No primary key / unique constraint in target"],
        f"SELECT {key}, COUNT(*) FROM {t} GROUP BY {key} HAVING COUNT(*) > 1;\n"
        f"DELETE FROM {t} a USING {t} b WHERE a.ctid > b.ctid AND a.{key} = b.{key};\n"
        f"ALTER TABLE {t} ADD PRIMARY KEY ({key});",
        f'df = df.drop_duplicates().drop_duplicates(subset=["{key}"], keep="last")',
        "Use MERGE/UPSERT loads, enforce a primary key, use watermark-based incremental extracts.", ex)]


def _outliers(df, types, t):
    out = []
    for c, ty in types.items():
        if ty != "number":
            continue
        n = pd.to_numeric(df[c], errors="coerce").dropna()
        if len(n) < 4:
            continue
        q1, q3 = n.quantile([.25, .75]); iqr = q3 - q1
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        bad = n[(n < lo) | (n > hi)]
        if len(bad):
            out.append(_issue(
                "medium", "Outliers", c, len(bad),
                f"{len(bad)} value(s) in '{c}' outside [{lo:.1f}, {hi:.1f}]: {bad.tolist()}.",
                "Extreme values skew averages/totals; often typos or unit mix-ups.",
                ["Manual entry typo / extra zeros", "Unit or currency mismatch", "Test record in production"],
                f"SELECT * FROM {t} WHERE {c} NOT BETWEEN {lo:.1f} AND {hi:.1f};",
                f'q1,q3 = df["{c}"].astype(float).quantile([.25,.75]); iqr = q3-q1',
                "Add range checks and anomaly alerts on numeric measures.", bad.tolist()))
    return out


def _invalid(df, types, t):
    out = []
    for c, ty in types.items():
        s = df[c].dropna()
        if ty == "number":
            num = pd.to_numeric(s, errors="coerce")
            bad = s[num.isna()]
            if len(bad):
                out.append(_issue(
                    "high", "Invalid records", c, len(bad),
                    f"{len(bad)} non-numeric value(s) in numeric column '{c}': {bad.tolist()}.",
                    "These rows cannot be summed and will fail or be rejected during load.",
                    ["Free text in source", "Column shift / wrong delimiter", "Upstream type change"],
                    f"SELECT * FROM {t} WHERE {c} !~ '^-?[0-9]+(\\.[0-9]+)?$';",
                    f'df["{c}"] = pd.to_numeric(df["{c}"], errors="coerce")',
                    "Validate data types in a staging layer before loading.", bad.tolist()))
            if any(h in c.lower() for h in MONEY_HINT):
                neg = num[num < 0]
                if len(neg):
                    out.append(_issue(
                        "medium", "Invalid records", c, len(neg),
                        f"{len(neg)} negative value(s) in '{c}': {neg.tolist()}.",
                        "Negative amounts reduce totals; may be refunds or sign errors.",
                        ["Refunds without a transaction-type flag", "Sign error in source"],
                        f"SELECT * FROM {t} WHERE {c} < 0;", f'df[df["{c}"].astype(float) < 0]',
                        f"Add rule '{c} >= 0' or move refunds to a separate table.", neg.tolist()))
        elif ty == "email":
            bad = s[~s.str.match(EMAIL_RE)]
            if len(bad):
                out.append(_issue(
                    "medium", "Invalid records", c, len(bad),
                    f"{len(bad)} malformed email(s) in '{c}': {bad.tolist()}.",
                    "Emails will bounce and customer matching will fail.",
                    ["No format validation at source", "Truncated values"],
                    f"SELECT * FROM {t} WHERE {c} !~ '^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$';",
                    f'df[~df["{c}"].fillna("").str.match(r"{EMAIL_RE}")]',
                    "Validate email format at entry and in the pipeline.", bad.tolist()))
        elif ty == "date":
            bad = s[~s.str.match(ISO_RE)]
            if len(bad):
                out.append(_issue(
                    "high", "Format inconsistency", c, len(bad),
                    f"{len(bad)} date(s) in '{c}' not in YYYY-MM-DD: {bad.tolist()}.",
                    "Date reports may misplace records (11/03 = 3 Nov or 11 Mar?).",
                    ["Two source systems use different date formats", "Locale changed in manual export",
                     "Parser has no explicit format"],
                    f"SELECT * FROM {t} WHERE {c} !~ '^\\d{{4}}-\\d{{2}}-\\d{{2}}$';",
                    f'df["{c}"] = pd.to_datetime(df["{c}"], format="mixed", errors="coerce").dt.strftime("%Y-%m-%d")',
                    "Standardise on ISO-8601 and fail fast on unknown formats.", bad.tolist()))
    return out


def _schema(types, baseline, t):
    if not baseline:
        return []
    out, cur = [], set(types)
    miss, new = [c for c in baseline if c not in cur], [c for c in types if c not in baseline]
    if miss:
        out.append(_issue("high", "Schema drift", ", ".join(miss), len(miss),
            f"Expected column(s) missing: {miss}.", "Reports using these columns will break or show blanks.",
            ["Source removed/renamed column without notice", "Extract query/file layout changed", "Wrong file version"],
            f"SELECT column_name FROM information_schema.columns WHERE table_name = '{t}';",
            f"missing = set({list(baseline)}) - set(df.columns)",
            "Introduce data contracts and schema-change alerts with the source team.", miss))
    if new:
        out.append(_issue("low", "Schema drift", ", ".join(new), len(new),
            f"New unexpected column(s): {new}.", "Usually harmless but may signal an unannounced upstream release.",
            ["New field added upstream"], f"ALTER TABLE {t} ADD COLUMN {new[0]} TEXT;",
            "df = df[list(expected_columns)]  # or extend the schema", "Review upstream changes before accepting new columns.", new))
    for c, ty in types.items():
        if c in baseline and baseline[c] != ty:
            out.append(_issue("medium", "Schema drift", c, 1, f"'{c}' was {baseline[c]}, now looks like {ty}.",
                "Type changes cause load failures or silent mis-conversion.",
                ["Upstream type change", "Bad values polluting the column"],
                f"ALTER TABLE {t} ALTER COLUMN {c} TYPE TEXT;", f'df["{c}"] = df["{c}"].astype(str)',
                "Enforce schema on read."))
    return out


def detect_all(df, baseline=None, key=None, table="my_table"):
    """One pass: infer types once, run every detector, return issues sorted by severity."""
    types = schema_of(df)
    key = key or df.columns[0]
    issues = (_nulls(df, types, table) + _duplicates(df, key, table) + _outliers(df, types, table)
              + _invalid(df, types, table) + _schema(types, baseline, table))
    return sorted(issues, key=lambda i: -WEIGHT[i["severity"]]), types


def quality_score(issues):
    return max(0, 100 - sum(WEIGHT[i["severity"]] for i in issues))