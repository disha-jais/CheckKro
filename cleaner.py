import numpy as np
import pandas as pd
from checks import MISSING_TOKENS, is_text


def clean(df):
    """Apply only safe fixes. Returns (cleaned_df, change_log)."""
    out = df.copy()
    log = []

    # 1. Trim extra spaces in text columns
    for col in out.columns:
        if not is_text(out[col]):
            continue
        s = out[col]
        trimmed = s.map(lambda v: v.strip() if isinstance(v, str) else v)
        changed = int(((s != trimmed) & s.notna()).sum())
        if changed > 0:
            out[col] = trimmed
            log.append({"action": "trimmed spaces", "column": col, "rows_affected": changed})

    # 2. Turn placeholders like "N/A" into real missing values
    for col in out.columns:
        if not is_text(out[col]):
            continue
        mask = out[col].map(lambda v: isinstance(v, str) and v.strip().lower() in MISSING_TOKENS)
        count = int(mask.sum())
        if count > 0:
            out.loc[mask, col] = np.nan
            log.append({"action": "placeholder -> missing", "column": col, "rows_affected": count})

    # 3. Remove exact duplicate rows (keep the first copy)
    before = len(out)
    out = out.drop_duplicates().reset_index(drop=True)
    removed = before - len(out)
    if removed > 0:
        log.append({"action": "removed duplicate rows", "column": "(all columns)", "rows_affected": removed})

    return out, pd.DataFrame(log, columns=["action", "column", "rows_affected"])
