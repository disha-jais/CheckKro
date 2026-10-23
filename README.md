# CheckKro

**Know if your data is safe to analyze.**

CheckKro checks any CSV file the way an analyst would on first opening it, and answers one question: can I trust this data? It gives a trust score out of 100, a plain-language verdict, and what each problem does to your numbers.

Live demo: (add the link after deploying)
Code: (add the GitHub link)

## Screenshots

(Add two or three images here after deploying: the verdict card, the Findings tab and the Charts tab, in light and dark mode.)

## What it does

1. **Checks** the file for the problems analysts look for first. There are 19 kinds: missing and hidden-missing values, duplicate rows and IDs, formatting mistakes, impossible values, extreme outliers, date errors, suspicious rates, and more.
2. **Gives a verdict in plain words.** A trust score with a bar that changes color (green, amber or red), and a verdict card such as "1 issue needs your attention: Vehicle Images has placeholder values in 100% of rows".
3. **Explains the impact on your numbers.** Not just "150 duplicate rows", but "total order amount is overstated by 3.1%".
4. **Cleans safely.** It only trims spaces, turns placeholders like "N/A" and "#NAME?" into real blanks, and removes exact duplicates. Every change is in a change log you can download. Your original file is never changed.
5. **Draws quick charts.** Eleven types: bar, stacked bar, line, area, pie, donut, scatter, histogram, box plot, correlation heatmap and a missing-values chart, on the original or the cleaned data.

It works on desktop and phone, in light or dark mode (a button in the top right corner switches them).

## What makes it different

- **Impact, not just detection.** Each finding says what it does to your results.
- **It understands blanks that are by design.** A cancelled ride has no rating, and that is not an error. CheckKro spots blanks that follow a rule in another column and rates them low instead of raising an alarm.
- **Suspicious-data detection.** It flags rates that look too high to be real, such as a 42% refund rate.
- **No silent changes.** The cleaner never guesses, and every change is logged.
- **Rule-based, not AI.** The checks are plain Python, so every result is repeatable and explainable.

## How the trust score works

The score starts at 100. Each finding takes points off by severity: 12 for high, 5 for medium and 1 for low. The verdict is "safe to analyze" at 85 or above with no high-severity finding, "use with caution" at 60 or above, and "do not use until fixed" below that.

The score is a simple heuristic, not a statistical probability. The "Score explained" tab in the app shows exactly how each result was reached.

## How well does it work?

**Planted-error test.** I planted 17 kinds of known error, one at a time, in 3 datasets of different sizes (51 tests in total). CheckKro caught 51 of 51, with 0 serious false alarms on the clean datasets. These errors were written by me on synthetic data, so this shows each check does what it was built to do, not how it performs on every real file.

**Real-file test.** I then ran it on a real dataset of 103,024 ride bookings. The first version scored it 0 out of 100 with 9 high-severity alarms, and most of them were wrong:
- Columns such as ratings and payment method are blank for cancelled rides. That is by design.
- Customer ID repeats because customers book more than once.
- A column full of Excel `#NAME?` errors was the one real problem, and it was under-reported.

I fixed all three, and re-ran the planted-error test to confirm nothing broke. The same file now scores 72 out of 100 with one high-severity finding: the `#NAME?` column, which is a real problem.

## Known limits

- Outliers are found with a simple statistical rule, so naturally skewed data (such as booking values with a long tail) can be flagged even when the values are real.
- Some checks use column names to decide what a column means (for example "amount" or "age"), so they work best with English column names.
- The thresholds, such as a refund rate above 25%, are sensible defaults, not universal truths.
- Pandas turns text like `N/A`, `NA`, `null` and `None` into real blanks while reading a file, so those appear as plain missing values. Placeholders such as `-`, `?`, `unknown` and `#NAME?` stay as text and are caught as placeholders.
- It reads CSV files only.
- On the public demo, your file is processed in memory for your session and is not saved by the app. Still, do not upload confidential data to it. You can run it locally instead.

## Run it yourself

    pip install -r requirements.txt
    streamlit run app.py

Click "Try with a sample messy file" to see it work without uploading anything.

## Files

- `app.py` is the Streamlit app: the dashboard, tabs, light and dark mode.
- `checks.py` holds all the checks and the `run_checkup` function.
- `scoring.py` turns findings into a trust score and a verdict.
- `cleaner.py` applies the safe fixes and writes the change log.
- `impact.py` writes the plain-language impact of each finding.
- `charts.py` builds the eleven chart types.
- `datagen.py` builds the clean and messy test data.
- `evaluate.py` plants errors and measures how many are caught.
- `BuildIt.ipynb` is the notebook the project was built in, step by step.

## Built with

Python, pandas, NumPy, Streamlit and Altair.

## Author

Disha Jaiswal, data analyst.
