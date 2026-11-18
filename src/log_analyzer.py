import re

PATTERNS = [
    (r"column .*(not found|does not exist)|unknown column|missing column", "Schema change",
     "Source no longer provides a column the pipeline expects.",
     "Reports using that field fail or go blank.", "Confirm change with source team, update mappings, add schema check before load."),
    (r"duplicate key|unique constraint|primary key", "Duplicate records",
     "Same key loaded twice (re-run or overlapping extract).",
     "Totals double-count and the load is rejected.", "Switch to upsert/MERGE loads; de-duplicate staging."),
    (r"not-null|null value|cannot be null", "NULL in required field",
     "A mandatory field arrived empty.", "Records rejected; reports miss data.",
     "Trace missing values to source; add default/reject rules in staging."),
    (r"invalid (date|input syntax|format)|cannot (cast|convert)|conversion failed|rows rejected", "Format / data-type error",
     "Values do not match the expected format or type.", "Bad rows dropped or whole batch fails.",
     "Standardise formats (ISO dates, numeric casts) in a cleansing step."),
    (r"timeout|connection (refused|reset)|could not connect", "Connectivity / performance",
     "Pipeline could not reach the database in time.", "Data arrives late for daily reports.",
     "Check DB load/network, add retries with backoff, alert on SLA breach."),
    (r"out of memory|oom|heap space", "Resource exhaustion",
     "Job ran out of memory on a large batch.", "Nightly refresh fails; stale dashboards.", "Process in chunks; increase memory."),
    (r"permission denied|access denied|unauthorized", "Access issue",
     "Credentials/permissions changed.", "Loads cannot read or write data.", "Verify service-account grants; rotate secrets."),
    (r"disk full|no space", "Storage full",
     "Target/temp disk is full.", "Loads fail until space is freed.", "Free space, add retention policy, monitor capacity."),
]
_COMPILED = [(re.compile(p, re.I), *rest) for p, *rest in PATTERNS]
_LEVEL = re.compile(r"\b(WARN|WARNING|ERROR|FATAL|CRITICAL)\b", re.I)


def analyze_log(text: str):
    """Single pass over only the WARN/ERROR/FATAL lines; returns grouped findings."""
    lines = [l for l in text.splitlines() if _LEVEL.search(l)]
    found = {}
    for l in lines:
        for rx, title, cause, biz, fix in _COMPILED:
            if rx.search(l):
                f = found.setdefault(title, dict(title=title, cause=cause, business=biz, action=fix, lines=[]))
                f["lines"].append(l)
    return list(found.values())