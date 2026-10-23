import pandas as pd
from checks import tokens_of, date_columns, DATE_PAIRS

MONEY_WORDS = {"amount", "price", "total", "revenue", "cost", "fee", "sales"}


def money_columns(df):
    return [c for c in df.columns
            if pd.api.types.is_numeric_dtype(df[c]) and tokens_of(c) & MONEY_WORDS]


def impact(df, f):
    """One plain sentence on what a finding does to your numbers (or None)."""
    c, col = f.check, f.column

    if c == "exact_duplicates":
        dup = df[df.duplicated()]
        parts = []
        for m in money_columns(df):
            true_total = df[m].sum() - dup[m].sum()
            if true_total:
                parts.append(f"total '{m}' is overstated by {dup[m].sum() / true_total * 100:.1f}%")
        parts.append(f"the row count is overstated by {len(dup)}")
        return "Duplicates: " + " and ".join(parts) + "."

    if c in ("missing_values", "disguised_missing"):
        return (f"{f.pct}% of rows have no usable '{col}', so any analysis by '{col}' "
                f"covers only {100 - f.pct:.1f}% of the data.")

    if c in ("impossible_values", "extreme_outliers"):
        s = df[col]
        toks = tokens_of(col)
        if c == "impossible_values":
            bad = (s < 0) | ((s > 120) if "age" in toks else False)
        else:
            q1, q3 = s.quantile(0.25), s.quantile(0.75)
            iqr = q3 - q1
            bad = (s < q1 - 5 * iqr) | (s > q3 + 5 * iqr)
        if bad.sum() == 0 or (~bad).sum() == 0:
            return None
        with_bad, without = s.mean(), s[~bad].mean()
        shift = (with_bad - without) / without * 100 if without else 0
        return (f"The average '{col}' is {with_bad:.2f} with these rows and {without:.2f} without "
                f"({shift:+.1f}% shift).")

    if c == "date_order":
        dates = date_columns(df)
        for first, second in DATE_PAIRS:
            if second in col.lower():
                for a in [x for x in dates if first in x.lower() and x != col]:
                    gap = (dates[col] - dates[a]).dt.days
                    return (f"{f.pct}% of rows have a negative time between '{a}' and '{col}'. "
                            f"The average gap is {gap.mean():.2f} days with them and "
                            f"{gap[gap >= 0].mean():.2f} days without.")

    if c == "suspicious_rate":
        return (f"'{col}' reads {f.pct}% where the normal range is a few percent to the low teens, "
                f"so any rate, cost or trend built on it is unreliable.")

    if c == "inconsistent_case":
        return (f"Grouping by '{col}' splits one category into several, so each shows a smaller "
                f"total than it should ({f.pct}% of rows use the minority spelling).")

    return None
