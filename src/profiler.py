import pandas as pd

NULL_TOKENS = ["", "null", "n/a", "na", "none", "nan"]
DATE_RE = r"^(?:\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})$"


def load_csv(src) -> pd.DataFrame:
    """Read everything as text (so bad values are not hidden), then normalise null tokens."""
    df = pd.read_csv(src, dtype=str, keep_default_na=False, sep=None, engine="python")
    df.columns = [c.strip() for c in df.columns]
    df = df.apply(lambda s: s.str.strip())
    return df.mask(df.apply(lambda s: s.str.lower()).isin(NULL_TOKENS))


def infer_type(s: pd.Series) -> str:
    s = s.dropna()
    if s.empty:
        return "text"
    if pd.to_numeric(s, errors="coerce").notna().mean() >= 0.8:
        return "number"
    if s.str.match(DATE_RE).mean() >= 0.8:
        return "date"
    if s.str.contains("@", regex=False).mean() >= 0.8:
        return "email"
    return "text"


def schema_of(df: pd.DataFrame) -> dict:
    return {c: infer_type(df[c]) for c in df.columns}


def profile(df: pd.DataFrame, types: dict | None = None) -> pd.DataFrame:
    types = types or schema_of(df)
    rows = []
    for c in df.columns:
        s, t = df[c], types[c]
        r = {"column": c, "type": t, "nulls": int(s.isna().sum()),
             "null_pct": round(s.isna().mean() * 100, 1), "distinct": int(s.nunique())}
        if t == "number":
            n = pd.to_numeric(s, errors="coerce")
            r.update(min=n.min(), max=n.max(), mean=round(n.mean(), 2))
        rows.append(r)
    return pd.DataFrame(rows)