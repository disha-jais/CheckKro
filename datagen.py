import numpy as np
import pandas as pd

def make_clean(n=5000, seed=0):
    r = np.random.default_rng(seed)
    order_date = pd.Timestamp("2024-01-01") + pd.to_timedelta(r.integers(0, 330, n), unit="D")
    return pd.DataFrame({
        "order_id": [f"ORD{i:06d}" for i in range(n)],
        "customer_age": np.clip(r.normal(36, 11, n).round(), 18, 75).astype(int),
        "order_amount": r.lognormal(6, 0.35, n).round(2),
        "rating": r.choice([1, 2, 3, 4, 5], n, p=[.05, .07, .18, .4, .3]),
        "city": r.choice(["Delhi", "Mumbai", "Bengaluru", "Pune", "Chennai"], n),
        "platform": r.choice(["Blinkit", "Zepto", "Instamart"], n),
        "order_date": order_date,
        "delivery_date": order_date + pd.to_timedelta(r.integers(0, 4, n), unit="D"),
        "refund_flag": (r.random(n) < 0.04).astype(int),
    })

def make_messy(n=5000, seed=0):
    r = np.random.default_rng(seed)
    df = make_clean(n, seed)
    pick = lambda frac: r.choice(n, int(n * frac), replace=False)

    df["rating"] = df["rating"].astype(float)
    df.loc[pick(0.08), "rating"] = np.nan            # real missing values
    df["city"] = df["city"].astype(object)
    df.loc[pick(0.05), "city"] = "N/A"               # disguised missing
    df.loc[pick(0.05), "platform"] = "blinkit"       # inconsistent casing
    df.loc[pick(0.01), "customer_age"] = 150         # impossible age
    df.loc[pick(0.02), "delivery_date"] = df["order_date"] - pd.Timedelta(days=3)  # delivered before ordered
    df.loc[pick(0.40), "refund_flag"] = 1            # implausible refund rate
    df = pd.concat([df, df.sample(frac=0.03, random_state=seed)], ignore_index=True)  # duplicate rows
    return df

if __name__ == "__main__":
    make_messy().to_csv("messy_orders.csv", index=False)
    print("Saved messy_orders.csv")
