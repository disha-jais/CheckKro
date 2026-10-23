import base64
import html
import io
import os
from collections import Counter

import pandas as pd
import streamlit as st

import charts
import checks
import cleaner
import impact
import scoring
from datagen import make_messy

st.set_page_config(page_title="CheckKro", page_icon="✅", layout="wide")

# ---------- light / dark mode (the button in the top right corner) ----------
LIGHT = """
    color-scheme: light;
    --bg1: #EEF4F8; --bg2: #DDE9F4;
    --card: rgba(255,255,255,0.80); --card-solid: #FFFFFF; --card-line: rgba(255,255,255,0.95);
    --input-bg: #FFFFFF;
    --text: #0B1B3A; --body: #1F2A3C; --muted: #5B6B85;
    --accent: #0F9AA8; --accent-hover: #0B7F8B; --on-accent: #FFFFFF;
    --accent-soft: #DDF1F3; --accent-text: #0F7F8B;
    --track: #E6EEF9; --line: #D5E1F5; --shadow: rgba(40,80,160,0.09);
    --tab: rgba(255,255,255,0.65);
    --hi-fg: #B42318; --hi-bg: #FDECEA; --me-fg: #B45309; --me-bg: #FEF3E2; --lo-fg: #4B5B78; --lo-bg: #EAF0F8;
"""
DARK = """
    color-scheme: dark;
    --bg1: #050506; --bg2: #0A0C10;
    --card: rgba(15,16,19,0.92); --card-solid: #0F1013; --card-line: rgba(255,255,255,0.06);
    --input-bg: #14161B;
    --text: #F2F4F8; --body: #C9CFDA; --muted: #9AA1AD;
    --accent: #38BDF8; --accent-hover: #7DD3FC; --on-accent: #04202C;
    --accent-soft: #0B2230; --accent-text: #7DD3FC;
    --track: #1A1D23; --line: #22252B; --shadow: rgba(0,0,0,0.6);
    --tab: rgba(15,16,19,0.7);
    --hi-fg: #F0716B; --hi-bg: #2A1316; --me-fg: #F5B54A; --me-bg: #2A210E; --lo-fg: #9FB0CC; --lo-bg: #1A1D23;
"""


def flip_theme():
    st.session_state["theme"] = "dark" if st.session_state.get("theme", "light") == "light" else "light"


mode = st.session_state.get("theme", "light")
st.button("🌙" if mode == "light" else "☀️", key="theme_toggle", on_click=flip_theme,
          help="Switch between light and dark mode")
st.markdown(f"<style>:root {{{DARK if mode == 'dark' else LIGHT}}}</style>", unsafe_allow_html=True)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

.stApp, .stApp p, .stApp label, .stApp li, .stApp h1, .stApp h2, .stApp h3, .stApp h4,
.stApp button, .stApp input, .stApp textarea, .tagline, .verdict-card, .verdict-card div,
.panel, .panel div, .finding, .finding div, .finding span, .scorecard, .scorecard div,
[data-testid="stMetricValue"], [data-testid="stMetricLabel"] {
    font-family: 'Inter', -apple-system, 'Segoe UI', Roboto, sans-serif !important;
}

.stApp {background: linear-gradient(160deg, var(--bg1) 0%, var(--bg2) 100%);}
header[data-testid="stHeader"] {background: transparent;}
[data-testid="stToolbar"], [data-testid="stDecoration"], #MainMenu, footer {display: none !important;}
.block-container {padding-top: 2rem; max-width: 1150px;}

.stApp p, .stApp li {font-size: 0.95rem; line-height: 1.65; color: var(--body);}
.stApp h1, .stApp h2, .stApp h3 {font-weight: 600; letter-spacing: -0.01em; color: var(--text);}
.stApp [data-testid="stCaptionContainer"] p {color: var(--muted);}
.tagline {color: var(--muted); font-size: 1.05rem; margin: 0.3rem 0 1.4rem;}
.logo {width: 230px; display: block;}

[data-testid="stMetricLabel"] p {font-size: 0.78rem; font-weight: 500; letter-spacing: 0.06em;
                                 text-transform: uppercase; color: var(--muted);}
[data-testid="stMetricValue"] {font-size: 1.8rem; color: var(--text); font-weight: 700;}
[data-testid="stMetric"], .scorecard {
    background: var(--card); border: 1px solid var(--card-line);
    border-top: 3px solid var(--accent); border-radius: 18px; padding: 16px 20px;
    box-shadow: 0 6px 24px var(--shadow); min-height: 132px; box-sizing: border-box;
}
.scorecard .slabel {font-size: 0.78rem; font-weight: 500; letter-spacing: 0.06em; text-transform: uppercase;
                    color: var(--muted);}
.scorecard .svalue {font-size: 1.8rem; font-weight: 700; color: var(--text); line-height: 1.3;}
.sbar {position: relative; height: 10px; background: var(--track); border-radius: 99px; margin: 8px 0 7px;}
.sfill {height: 100%; border-radius: 99px;}
.scorecard .snote {font-size: 0.78rem; color: var(--muted); line-height: 1.35;}

.verdict-card {display: flex; justify-content: space-between; align-items: center; gap: 24px;
               border-radius: 18px; padding: 16px 24px; margin: 14px 0 18px; color: #FFFFFF;
               box-shadow: 0 8px 24px var(--shadow);}
.verdict-card .label {font-size: 0.72rem; letter-spacing: 0.1em; text-transform: uppercase; opacity: 0.85;}
.verdict-card .big {font-size: 1.35rem; font-weight: 800;}
.verdict-card .reason {text-align: left; max-width: 60%; font-size: 0.95rem;}
.verdict-card .reason b {font-weight: 800;}
.verdict-card .rhead {font-weight: 700; font-size: 1.02rem; margin-bottom: 4px;}
.verdict-card ul {margin: 0; padding-left: 1.1rem;}
.verdict-card ul li {color: #FFFFFF; font-size: 0.93rem; line-height: 1.5; margin: 2px 0;}
.verdict-card .rmore {opacity: 0.85; font-size: 0.85rem; margin-top: 4px;}

.panel {background: var(--card); border: 1px solid var(--card-line);
        border-radius: 18px; padding: 16px 20px; box-shadow: 0 6px 24px var(--shadow);
        margin-bottom: 14px;}
.ptitle {font-weight: 600; color: var(--text); margin-bottom: 8px;}
.brow {display: flex; align-items: center; gap: 10px; margin: 8px 0; font-size: 0.9rem; color: var(--body);}
.blabel {width: 140px; flex: none; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
         font-weight: 700; color: var(--text);}
.btrack {flex: 1; background: var(--track); border-radius: 99px; height: 9px;}
.bfill {height: 9px; border-radius: 99px;}
.bcount {width: 30px; text-align: right; color: var(--muted);}

.finding {background: var(--card); border: 1px solid var(--card-line);
          border-radius: 16px; padding: 14px 18px; margin: 12px 0 4px;
          box-shadow: 0 4px 18px var(--shadow);}
.fhead {display: flex; flex-wrap: wrap; align-items: center; gap: 10px; margin-bottom: 6px;}
.pill {font-size: 0.7rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
       padding: 3px 10px; border-radius: 99px;}
.pill-hi {color: var(--hi-fg); background: var(--hi-bg);}
.pill-me {color: var(--me-fg); background: var(--me-bg);}
.pill-lo {color: var(--lo-fg); background: var(--lo-bg);}
.ftitle {font-weight: 600; color: var(--text);}
.fcol {color: var(--text); font-weight: 700; font-family: ui-monospace, Menlo, monospace; font-size: 0.85rem;
       background: var(--accent-soft); padding: 2px 9px; border-radius: 7px;}
.faff {margin-left: auto; color: var(--muted); font-size: 0.88rem;}
.frow {font-size: 0.92rem; color: var(--body); margin: 3px 0;}
.frow b {color: var(--text); font-weight: 700;}

.tbl {overflow-x: auto; background: var(--card); border: 1px solid var(--card-line);
      border-radius: 16px; padding: 6px 12px; margin-bottom: 14px;}
.tbl table {border-collapse: collapse; width: 100%; font-size: 0.88rem;}
.tbl th {text-align: left; color: var(--muted); font-size: 0.72rem; text-transform: uppercase;
         letter-spacing: 0.06em; padding: 9px 10px; border-bottom: 1px solid var(--line); white-space: nowrap;}
.tbl td {padding: 8px 10px; border-bottom: 1px solid var(--line); color: var(--body);}
.tbl td.cn {font-weight: 700; color: var(--text);}

div[data-baseweb="tab-list"] {gap: 8px; background: transparent;}
button[data-baseweb="tab"] {background: var(--tab); border: 1px solid var(--line);
                            border-radius: 999px; padding: 6px 18px; height: auto;}
button[data-baseweb="tab"][aria-selected="true"] {background: var(--accent); border-color: var(--accent);}
button[data-baseweb="tab"][aria-selected="true"] p {color: var(--on-accent);}
div[data-baseweb="tab-highlight"], div[data-baseweb="tab-border"] {display: none;}

[data-testid="stExpander"] {background: var(--card); border: 1px solid var(--card-line);
                            border-radius: 14px; overflow: hidden;}
[data-testid="stExpander"] details {border: none;}
[data-testid="stExpander"] summary p {font-size: 0.9rem; font-weight: 500; color: var(--accent-text);}
[data-testid="stExpander"] summary svg {color: var(--accent-text);}

.stButton > button, .stDownloadButton > button {background: var(--accent); color: var(--on-accent); border: none;
                                                border-radius: 12px; padding: 0.55rem 1.3rem;}
.stButton > button p, .stDownloadButton > button p {color: var(--on-accent);}
.stButton > button:hover, .stDownloadButton > button:hover {background: var(--accent-hover);}

/* the light / dark button, fixed in the top right corner */
.st-key-theme_toggle {position: fixed; top: 0.9rem; right: 1.1rem; z-index: 1000000; width: auto !important;}
.st-key-theme_toggle button {width: 44px; height: 44px; min-height: 44px; padding: 0; border-radius: 50%;
                             background: var(--card-solid); border: 1px solid var(--line);
                             box-shadow: 0 6px 18px var(--shadow);}
.st-key-theme_toggle button p {color: var(--text); font-size: 1.15rem; line-height: 1; margin: 0;}
.st-key-theme_toggle button:hover {background: var(--accent-soft); border-color: var(--accent);}

/* Streamlit's own widgets, restyled so they follow the button and not the device */
[data-testid="stWidgetLabel"] p {color: var(--muted);}
[data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="textarea"], [data-baseweb="select"] > div {
    background: var(--input-bg) !important; border-color: var(--line) !important; color: var(--text) !important;
}
[data-baseweb="input"] input, [data-baseweb="select"] input, [data-baseweb="select"] div {color: var(--text) !important;}
[data-baseweb="select"] svg {fill: var(--muted) !important;}
[data-baseweb="popover"] > div, [data-baseweb="popover"] ul, [role="listbox"] {
    background: var(--card-solid) !important; color: var(--body) !important;
}
[data-baseweb="popover"] li, [role="option"] {color: var(--body) !important; background: transparent !important;}
[data-baseweb="popover"] li:hover, [role="option"]:hover, [role="option"][aria-selected="true"] {
    background: var(--accent-soft) !important;
}
[data-testid="stSliderTickBarMin"], [data-testid="stSliderTickBarMax"] {color: var(--muted);}
[data-testid="stThumbValue"] {color: var(--text);}
[data-testid="stSlider"] [role="slider"] {background-color: var(--accent) !important;}

[data-testid="stFileUploader"] section {background: var(--card); border: 1.5px dashed var(--accent);
                                        border-radius: 18px;}
[data-testid="stFileUploader"] small, [data-testid="stFileUploader"] section span,
[data-testid="stFileUploaderFile"] {color: var(--muted);}
[data-testid="stFileUploaderDropzone"] button {background: var(--accent); color: var(--on-accent); border: none;
                                               border-radius: 10px;}
[data-testid="stFileUploaderDropzone"] button p {color: var(--on-accent);}

[data-testid="stAlert"], [data-testid="stAlert"] > div {
    background: var(--card-solid) !important; border-radius: 14px; color: var(--body);
}
[data-testid="stAlert"] {border: 1px solid var(--line);}
[data-testid="stAlert"] p {color: var(--body) !important;}

/* ---------- mobile view ---------- */
@media (max-width: 640px) {
    .block-container {padding: 1rem 0.9rem 3rem;}
    .tagline {font-size: 0.95rem; margin-bottom: 1rem;}
    .logo {width: 180px;}

    [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) {flex-wrap: wrap; gap: 0.6rem;}
    [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) > [data-testid="stColumn"],
    [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) > [data-testid="column"] {
        flex: 1 1 calc(50% - 0.6rem) !important;
        min-width: calc(50% - 0.6rem) !important;
        width: calc(50% - 0.6rem) !important;
    }
    [data-testid="stMetric"], .scorecard {padding: 12px 14px; min-height: 0;}
    [data-testid="stMetricValue"] {font-size: 1.3rem;}
    .scorecard .svalue {font-size: 1.3rem;}

    .verdict-card {flex-direction: column; align-items: flex-start; gap: 8px; padding: 14px 18px;}
    .verdict-card .reason {text-align: left; max-width: 100%;}
    .verdict-card .big {font-size: 1.15rem;}

    .panel {padding: 14px 16px;}
    .blabel {width: 96px;}
    .finding {padding: 12px 14px;}
    .faff {margin-left: 0; width: 100%;}
    button[data-baseweb="tab"] {padding: 5px 12px;}
    .stButton > button, .stDownloadButton > button {width: 100%;}
    .st-key-theme_toggle button {width: 44px;}
}
</style>
""", unsafe_allow_html=True)

TITLES = {
    "missing_values": "Missing values",
    "structural_missing": "Blank by design",
    "disguised_missing": "Placeholder values (like N/A)",
    "exact_duplicates": "Duplicate rows",
    "duplicate_ids": "Repeated IDs",
    "extra_whitespace": "Extra spaces",
    "inconsistent_case": "Inconsistent spelling or case",
    "numeric_as_text": "Numbers stored as text",
    "mixed_types": "Text mixed into numbers",
    "impossible_values": "Impossible values",
    "extreme_outliers": "Extreme outliers",
    "future_dates": "Dates in the future",
    "date_order": "Dates in the wrong order",
    "suspicious_rate": "Suspiciously high rate",
    "constant_column": "Column never changes",
    "all_unique_column": "Every value is unique",
    "messy_column_name": "Messy column name",
    "date_gaps": "Missing days in the data",
    "rare_categories": "Rare values (possible typos)",
}
SEV = {"high": ("hi", "High"), "medium": ("me", "Medium"), "low": ("lo", "Low")}
VERDICT_STYLE = {
    "SAFE TO ANALYZE": "linear-gradient(135deg, #27B5A5, #0F8F97)",
    "USE WITH CAUTION": "linear-gradient(135deg, #F5B54A, #E08A1E)",
    "DO NOT USE UNTIL FIXED": "linear-gradient(135deg, #F0716B, #D6453F)",
}
BAR = {"SAFE TO ANALYZE": "#22B07D", "USE WITH CAUTION": "#E08A1E", "DO NOT USE UNTIL FIXED": "#D6453F"}


def esc(x):
    return html.escape(str(x))


def bold_cols(text, columns):
    """Escape text and make any 'column name' in quotes bold."""
    out = html.escape(str(text))
    for c in sorted(map(str, columns), key=len, reverse=True):
        out = out.replace(html.escape(f"'{c}'"), f"<b>{html.escape(c)}</b>")
    return out


def table_html(frame):
    """A simple styled table where the 'column' column is bold."""
    head = "".join(f"<th>{esc(c)}</th>" for c in frame.columns)
    body = ""
    for _, row in frame.iterrows():
        cells = "".join(
            f'<td class="cn">{esc(v)}</td>' if c == "column" else f"<td>{esc(v)}</td>"
            for c, v in zip(frame.columns, row.values))
        body += f"<tr>{cells}</tr>"
    return f'<div class="tbl"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def title_of(check):
    return TITLES.get(check, check.replace("_", " ").capitalize())


def plain(f):
    """One easy sentence about a finding, with the column and the key words in bold."""
    col = f"<b>{esc(f.column)}</b>"
    pct = f"{f.pct:g}%"
    sentences = {
        "missing_values": f"{col} information is <b>missing</b> in {pct} of rows",
        "structural_missing": f"{col} is <b>blank by design</b> in some rows",
        "disguised_missing": f"{col} has <b>placeholder values</b> (like N/A) in {pct} of rows",
        "exact_duplicates": f"<b>{f.count:,} duplicate rows</b> were found",
        "duplicate_ids": f"{col} has <b>repeated IDs</b>",
        "extra_whitespace": f"{col} has <b>extra spaces</b> in some values",
        "inconsistent_case": f"{col} is <b>spelled inconsistently</b> in some rows",
        "numeric_as_text": f"{col} holds numbers saved as <b>text</b>",
        "mixed_types": f"{col} has <b>text mixed into numbers</b>",
        "impossible_values": f"{col} has <b>impossible values</b> in {pct} of rows",
        "extreme_outliers": f"{col} has <b>extreme outliers</b>",
        "future_dates": f"{col} has <b>dates in the future</b>",
        "date_order": f"{col} has <b>dates in the wrong order</b>",
        "suspicious_rate": f"{col} has a <b>suspiciously high rate</b> ({pct})",
        "constant_column": f"{col} <b>never changes</b>",
        "all_unique_column": f"{col} has <b>no repeated values</b>",
        "messy_column_name": f"{col} has a <b>messy column name</b>",
        "date_gaps": f"{col} has <b>missing days</b>",
        "rare_categories": f"{col} has <b>rare values</b> (possible typos)",
    }
    return sentences.get(f.check, f"<b>{esc(title_of(f.check))}</b> in {col}")


def affected(f):
    return f"{f.count:,} rows ({f.pct}%)" if f.count else "Column-level issue"


def bars(rows, colors):
    """rows: list of (label, value, color). Draws simple horizontal bars."""
    top = max([v for _, v, _ in rows] + [1])
    out = ""
    for label, value, color in rows:
        out += (f'<div class="brow"><div class="blabel">{esc(label)}</div>'
                f'<div class="btrack"><div class="bfill" style="width:{value / top * 100:.0f}%;background:{color};"></div></div>'
                f'<div class="bcount">{value}</div></div>')
    return out


def load_csv(file):
    raw = file.getvalue()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return pd.read_csv(io.BytesIO(raw), encoding=enc), enc
        except UnicodeDecodeError:
            continue
    raise ValueError("unreadable")


@st.cache_resource
def logo_html(theme):
    """The logo with dark letters for light mode, and light letters for dark mode."""
    def encode(path):
        with open(path, "rb") as fh:
            return base64.b64encode(fh.read()).decode()
    if not os.path.exists("logo_clean.png"):
        return "<h1>CheckKro</h1>"
    path = "logo_dark.png" if theme == "dark" and os.path.exists("logo_dark.png") else "logo_clean.png"
    return f'<img class="logo" src="data:image/png;base64,{encode(path)}" alt="CheckKro">'


@st.cache_data(show_spinner="Checking your file...")
def analyse(df):
    findings = checks.run_checkup(df)
    cleaned, log = cleaner.clean(df)
    after = checks.run_checkup(cleaned)
    return findings, cleaned, log, after


# ---------- header and upload ----------
st.markdown(logo_html(mode), unsafe_allow_html=True)
st.markdown('<div class="tagline">Know if your data is safe to analyze.</div>', unsafe_allow_html=True)

uploaded = st.file_uploader("Upload a CSV file", type="csv")
if uploaded is None:
    if st.button("Try with a sample messy file"):
        st.session_state["sample"] = True
else:
    st.session_state["sample"] = False

df = None
if uploaded is not None:
    try:
        df, enc = load_csv(uploaded)
    except Exception:
        st.error("This file could not be read as a CSV. Check that it is a plain CSV export and try again.")
        st.stop()
    if enc != "utf-8-sig":
        st.info(f"This file is not UTF-8, so it was read as {enc}. Special characters may look different.")
elif st.session_state.get("sample"):
    df = make_messy()
    st.info("Showing the built-in sample file.")

if df is None:
    st.stop()
if df.shape[0] == 0 or df.shape[1] == 0:
    st.warning("This file has no rows to check. Upload a file that contains data.")
    st.stop()

findings, cleaned, log, after = analyse(df)
score = scoring.trust_score(findings)
verdict = scoring.verdict(score, findings)
n_sev = {s: sum(f.severity == s for f in findings) for s in ("high", "medium", "low")}
n_high = n_sev["high"]
affected_cols = Counter(f.column for f in findings if f.column != "(all columns)")

# ---------- dashboard: metrics (the trust score bar is coloured by the result) ----------
bar = BAR[verdict]
if score >= 85 and n_high > 0:
    bar_note = "High score, but a serious issue blocks 'safe'"
elif verdict == "SAFE TO ANALYZE":
    bar_note = "Safe to analyze (85 and above)"
elif verdict == "USE WITH CAUTION":
    bar_note = "Use with caution (60 to 84)"
else:
    bar_note = "Do not use until fixed (below 60)"
c1, c2, c3, c4 = st.columns(4)
c1.markdown(
    f'<div class="scorecard" style="border-top-color:{bar};"><div class="slabel">Trust score</div>'
    f'<div class="svalue">{score} / 100</div>'
    f'<div class="sbar"><div class="sfill" style="width:{max(0, min(score, 100))}%;background:{bar};"></div></div>'
    f'<div class="snote">{bar_note}</div></div>',
    unsafe_allow_html=True,
)
c2.metric("Problems found", len(findings))
c3.metric("Columns affected", len(affected_cols))
c4.metric("Rows x columns", f"{len(df):,} x {df.shape[1]}")

# ---------- verdict card, explained in plain words ----------
serious = [f for f in findings if f.severity == "high"]
worth_a_look = [f for f in findings if f.severity == "medium"]
if not findings:
    reason = '<div class="rhead">No problems found.</div>'
else:
    if serious:
        head = "1 issue needs your attention" if len(serious) == 1 else f"{len(serious)} issues need your attention"
        shown_items, rest = serious[:4], len(serious) - 4
    elif worth_a_look:
        head = "No serious issues. Worth a look:"
        shown_items, rest = worth_a_look[:3], len(worth_a_look) - 3
    else:
        head, shown_items, rest = "No serious issues. Only minor notes.", [], 0
    reason = f'<div class="rhead">{esc(head)}</div>'
    if shown_items:
        reason += "<ul>" + "".join(f"<li>{plain(f)}</li>" for f in shown_items) + "</ul>"
    if rest > 0:
        reason += f'<div class="rmore">and {rest} more in the Findings tab</div>'
st.markdown(
    f'<div class="verdict-card" style="background:{VERDICT_STYLE[verdict]};">'
    f'<div><div class="label">Verdict</div><div class="big">{esc(verdict)}</div></div>'
    f'<div class="reason">{reason}</div></div>',
    unsafe_allow_html=True,
)

# ---------- dashboard: breakdown panels ----------
left, right = st.columns(2)
with left:
    rows = [("High", n_sev["high"], "#D6453F"), ("Medium", n_sev["medium"], "#E08A1E"),
            ("Low", n_sev["low"], "#8CA0BF")]
    st.markdown(f'<div class="panel"><div class="ptitle">Findings by severity</div>{bars(rows, None)}</div>',
                unsafe_allow_html=True)
with right:
    top_cols = [(c, n, "var(--accent)") for c, n in affected_cols.most_common(5)]
    body = bars(top_cols, None) if top_cols else '<div class="frow">No column has problems.</div>'
    st.markdown(f'<div class="panel"><div class="ptitle">Columns needing attention</div>{body}</div>',
                unsafe_allow_html=True)

tab_findings, tab_score, tab_overview, tab_charts, tab_clean = st.tabs(
    ["Findings", "Score explained", "Overview", "Charts", "Clean the file"])

# ---------- findings ----------
with tab_findings:
    show = st.radio("Show", ["All", "High", "Medium", "Low"], horizontal=True, label_visibility="collapsed")
    shown = [f for f in findings if show == "All" or f.severity == show.lower()]
    if not findings:
        st.success("No problems found.")
    elif not shown:
        st.info("No findings at this severity.")
    for f in shown:
        css, label = SEV[f.severity]
        st.markdown(
            f'<div class="finding"><div class="fhead">'
            f'<span class="pill pill-{css}">{label}</span>'
            f'<span class="ftitle">{esc(title_of(f.check))}</span>'
            f'<span class="fcol">{esc(f.column)}</span>'
            f'<span class="faff">{esc(affected(f))}</span></div>'
            f'<div class="frow"><b>Why it matters:</b> {bold_cols(f.why, df.columns)}</div>'
            f'<div class="frow"><b>Suggested action:</b> {bold_cols(f.suggestion, df.columns)}</div></div>',
            unsafe_allow_html=True,
        )
        with st.expander("Details and impact on your numbers"):
            st.markdown(f'<div class="frow">{bold_cols(f.detail, df.columns)}</div>', unsafe_allow_html=True)
            effect = impact.impact(df, f)
            if effect:
                st.markdown(f'<div class="frow"><b>Impact on your numbers:</b> {bold_cols(effect, df.columns)}</div>',
                            unsafe_allow_html=True)

# ---------- score explained ----------
with tab_score:
    pen = scoring.PENALTY
    st.markdown("**How the score is calculated.** The score starts at 100. Every finding takes points off, "
                "depending on its severity:")
    for s in ("high", "medium", "low"):
        st.markdown(f"- {n_sev[s]} {s} finding(s) x {pen[s]} points = **-{n_sev[s] * pen[s]}**")
    st.markdown(f"Result: **{score} / 100**.")
    costly = sorted(findings, key=lambda f: -pen[f.severity])[:5]
    if costly:
        st.markdown("**What lowers it most:**")
        for f in costly:
            st.markdown(f"- -{pen[f.severity]}: {title_of(f.check)} in **{f.column}**")
    st.markdown("**What the verdict means:**")
    st.markdown("- **Safe to analyze:** score of 85 or more, and no high-severity findings.\n"
                "- **Use with caution:** score of 60 or more.\n"
                "- **Do not use until fixed:** anything below 60.")
    st.caption("The score is a simple rule-based heuristic: fixed penalties by severity. It is not a statistical "
               "probability and does not guarantee that the data is right or wrong. One high-severity finding "
               "always blocks 'safe to analyze'.")

# ---------- overview ----------
with tab_overview:
    ov = checks.overview(df)
    ov["example"] = ov["example"].astype(str)
    st.subheader("Columns")
    st.markdown(table_html(ov), unsafe_allow_html=True)
    cov = checks.date_coverage(df)
    if len(cov) > 0:
        st.subheader("Date coverage")
        st.markdown(table_html(cov), unsafe_allow_html=True)

# ---------- charts ----------
with tab_charts:
    charts.TEAL = "#38BDF8" if mode == "dark" else "#0F9AA8"
    charts.render_charts(df, cleaned)

# ---------- clean ----------
with tab_clean:
    st.write("Only safe fixes are applied: trimming spaces, turning placeholders like 'N/A' "
             "into real blanks, and removing exact duplicate rows. Everything else needs your decision. "
             "Your original file is never changed.")
    placeholders = int(log.loc[log["action"].str.startswith("placeholder"), "rows_affected"].sum()) if len(log) else 0
    after_score = scoring.trust_score(after)
    m1, m2, m3 = st.columns(3)
    m1.metric("Rows", f"{len(df):,} -> {len(cleaned):,}")
    m2.metric("Placeholders turned blank", f"{placeholders:,}")
    m3.metric("Score after safe fixes", f"{after_score} / 100", delta=after_score - score)
    if len(log) == 0:
        st.info("Nothing needed the safe fixes.")
    else:
        st.subheader("Change log")
        st.markdown(table_html(log), unsafe_allow_html=True)
    st.subheader("Preview of the cleaned data")
    preview = cleaned.head(50).astype(object).where(lambda x: x.notna(), "")
    st.markdown(table_html(preview), unsafe_allow_html=True)
    d1, d2 = st.columns(2)
    d1.download_button("Download cleaned CSV", cleaned.to_csv(index=False).encode("utf-8"),
                       file_name="cleaned.csv", mime="text/csv")
    d2.download_button("Download change log (CSV)", log.to_csv(index=False).encode("utf-8"),
                       file_name="change_log.csv", mime="text/csv")

st.caption("CheckKro uses rule-based checks. Nothing in your file is changed without a logged record.")
