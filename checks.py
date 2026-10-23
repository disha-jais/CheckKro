from dataclasses import dataclass
import pandas as pd

# Text values that really mean "missing" (including Excel error values)
MISSING_TOKENS = {"", "na", "n/a", "nan", "null", "none", "-", "--", "?", "unknown", "missing", "#n/a",
                  "#name?", "#ref!", "#div/0!", "#value!", "#num!", "#null!"}


@dataclass
class Finding:
    check: str        # which check found it
    column: str       # which column
    severity: str     # low / medium / high
    count: int        # how many rows affected
    pct: float        # percent of all rows
    detail: str       # what exactly was found
    why: str          # why it matters
    suggestion: str   # what to do


def is_text(s):
    return pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s)


def severity_from_pct(pct, high=20, medium=5):
    if pct >= high:
        return "high"
    if pct >= medium:
        return "medium"
    return "low"


def explained_by(df, col):
    """If the blanks in `col` follow a clean pattern in a small category column,
    return (that column, the values where `col` is blank). Otherwise None."""
    miss = df[col].isna()
    for other in df.columns:
        s = df[other]
        if other == col or not is_text(s) or not (2 <= s.nunique() <= 10):
            continue
        rate = miss.groupby(s).mean()
        if ((rate >= 0.95) | (rate <= 0.05)).all() and (rate >= 0.95).any() and (rate <= 0.05).any():
            return other, [str(v) for v in rate.index[rate >= 0.95]]
    return None


def check_missing(df):
    findings = []
    n = len(df)
    for col in df.columns:
        s = df[col]

        # 1. Real missing values (NaN)
        count = int(s.isna().sum())
        if count > 0:
            pct = round(count / n * 100, 2)
            why = explained_by(df, col) if pct >= 5 else None
            if why:
                other, vals = why
                findings.append(Finding(
                    check="structural_missing",
                    column=col,
                    severity="low",
                    count=count,
                    pct=pct,
                    detail=f"{pct}% of '{col}' is blank, but the pattern is explained by '{other}' (blank when it is: {', '.join(vals[:3])}). Probably by design, not an error.",
                    why="Blanks that follow a clear rule are usually expected, but they still limit what you can analyze.",
                    suggestion=f"Confirm the rule with the data owner, and analyze '{col}' only where it applies.",
                ))
            else:
                findings.append(Finding(
                    check="missing_values",
                    column=col,
                    severity=severity_from_pct(pct),
                    count=count,
                    pct=pct,
                    detail=f"{count} empty values ({pct}%) in '{col}'.",
                    why="Averages, counts and models can be skewed if missing rows are ignored.",
                    suggestion="Decide per column: fill (median/mode), drop rows, or leave and report it.",
                ))

        # 2. Hidden missing values (text like "N/A" or Excel's "#NAME?")
        if is_text(s):
            cleaned = s.dropna().astype(str).str.strip().str.lower()
            hidden = int(cleaned.isin(MISSING_TOKENS).sum())
            if hidden > 0:
                pct = round(hidden / n * 100, 2)
                findings.append(Finding(
                    check="disguised_missing",
                    column=col,
                    severity=severity_from_pct(pct),
                    count=hidden,
                    pct=pct,
                    detail=f"{hidden} values ({pct}%) in '{col}' look like placeholders for missing data (e.g. 'N/A' or '#NAME?').",
                    why="Normal missing-value checks miss these, so they get counted as real categories.",
                    suggestion="Convert these to real missing values before analysis.",
                ))
    return findings


import re

# ID columns named after these things are expected to repeat (one customer, many orders)
FOREIGN_KEY_WORDS = {"customer", "user", "driver", "client", "account", "member", "product",
                     "store", "vendor", "supplier", "session", "device", "employee", "patient", "student"}


def check_duplicates(df):
    findings = []
    n = len(df)

    # 1. Exact duplicate rows (every column identical)
    count = int(df.duplicated().sum())
    if count > 0:
        pct = round(count / n * 100, 2)
        findings.append(Finding(
            check="exact_duplicates",
            column="(all columns)",
            severity=severity_from_pct(pct, high=5, medium=1),
            count=count,
            pct=pct,
            detail=f"{count} rows ({pct}%) are exact copies of another row.",
            why="Duplicates inflate counts, revenue and averages.",
            suggestion="Remove exact duplicate rows, keeping the first copy.",
        ))

    # 2. Repeated IDs (same ID, but the rest of the row is different)
    unique_rows = df[~df.duplicated()]
    for col in df.columns:
        tokens = set(re.split(r"[^a-z0-9]+", str(col).lower()))
        if "id" in tokens and not (tokens & FOREIGN_KEY_WORDS):
            repeated = int(unique_rows[col].duplicated().sum())
            if 0 < repeated <= 0.05 * n:
                pct = round(repeated / n * 100, 2)
                findings.append(Finding(
                    check="duplicate_ids",
                    column=col,
                    severity=severity_from_pct(pct, high=5, medium=1),
                    count=repeated,
                    pct=pct,
                    detail=f"{repeated} rows ({pct}%) reuse an ID in '{col}' that already exists, with different data.",
                    why="An ID should identify one record. Repeats mean conflicting or mis-keyed data.",
                    suggestion="Investigate which version is correct before removing anything.",
                ))
    return findings


def check_formatting(df):
    findings = []
    n = len(df)
    for col in df.columns:
        s = df[col]
        if not is_text(s):
            continue
        values = s.dropna().astype(str)
        if len(values) == 0:
            continue

        # 1. Extra spaces at the start or end
        stripped = values.str.strip()
        spaces = int((values != stripped).sum())
        if spaces > 0:
            pct = round(spaces / n * 100, 2)
            findings.append(Finding(
                check="extra_whitespace",
                column=col,
                severity=severity_from_pct(pct, high=20, medium=5),
                count=spaces,
                pct=pct,
                detail=f"{spaces} values ({pct}%) in '{col}' have spaces at the start or end.",
                why="'Delhi' and 'Delhi ' look the same but group as different categories.",
                suggestion="Trim the spaces.",
            ))

        # 2. Inconsistent casing (same word, different capitalisation)
        if stripped.nunique() / len(stripped) < 0.5:
            counts = stripped.value_counts()
            table = pd.DataFrame({"raw": counts.index, "n": counts.values})
            table["key"] = table["raw"].str.lower()
            mixed = table.groupby("key").filter(lambda g: len(g) > 1)
            if len(mixed) > 0:
                minority = int(mixed.groupby("key")["n"].apply(lambda x: x.sum() - x.max()).sum())
                pct = round(minority / n * 100, 2)
                examples = ", ".join(f"'{v}'" for v in list(mixed["raw"])[:4])
                findings.append(Finding(
                    check="inconsistent_case",
                    column=col,
                    severity=severity_from_pct(pct, high=20, medium=5),
                    count=minority,
                    pct=pct,
                    detail=f"'{col}' has the same value written in different cases ({examples}). About {minority} rows ({pct}%) use the less common spelling.",
                    why="Group-bys and filters treat each spelling as a separate category, splitting your totals.",
                    suggestion="Standardise to one spelling (e.g. the most common one).",
                ))

        # 3. Numbers stored as text
        present = stripped[~stripped.str.lower().isin(MISSING_TOKENS)]
        if len(present) > 0:
            num = pd.to_numeric(present.str.replace(",", "", regex=False), errors="coerce")
            ratio = num.notna().mean()
            if ratio == 1:
                findings.append(Finding(
                    check="numeric_as_text",
                    column=col,
                    severity="low",
                    count=len(present),
                    pct=round(len(present) / n * 100, 2),
                    detail=f"'{col}' holds only numbers but is stored as text.",
                    why="Sorting and maths on text columns give wrong results.",
                    suggestion="Convert the column to a numeric type.",
                ))
            elif ratio >= 0.8:
                bad = int(num.isna().sum())
                pct = round(bad / n * 100, 2)
                findings.append(Finding(
                    check="mixed_types",
                    column=col,
                    severity=severity_from_pct(pct, high=5, medium=1),
                    count=bad,
                    pct=pct,
                    detail=f"'{col}' is mostly numbers, but {bad} values ({pct}%) are text.",
                    why="A few text values stop the whole column from being used as a number.",
                    suggestion="Find the text values and correct or remove them.",
                ))
    return findings


# Column-name words that tell us a value can never be negative
NON_NEGATIVE_WORDS = {"age", "price", "amount", "quantity", "qty", "count",
                      "total", "fee", "cost", "salary", "distance", "duration"}


def tokens_of(col):
    return set(re.split(r"[^a-z0-9]+", str(col).lower()))


def check_values(df):
    findings = []
    n = len(df)
    for col in df.columns:
        s = df[col]
        if not pd.api.types.is_numeric_dtype(s) or pd.api.types.is_bool_dtype(s):
            continue
        toks = tokens_of(col)
        if "id" in toks:
            continue

        # 1. Negative values where they make no sense
        if toks & NON_NEGATIVE_WORDS:
            neg = int((s < 0).sum())
            if neg > 0:
                pct = round(neg / n * 100, 2)
                findings.append(Finding(
                    check="impossible_values",
                    column=col,
                    severity="high",
                    count=neg,
                    pct=pct,
                    detail=f"{neg} rows ({pct}%) in '{col}' are negative, which should not be possible.",
                    why="Negative values usually mean entry errors or refunds mixed into sales data.",
                    suggestion="Check the source. Correct, separate or remove these rows.",
                ))

        # 2. Ages above 120
        if "age" in toks:
            too_old = int((s > 120).sum())
            if too_old > 0:
                pct = round(too_old / n * 100, 2)
                findings.append(Finding(
                    check="impossible_values",
                    column=col,
                    severity="high",
                    count=too_old,
                    pct=pct,
                    detail=f"{too_old} rows ({pct}%) in '{col}' are above 120, which is not a realistic age.",
                    why="Impossible ages distort averages and age-group analysis.",
                    suggestion="Treat as errors. Correct from source or set to missing.",
                ))

        # 3. Extreme outliers (far outside the normal range)
        if s.nunique() > 20:
            q1, q3 = s.quantile(0.25), s.quantile(0.75)
            iqr = q3 - q1
            if iqr > 0:
                low, high = q1 - 5 * iqr, q3 + 5 * iqr
                out = int(((s < low) | (s > high)).sum())
                if out > 0:
                    pct = round(out / n * 100, 2)
                    findings.append(Finding(
                        check="extreme_outliers",
                        column=col,
                        severity=severity_from_pct(pct, high=5, medium=1),
                        count=out,
                        pct=pct,
                        detail=f"{out} rows ({pct}%) in '{col}' fall outside {low:.1f} to {high:.1f}, far beyond the normal range.",
                        why="A few extreme values can drag averages and totals far from reality.",
                        suggestion="Check whether they are real. Keep, cap, or remove with a note.",
                    ))
    return findings


import warnings

# Pairs of (earlier event, later event) that must happen in this order
DATE_PAIRS = [("order", "deliver"), ("order", "ship"), ("start", "end"), ("created", "updated")]
# Date columns that are normally in the future, so we skip them
FUTURE_OK = ("expir", "due", "end", "renew", "next", "valid")
# Columns that are yes/no flags where a very high rate is suspicious
RATE_WORDS = {"refund", "cancel", "return", "fraud", "chargeback"}


def date_columns(df):
    out = {}
    for col in df.columns:
        s = df[col]
        if pd.api.types.is_datetime64_any_dtype(s):
            out[col] = s
        elif is_text(s):
            sample = s.dropna().astype(str).head(200)
            if len(sample) > 0 and sample.str.match(r"^\s*\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}").mean() >= 0.9:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    parsed = pd.to_datetime(s, errors="coerce")
                if parsed.notna().sum() >= 0.8 * s.notna().sum():
                    out[col] = parsed
    return out


def check_dates_and_patterns(df):
    findings = []
    n = len(df)
    dates = date_columns(df)

    # 1. Dates in the future
    now = pd.Timestamp.now()
    for col, d in dates.items():
        if any(w in col.lower() for w in FUTURE_OK):
            continue
        future = int((d > now).sum())
        if future > 0:
            pct = round(future / n * 100, 2)
            findings.append(Finding(
                check="future_dates", column=col, severity="high",
                count=future, pct=pct,
                detail=f"{future} rows ({pct}%) in '{col}' are dated in the future.",
                why="Events that have not happened yet cannot be in historical data.",
                suggestion="Check for typos in the year or a wrong date format.",
            ))

    # 2. Events happening in the wrong order
    for first, second in DATE_PAIRS:
        for a in [c for c in dates if first in c.lower()]:
            for b in [c for c in dates if second in c.lower() and c != a]:
                both = dates[a].notna() & dates[b].notna()
                bad = int((dates[a][both] > dates[b][both]).sum())
                if bad > 0:
                    pct = round(bad / n * 100, 2)
                    findings.append(Finding(
                        check="date_order", column=b, severity="high",
                        count=bad, pct=pct,
                        detail=f"{bad} rows ({pct}%) have '{b}' earlier than '{a}'.",
                        why="Time-based metrics (like delivery time) become negative or meaningless.",
                        suggestion="Check whether the two columns were swapped or mis-entered.",
                    ))

    # 3. Suspiciously high rates in yes/no flag columns
    for col in df.columns:
        if not (tokens_of(col) & RATE_WORDS):
            continue
        s = df[col].dropna()
        if len(s) == 0:
            continue
        if pd.api.types.is_numeric_dtype(s) and s.isin([0, 1]).all():
            rate = s.mean()
        elif is_text(s) and s.astype(str).str.strip().str.lower().isin(["yes", "no", "y", "n", "true", "false"]).all():
            rate = s.astype(str).str.strip().str.lower().isin(["yes", "y", "true"]).mean()
        else:
            continue
        if rate > 0.25:
            findings.append(Finding(
                check="suspicious_rate", column=col,
                severity="high" if rate >= 0.4 else "medium",
                count=int(round(rate * len(s))), pct=round(rate * 100, 2),
                detail=f"'{col}' is positive in {rate*100:.1f}% of rows, far higher than is normal for this kind of event (usually in the low single digits to low teens).",
                why="Rates this high often signal synthetic data, a logging bug, or a mislabeled column.",
                suggestion="Verify against the source system before drawing conclusions.",
            ))
    return findings


def overview(df):
    """The table an analyst prints first: type, missing %, unique count per column."""
    rows = []
    for col in df.columns:
        s = df[col]
        hidden = 0
        if is_text(s):
            hidden = int(s.dropna().astype(str).str.strip().str.lower().isin(MISSING_TOKENS).sum())
        rows.append({
            "column": col,
            "type": str(s.dtype),
            "missing_%": round((s.isna().sum() + hidden) / len(df) * 100, 2),
            "unique": int(s.nunique()),
            "example": s.dropna().iloc[0] if s.notna().any() else None,
        })
    return pd.DataFrame(rows)


def check_column_profile(df):
    findings = []
    n = len(df)
    for col in df.columns:
        s = df[col]
        present = s.dropna()

        # 1. Column with only one value
        if n > 1 and present.nunique() == 1:
            findings.append(Finding(
                check="constant_column", column=col, severity="low",
                count=n, pct=100.0,
                detail=f"'{col}' has the same value in every row.",
                why="A column that never changes carries no information for analysis.",
                suggestion="Drop it, or confirm it should really be constant.",
            ))

        # 2. Text column where every value is unique (looks like an ID or free text)
        if (is_text(s) and n > 20 and len(present) > 0
                and present.nunique() == len(present) and "id" not in tokens_of(col)):
            findings.append(Finding(
                check="all_unique_column", column=col, severity="low",
                count=len(present), pct=round(len(present) / n * 100, 2),
                detail=f"Every value in '{col}' is unique, so it is probably an identifier or free text.",
                why="It cannot be used to group or compare rows.",
                suggestion="Exclude it from group-by analysis, or confirm it is meant to be an ID.",
            ))

        # 3. Messy column name
        name = str(col)
        if name != name.strip() or re.search(r"[^A-Za-z0-9_]", name.strip()):
            findings.append(Finding(
                check="messy_column_name", column=col, severity="low",
                count=0, pct=0.0,
                detail=f"Column name '{col}' has spaces or special characters.",
                why="Awkward names cause errors in code, SQL and BI tools.",
                suggestion="Rename to lowercase_with_underscores.",
            ))
    return findings


def date_coverage(df):
    """Earliest date, latest date and number of distinct days for each date column."""
    rows = []
    for col, d in date_columns(df).items():
        days = d.dropna().dt.normalize()
        if len(days) == 0:
            continue
        rows.append({
            "column": col,
            "earliest": days.min().date(),
            "latest": days.max().date(),
            "span_days": (days.max() - days.min()).days + 1,
            "distinct_days": int(days.nunique()),
        })
    return pd.DataFrame(rows)


def check_date_gaps(df):
    findings = []
    for col, d in date_columns(df).items():
        days = d.dropna().dt.normalize().drop_duplicates().sort_values()
        if len(days) < 30:
            continue
        diffs = days.diff().dt.days.dropna()
        if diffs.median() > 1:          # not daily data, so gaps are normal
            continue
        big = diffs[diffs > 3]
        if len(big) == 0:
            continue
        span = (days.max() - days.min()).days + 1
        missing = int((big - 1).sum())
        pct = round(missing / span * 100, 2)
        worst = diffs.idxmax()
        start = days.shift(1).loc[worst].date()
        end = days.loc[worst].date()
        findings.append(Finding(
            check="date_gaps", column=col,
            severity=severity_from_pct(pct, high=10, medium=2),
            count=missing, pct=pct,
            detail=f"'{col}' has {missing} missing days ({pct}% of its range). Longest gap: {start} to {end}.",
            why="Gaps in a daily series quietly break trends, averages and week-on-week comparisons.",
            suggestion="Check whether the data was not collected or was lost in an extract.",
        ))
    return findings


def check_rare_categories(df):
    findings = []
    n = len(df)
    if n < 100:
        return findings
    for col in df.columns:
        s = df[col]
        if not is_text(s):
            continue
        values = s.dropna().astype(str).str.strip()
        if values.nunique() > 50 or values.nunique() / max(len(values), 1) >= 0.5:
            continue
        counts = values.value_counts()
        rare = [v for v, c in counts.items() if c <= 2 and v.lower() not in MISSING_TOKENS]
        if rare:
            examples = ", ".join(f"'{v}'" for v in rare[:5])
            findings.append(Finding(
                check="rare_categories", column=col, severity="low",
                count=len(rare), pct=round(len(rare) / n * 100, 2),
                detail=f"'{col}' has {len(rare)} values that appear only once or twice ({examples}).",
                why="Very rare category values are often typos or entry mistakes.",
                suggestion="Check whether they are real categories or misspellings of a common one.",
            ))
    return findings


ALL_CHECKS = [
    check_missing,
    check_duplicates,
    check_formatting,
    check_values,
    check_dates_and_patterns,
    check_column_profile,
    check_date_gaps,
    check_rare_categories,
]

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def run_checkup(df):
    """Run every check and return all findings, most serious first."""
    findings = []
    for check in ALL_CHECKS:
        findings.extend(check(df))
    findings.sort(key=lambda f: (SEVERITY_ORDER[f.severity], -f.pct))
    return findings
