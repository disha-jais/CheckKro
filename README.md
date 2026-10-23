# 🛡️ CheckKro

**🔍 Know if your data is safe to analyze.**

CheckKro checks any CSV file the way an analyst would on first opening it, and answers one question: **Can I trust this data?** It gives you a trust score out of 100, a plain-language verdict, and an explanation of how each problem affects your numbers.

🚀 **Live Demo:** *(Add the link after deploying)*  
💻 **Source Code:** *(Add the GitHub link)*

## 📸 Screenshots

_Add two or three screenshots after deploying:_

- 🎯 Verdict card
- 🔎 Findings tab
- 📊 Charts tab

Include both light and dark modes to showcase the interface.

## ✨ What It Does

1. **🔍 Detects data quality issues**  
   Checks for 19 kinds of problems analysts look for first, including missing and hidden-missing values, duplicate rows and IDs, formatting mistakes, impossible values, extreme outliers, date errors, suspicious rates, and more.

2. **🚦 Gives a verdict in plain language**  
   Displays a trust score with a color-coded bar (green, amber, or red) and a verdict card, such as:  
   > ⚠️ 1 issue needs your attention: Vehicle Images has placeholder values in 100% of rows.

3. **📉 Explains the impact on your numbers**  
   Goes beyond reporting "150 duplicate rows" to explain the business impact, such as "total order amount is overstated by 3.1%".

4. **🧹 Cleans data safely**  
   Only trims spaces, converts placeholders such as `N/A` and `#NAME?` into real blanks, and removes exact duplicates. Every change is recorded in a downloadable change log. Your original file is never modified.

5. **📊 Creates quick visualizations**  
   Supports 11 chart types: bar, stacked bar, line, area, pie, donut, scatter, histogram, box plot, correlation heatmap, and missing-values chart. Explore both the original and cleaned data.

6. **🌓 Supports light and dark modes**  
   Works on desktop and mobile, with a toggle in the top-right corner to switch themes.

## 💡 What Makes It Different

- 🎯 **Impact, not just detection:** Each finding explains how the issue can affect your results.
- 🧠 **Understands expected blanks:** A cancelled ride may have no rating, and that is not necessarily an error. CheckKro identifies blanks that follow a rule in another column and rates them as low severity instead of raising a false alarm.
- 🚩 **Detects suspicious data patterns:** Flags rates that appear unusually high, such as a 42% refund rate.
- 🔒 **No silent changes:** The cleaner never guesses, and every modification is recorded.
- ⚙️ **Rule-based and explainable:** Uses plain Python checks rather than AI, making results repeatable and transparent.

## 🧮 How the Trust Score Works

The score starts at **100**. Each finding deducts points according to its severity:

| Severity | Points Deducted |
|---|---:|
| 🔴 High | 12 |
| 🟠 Medium | 5 |
| 🟢 Low | 1 |

**Verdict thresholds:**

- ✅ **Safe to analyze:** Score of 85 or above, with no high-severity findings.
- ⚠️ **Use with caution:** Score of 60 or above, unless the safe-to-analyze condition applies.
- ❌ **Do not use until fixed:** Score below 60.

The score is a heuristic, not a statistical probability. The **Score Explained** tab shows exactly how each result was calculated.

## 🧪 How Well Does It Work?

### ✅ Planted-Error Test

I planted 17 kinds of known errors, one at a time, across three datasets of different sizes, resulting in **51 tests**.

- 🎯 **51/51 errors detected**
- ✅ **0 serious false alarms on clean datasets**

These errors were deliberately introduced into synthetic data. This demonstrates that each check works as designed, not that the tool will achieve the same performance on every real-world dataset.

### 📂 Real-File Test

I tested CheckKro on a real dataset containing **103,024 ride bookings**.

The initial version scored it **0/100**, with nine high-severity alerts, most of which were incorrect:

- 🚫 Ratings and payment methods were blank for cancelled rides by design.
- 🔁 Customer IDs repeated because customers can book multiple times.
- 🚨 A column containing Excel `#NAME?` errors was the genuine issue, but it was under-reported.

I corrected all three issues and reran the planted-error tests to check for regressions.

**Final result:** The same dataset scored **72/100**, with one high-severity finding identifying the `#NAME?` column as a genuine data quality problem.

## ⚠️ Known Limitations

- 📈 **Outliers:** A simple statistical rule may flag naturally skewed data, such as booking values with a long tail, even when the values are valid.
- 🏷️ **Column names:** Some checks infer meaning from names such as `amount` or `age`, so English column names work best.
- 🎚️ **Thresholds:** Rules such as a refund rate above 25% are sensible defaults, not universal standards.
- 📝 **CSV parsing:** Pandas converts text such as `N/A`, `NA`, `null`, and `None` into missing values while reading a CSV. These appear as ordinary missing values. Placeholders such as `-`, `?`, `unknown`, and `#NAME?` remain text and can be detected separately.
- 📄 **File support:** Currently supports CSV files only.
- 🔐 **Privacy:** On the public demo, files are processed in memory for your session and are not saved by the app. However, avoid uploading confidential data to a public demo. For sensitive files, run CheckKro locally.

## 🚀 Run It Yourself

**1. Install dependencies**

```bash
pip install -r requirements.txt
```

**2. Launch the app**

```bash
streamlit run app.py
```

💡 Click **"Try with a sample messy file"** to explore the app without uploading your own data.

## 🗂️ Project Structure

| File | Purpose |
|---|---|
| `app.py` | 🖥️ Streamlit dashboard, tabs, and theme switching |
| `checks.py` | 🔍 Data quality checks and `run_checkup` |
| `scoring.py` | 🧮 Trust score and verdict calculation |
| `cleaner.py` | 🧹 Safe fixes and downloadable change log |
| `impact.py` | 📉 Plain-language impact explanations |
| `charts.py` | 📊 Eleven chart types |
| `datagen.py` | 🧪 Generation of clean and messy test data |
| `evaluate.py` | ✅ Error injection and detection evaluation |
| `BuildIt.ipynb` | 📓 Step-by-step development notebook |

## 🛠️ Built With

🐍 Python · 🐼 pandas · 🔢 NumPy · 🎈 Streamlit · 📊 Altair

## 👩‍💻 Author

**Disha Jaiswal**  
📊 Data Analyst | Building practical tools for trustworthy data analysis
