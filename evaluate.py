import numpy as np
import pandas as pd
import checks
from datagen import make_clean

KINDS = [
    "missing_values", "disguised_missing", "exact_duplicates", "duplicate_ids",
    "extra_whitespace", "inconsistent_case", "mixed_types", "numeric_as_text",
    "negative_amount", "impossible_age", "extreme_outliers", "future_dates",
    "date_order", "suspicious_rate", "date_gaps", "constant_column", "rare_categories",
]

DATASETS = [(3000, 1), (5000, 2), (8000, 3)]   # (rows, seed)


def inject(base, kind, seed):
    """Plant ONE known error. Returns (data, expected_check, expected_column, expected_count)."""
    r = np.random.default_rng(seed)
    df = base.copy()
    n = len(df)

    def pick(frac):
        return r.choice(n, max(int(n * frac), 3), replace=False)

    if kind == "missing_values":
        idx = pick(0.08)
        df["rating"] = df["rating"].astype(float)
        df.loc[idx, "rating"] = np.nan
        return df, "missing_values", "rating", len(idx)

    if kind == "disguised_missing":
        idx = pick(0.05)
        df["city"] = df["city"].astype(object)
        df.loc[idx, "city"] = "N/A"
        return df, "disguised_missing", "city", len(idx)

    if kind == "exact_duplicates":
        copies = df.sample(frac=0.03, random_state=seed)
        df = pd.concat([df, copies], ignore_index=True)
        return df, "exact_duplicates", None, len(copies)

    if kind == "duplicate_ids":
        idx = r.choice(n, 40, replace=False)
        df.loc[idx[:20], "order_id"] = df.loc[idx[20:], "order_id"].values
        return df, "duplicate_ids", "order_id", 20

    if kind == "extra_whitespace":
        idx = pick(0.05)
        df["city"] = df["city"].astype(object)
        df.loc[idx, "city"] = df.loc[idx, "city"].astype(str) + " "
        return df, "extra_whitespace", "city", len(idx)

    if kind == "inconsistent_case":
        idx = pick(0.05)
        df["platform"] = df["platform"].astype(object)
        df.loc[idx, "platform"] = df.loc[idx, "platform"].astype(str).str.lower()
        return df, "inconsistent_case", "platform", len(idx)

    if kind == "mixed_types":
        idx = pick(0.02)
        df["order_amount"] = df["order_amount"].astype(object)
        df.loc[idx, "order_amount"] = "abc"
        return df, "mixed_types", "order_amount", len(idx)

    if kind == "numeric_as_text":
        df["order_amount"] = df["order_amount"].astype(str)
        return df, "numeric_as_text", "order_amount", None

    if kind == "negative_amount":
        idx = pick(0.01)
        df.loc[idx, "order_amount"] = -df.loc[idx, "order_amount"].abs()
        return df, "impossible_values", "order_amount", len(idx)

    if kind == "impossible_age":
        idx = pick(0.01)
        df.loc[idx, "customer_age"] = 150
        return df, "impossible_values", "customer_age", len(idx)

    if kind == "extreme_outliers":
        idx = pick(0.005)
        df.loc[idx, "order_amount"] = df.loc[idx, "order_amount"] * 1000
        return df, "extreme_outliers", "order_amount", len(idx)

    if kind == "future_dates":
        idx = pick(0.01)
        df.loc[idx, "order_date"] = df.loc[idx, "order_date"] + pd.Timedelta(days=1800)
        return df, "future_dates", "order_date", len(idx)

    if kind == "date_order":
        idx = pick(0.02)
        df.loc[idx, "delivery_date"] = df.loc[idx, "order_date"] - pd.Timedelta(days=3)
        return df, "date_order", "delivery_date", len(idx)

    if kind == "suspicious_rate":
        idx = pick(0.40)
        df.loc[idx, "refund_flag"] = 1
        return df, "suspicious_rate", "refund_flag", None

    if kind == "date_gaps":
        start = df["order_date"].min().normalize()
        window = (df["order_date"] >= start + pd.Timedelta(days=100)) & \
                 (df["order_date"] <= start + pd.Timedelta(days=120))
        df = df[~window].reset_index(drop=True)
        return df, "date_gaps", "order_date", 21

    if kind == "constant_column":
        df["platform"] = "Blinkit"
        return df, "constant_column", "platform", None

    if kind == "rare_categories":
        idx = r.choice(n, 3, replace=False)
        df["city"] = df["city"].astype(object)
        df.loc[idx[:2], "city"] = "Dehli"
        df.loc[idx[2], "city"] = "Mumbia"
        return df, "rare_categories", "city", None

    raise ValueError(kind)


def detected(findings, check, column, expected_count):
    """Caught = right check, right column, and it found most of the planted rows."""
    for f in findings:
        if f.check == check and (column is None or f.column == column):
            if expected_count is None or f.count >= 0.8 * expected_count:
                return True
    return False


def run_evaluation():
    rows, false_alarms = [], []
    for size, seed in DATASETS:
        base = make_clean(size, seed)
        serious = [f for f in checks.run_checkup(base) if f.severity in ("medium", "high")]
        false_alarms.append(len(serious))
        for kind in KINDS:
            bad, check, col, exp = inject(base, kind, seed)
            found = checks.run_checkup(bad)
            rows.append({
                "dataset": f"{size} rows",
                "error": kind,
                "caught": detected(found, check, col, exp),
            })
    return pd.DataFrame(rows), false_alarms
