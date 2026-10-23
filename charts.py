import altair as alt
import numpy as np
import pandas as pd

import checks

alt.data_transformers.disable_max_rows()

TEAL = "#0F9AA8"
NEUTRAL = "#7A879E"   # reads on both light and dark backgrounds
WARM = "#E08A1E"
RED = "#E0584F"
COUNT = "(count of rows)"
PERIOD = {"Day": "D", "Week": "W", "Month": "M"}
KINDS = ["Bar", "Stacked bar", "Line", "Area", "Pie", "Donut", "Scatter", "Histogram",
         "Box plot", "Correlation heatmap", "Missing values"]


def palette():
    return [TEAL, "#38BDF8", "#6366F1", "#F59E0B", "#EC4899", "#10B981", "#94A3B8", "#A78BFA"]


def is_num(s):
    return pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s)


def prepare(raw):
    """Chart-ready copy of the data. Text columns that are mostly numbers are read as numbers.
    Returns (data, converted, numeric, dates, why_not)."""
    data = raw.copy()
    dates = checks.date_columns(raw)
    converted, why_not = [], {}
    for c in raw.columns:
        s = raw[c]
        if c in dates:
            why_not[c] = "date"
        elif is_num(s):
            continue
        elif pd.api.types.is_bool_dtype(s):
            why_not[c] = "yes/no"
        elif checks.is_text(s):
            txt = s.astype(str).str.strip().str.replace(",", "", regex=False)
            num = pd.to_numeric(txt, errors="coerce")
            if s.notna().any() and num[s.notna()].notna().mean() >= 0.8:
                data[c] = num
                converted.append(c)
            else:
                why_not[c] = "text"
        else:
            why_not[c] = "other"
    numeric = [c for c in data.columns if is_num(data[c])]
    return data, converted, numeric, dates, why_not


def style(chart, title, height=340):
    return (chart.properties(title=title, height=height, background="transparent")
            .configure_axis(labelColor=NEUTRAL, titleColor=NEUTRAL, gridColor="rgba(128,128,128,0.22)",
                            domainColor="rgba(128,128,128,0.4)", labelFontSize=12, titleFontSize=12)
            .configure_legend(labelColor=NEUTRAL, titleColor=NEUTRAL, labelFontSize=12)
            .configure_title(color=NEUTRAL, fontSize=15, fontWeight=600, anchor="start")
            .configure_view(stroke=None))


def ylabel_of(y, agg):
    return "Number of rows" if y == COUNT else f"{agg} of {y}"


def auto_title(kind, x=None, y=None, agg="sum", split=None):
    if kind in ("Bar", "Line", "Area", "Pie", "Donut"):
        return f"{ylabel_of(y, agg)} by {x}"
    if kind == "Stacked bar":
        return f"{ylabel_of(y, agg)} by {x}, split by {split}"
    if kind == "Scatter":
        return f"{y} vs {x}"
    if kind == "Histogram":
        return f"Distribution of {x}"
    if kind == "Box plot":
        return f"Spread of {y}" + (f" by {x}" if x else "")
    if kind == "Correlation heatmap":
        return "How the number columns move together"
    return "Missing values by column"


def _period_labels(series, freq):
    return series.dt.to_period(PERIOD[freq]).dt.to_timestamp()


def _group(df, label, y, agg):
    if y == COUNT:
        return pd.DataFrame({"label": label}).dropna().groupby("label").size().reset_index(name="value")
    return (pd.DataFrame({"label": label, "v": df[y]}).dropna()
            .groupby("label")["v"].agg(agg).reset_index(name="value"))


def _bar_line_area(df, kind, x, y, agg, top_n, freq, dates, title, sort_by, labels):
    is_date = x in dates
    if is_date:
        label = _period_labels(dates[x], freq)
    else:
        label = df[x] if is_num(df[x]) else df[x].astype(str)
    g = _group(df, label, y, agg)
    ylabel = ylabel_of(y, agg)
    if g.empty:
        return None, None, "There is nothing to plot for this selection."
    if kind == "Bar" and not is_date:
        g = g.sort_values("value", ascending=False).head(top_n)
        g["label"] = g["label"].astype(str)
        if sort_by == "Smallest first":
            g = g.sort_values("value")
        elif sort_by == "A to Z":
            g = g.sort_values("label")
    else:
        g = g.sort_values("label")
    if is_date:
        xenc = alt.X("label:T", title=x)
    elif kind in ("Line", "Area") and is_num(g["label"]):
        xenc = alt.X("label:Q", title=x)
    else:
        xenc = alt.X("label:N", sort=None, title=x)
    base = alt.Chart(g)
    if kind == "Bar":
        mark = base.mark_bar(color=TEAL, cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
    elif kind == "Area":
        mark = base.mark_area(color=TEAL, opacity=0.35, line={"color": TEAL})
    else:
        mark = base.mark_line(color=TEAL, strokeWidth=2.5, point=alt.OverlayMarkDef(color=TEAL))
    chart = mark.encode(x=xenc, y=alt.Y("value:Q", title=ylabel),
                        tooltip=[alt.Tooltip("label", title=x), alt.Tooltip("value:Q", title=ylabel, format=",.2f")])
    if labels and len(g) <= 25:
        whole = bool((g["value"] % 1 == 0).all())
        text = base.mark_text(dy=-9, fontSize=11, fontWeight="bold", color=NEUTRAL).encode(
            x=xenc, y=alt.Y("value:Q", title=ylabel),
            text=alt.Text("value:Q", format=",.0f" if whole else ",.1f"))
        chart = chart + text
    note = f"Showing the top {top_n} values." if kind == "Bar" and not is_date and len(g) == top_n else None
    return (style(chart, title or auto_title(kind, x, y, agg)),
            g.rename(columns={"label": x, "value": ylabel}), note)


def _stacked(df, x, split, y, agg, top_n, freq, dates, title, pct):
    if x == split:
        return None, None, "Pick two different columns."
    label = (_period_labels(dates[x], freq).dt.strftime("%Y-%m-%d") if x in dates else df[x].astype(str))
    part = df[split].astype(str)
    keep = part.value_counts().head(7).index
    part = part.where(part.isin(keep), "Other")
    ylabel = ylabel_of(y, agg)
    frame = pd.DataFrame({"label": label, "split": part})
    if y == COUNT:
        g = frame.dropna().groupby(["label", "split"]).size().reset_index(name="value")
    else:
        frame["v"] = df[y]
        g = frame.dropna().groupby(["label", "split"])["v"].agg(agg).reset_index(name="value")
    if g.empty:
        return None, None, "There is nothing to plot for this selection."
    totals = g.groupby("label")["value"].sum().sort_values(ascending=False)
    order = [str(v) for v in (totals.index if x in dates else totals.head(top_n).index)]
    if x in dates:
        order = sorted(order)
    g = g[g["label"].isin(order)]
    chart = (alt.Chart(g).mark_bar()
             .encode(x=alt.X("label:N", sort=order, title=x),
                     y=alt.Y("value:Q", stack="normalize" if pct else "zero", title="Share of each bar" if pct else ylabel,
                             axis=alt.Axis(format="%") if pct else alt.Axis()),
                     color=alt.Color("split:N", scale=alt.Scale(range=palette()), legend=alt.Legend(title=split)),
                     tooltip=[alt.Tooltip("label", title=x), alt.Tooltip("split", title=split),
                              alt.Tooltip("value:Q", title=ylabel, format=",.2f")]))
    notes = []
    if x not in dates and len(totals) > top_n:
        notes.append(f"Showing the top {top_n} groups.")
    if df[split].astype(str).nunique() > 7:
        notes.append(f"The 7 biggest values of '{split}' are shown, and the rest are grouped as Other.")
    note = " ".join(notes) or None
    return (style(chart, title or auto_title("Stacked bar", x, y, agg, split)),
            g.rename(columns={"label": x, "split": split, "value": ylabel}), note)


def _pie(df, kind, x, y, agg, top_n, title):
    g = _group(df, df[x].astype(str), y, agg)
    if g.empty:
        return None, None, "There is nothing to plot for this selection."
    if (g["value"] < 0).any():
        return None, None, "Pie charts need values that are zero or above. Pick another column or use a bar chart."
    g = g.sort_values("value", ascending=False)
    additive = (y == COUNT or agg == "sum")
    note = None
    top = g.head(top_n)
    if len(g) > top_n:
        if additive:
            top = pd.concat([top, pd.DataFrame({"label": ["Other"], "value": [g.iloc[top_n:]["value"].sum()]})])
            note = f"Showing the top {top_n} slices; the rest are grouped as Other."
        else:
            note = f"Showing the top {top_n} slices only."
    total = top["value"].sum()
    if total <= 0:
        return None, None, "All values are zero, so there is nothing to draw."
    top = top.assign(share=top["value"] / total * 100)
    top["legend"] = top.apply(lambda r: f"{r['label']} ({r['share']:.1f}%)", axis=1)
    order = list(top["legend"])
    ylabel = ylabel_of(y, agg)
    chart = (alt.Chart(top).mark_arc(innerRadius=70 if kind == "Donut" else 0, outerRadius=140)
             .encode(theta=alt.Theta("value:Q", stack=True),
                     color=alt.Color("legend:N", sort=order, scale=alt.Scale(range=palette()),
                                     legend=alt.Legend(title=x)),
                     tooltip=[alt.Tooltip("label", title=x), alt.Tooltip("value:Q", title=ylabel, format=",.2f"),
                              alt.Tooltip("share:Q", title="Share (%)", format=".1f")]))
    return (style(chart, title or auto_title(kind, x, y, agg)),
            top[["label", "value", "share"]].rename(columns={"label": x, "value": ylabel, "share": "share_%"}), note)


def _scatter(df, x, y, title):
    if x == y:
        return None, None, "Pick two different columns."
    d = df[[x, y]].dropna().rename(columns={x: "x", y: "y"})
    if d.empty:
        return None, None, "There is nothing to plot for this selection."
    note = None
    if len(d) > 3000:
        note = f"Showing a random sample of 3,000 points out of {len(d):,}."
        d = d.sample(3000, random_state=0)
    chart = (alt.Chart(d).mark_circle(size=45, opacity=0.45, color=TEAL)
             .encode(x=alt.X("x:Q", title=x), y=alt.Y("y:Q", title=y),
                     tooltip=[alt.Tooltip("x:Q", title=x), alt.Tooltip("y:Q", title=y)]))
    return style(chart, title or auto_title("Scatter", x, y)), d.rename(columns={"x": x, "y": y}), note


def _hist(df, x, bins, title):
    s = pd.to_numeric(df[x], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if s.empty:
        return None, None, "There are no numbers to plot in this column."
    counts, edges = np.histogram(s, bins=bins)
    h = pd.DataFrame({"start": edges[:-1], "end": edges[1:], "count": counts})
    chart = (alt.Chart(h).mark_bar(color=TEAL, opacity=0.9)
             .encode(x=alt.X("start:Q", title=x), x2="end:Q", y=alt.Y("count:Q", title="Number of rows"),
                     tooltip=[alt.Tooltip("start:Q", title="From", format=",.2f"),
                              alt.Tooltip("end:Q", title="To", format=",.2f"),
                              alt.Tooltip("count:Q", title="Rows")]))
    return style(chart, title or auto_title("Histogram", x)), h, None


def _box(df, y, group, title):
    vals = pd.to_numeric(df[y], errors="coerce").replace([np.inf, -np.inf], np.nan)
    if group:
        keys = df[group].astype(str)
        top = keys.value_counts().head(8).index
        parts = {k: vals[(keys == k)].dropna() for k in top}
    else:
        parts = {"All rows": vals.dropna()}
    stats, outs = [], []
    for name, v in parts.items():
        if len(v) == 0:
            continue
        q1, med, q3 = np.percentile(v, [25, 50, 75])
        iqr = q3 - q1
        lo_f, hi_f = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        inside = v[(v >= lo_f) & (v <= hi_f)]
        low = inside.min() if len(inside) else q1
        high = inside.max() if len(inside) else q3
        out = v[(v < lo_f) | (v > hi_f)]
        stats.append({"group": name, "low": low, "q1": q1, "median": med, "q3": q3, "high": high,
                      "rows": len(v), "outliers": len(out)})
        outs.append(pd.DataFrame({"group": name, "value": out.head(200).values}))
    if not stats:
        return None, None, "There are no numbers to plot in this column."
    st_df = pd.DataFrame(stats)
    xenc = alt.X("group:N", sort=list(st_df["group"]), title=group or None)
    rule = alt.Chart(st_df).mark_rule(color=NEUTRAL).encode(x=xenc, y=alt.Y("low:Q", title=y), y2="high:Q")
    box = (alt.Chart(st_df).mark_bar(color=TEAL, size=44, opacity=0.9)
           .encode(x=xenc, y="q1:Q", y2="q3:Q",
                   tooltip=[alt.Tooltip("group", title="Group"), alt.Tooltip("median:Q", format=",.2f"),
                            alt.Tooltip("q1:Q", title="25th percentile", format=",.2f"),
                            alt.Tooltip("q3:Q", title="75th percentile", format=",.2f"),
                            alt.Tooltip("rows:Q", title="Rows"), alt.Tooltip("outliers:Q", title="Outliers")]))
    med = alt.Chart(st_df).mark_tick(color="white", size=44, thickness=2).encode(x=xenc, y="median:Q")
    chart = rule + box + med
    out_df = pd.concat(outs, ignore_index=True)
    note = None
    if len(out_df):
        pts = alt.Chart(out_df).mark_circle(color=WARM, size=35, opacity=0.7).encode(
            x=alt.X("group:N", sort=list(st_df["group"])), y="value:Q",
            tooltip=[alt.Tooltip("value:Q", title="Outlier", format=",.2f")])
        chart = chart + pts
        note = "Orange dots are outliers (more than 1.5 times the middle spread beyond the box). Up to 200 are drawn per group."
    return style(chart, title or auto_title("Box plot", group, y)), st_df, note


def _heatmap(df, numeric, title):
    cols = [c for c in numeric if df[c].nunique() > 1][:15]
    if len(cols) < 2:
        return None, None, "A heatmap needs at least two number columns that are not constant."
    corr = df[cols].corr(numeric_only=True)
    long = corr.stack().reset_index()
    long.columns = ["x", "y", "value"]
    long = long.dropna()
    long["value"] = long["value"].round(2)
    long["strong"] = long["value"].abs() > 0.6
    xenc = alt.X("x:N", sort=cols, title=None, axis=alt.Axis(labelAngle=-45))
    yenc = alt.Y("y:N", sort=cols, title=None)
    rect = (alt.Chart(long).mark_rect()
            .encode(x=xenc, y=yenc,
                    color=alt.Color("value:Q", scale=alt.Scale(domain=[-1, 0, 1], range=[RED, "#CBD5E1", TEAL]),
                                    legend=alt.Legend(title="Correlation")),
                    tooltip=[alt.Tooltip("x", title="Column"), alt.Tooltip("y", title="Compared with"),
                             alt.Tooltip("value:Q", title="Correlation", format=".2f")]))
    text = (alt.Chart(long).mark_text(fontSize=11)
            .encode(x=xenc, y=yenc, text=alt.Text("value:Q", format=".2f"),
                    color=alt.condition("datum.strong", alt.value("white"), alt.value("#0B1B3A"))))
    note = "Correlation shows how two columns move together, from -1 to 1. It does not mean one causes the other."
    if len([c for c in numeric if df[c].nunique() > 1]) > 15:
        note = "Showing the first 15 number columns. " + note
    return style(rect + text, title or auto_title("Correlation heatmap"), height=420), corr.reset_index(), note


def _missing(df, title):
    ov = checks.overview(df)
    d = (ov[ov["missing_%"] > 0][["column", "missing_%"]]
         .sort_values("missing_%", ascending=False).head(25).rename(columns={"missing_%": "pct"}))
    if d.empty:
        return None, None, "No missing values found in this file."
    bars = (alt.Chart(d).mark_bar(cornerRadiusEnd=4)
            .encode(y=alt.Y("column:N", sort="-x", title=None), x=alt.X("pct:Q", title="% of rows missing"),
                    color=alt.condition("datum.pct > 20", alt.value(RED), alt.value(TEAL)),
                    tooltip=[alt.Tooltip("column", title="Column"), alt.Tooltip("pct:Q", title="% missing", format=".1f")]))
    text = (alt.Chart(d).mark_text(align="left", dx=4, fontSize=11, fontWeight="bold", color=NEUTRAL)
            .encode(y=alt.Y("column:N", sort="-x"), x="pct:Q", text=alt.Text("pct:Q", format=".1f")))
    note = "Counts blank cells and placeholders such as N/A. Bars above 20% are shown in red."
    return (style(bars + text, title or auto_title("Missing values"), height=max(120, len(d) * 28 + 40)),
            d.rename(columns={"pct": "missing_%"}), note)


def build_chart(df, kind, x=None, y=None, agg="sum", top_n=10, bins=30, freq="Day", dates=None,
                title=None, sort_by="Largest first", labels=True, split=None, pct=False, numeric=None):
    """Returns (chart, plotted_data, note). chart is None when nothing can be drawn."""
    dates = dates or {}
    if kind in ("Bar", "Line", "Area"):
        return _bar_line_area(df, kind, x, y, agg, top_n, freq, dates, title, sort_by, labels)
    if kind == "Stacked bar":
        return _stacked(df, x, split, y, agg, top_n, freq, dates, title, pct)
    if kind in ("Pie", "Donut"):
        return _pie(df, kind, x, y, agg, top_n, title)
    if kind == "Scatter":
        return _scatter(df, x, y, title)
    if kind == "Histogram":
        return _hist(df, x, bins, title)
    if kind == "Box plot":
        return _box(df, y, x, title)
    if kind == "Correlation heatmap":
        return _heatmap(df, numeric or [c for c in df.columns if is_num(df[c])], title)
    return _missing(df, title)


def hidden_note(cols, numeric, why_not):
    left_out = [f"{c} ({why_not.get(c, 'other')})" for c in cols if c not in numeric]
    if not left_out:
        return None
    shown = ", ".join(left_out[:6]) + (f" and {len(left_out) - 6} more" if len(left_out) > 6 else "")
    return f"Not offered here, because they are not numbers: {shown}."


def pick_count(st, label, n_available, cap, default, key):
    """A slider whose maximum follows the number of groups the chosen column really has."""
    n_available = int(n_available)
    top = min(cap, n_available)
    if top <= 3:
        st.caption(f"This column has {n_available} different values, so all of them are shown.")
        return max(n_available, 1)
    return st.slider(label, 3, top, min(default, top), key=f"{key}_{top}")


def render_charts(df, cleaned):
    import streamlit as st

    left, right = st.columns([1, 2.2])
    problem = None
    chart = plotted = note = None

    with left:
        st.markdown("**Chart settings**")
        source = st.radio("Data", ["Original", "Cleaned"], horizontal=True, key="ch_source")
        data, converted, numeric, dates, why_not = prepare(df if source == "Original" else cleaned)
        cols = list(data.columns)
        kind = st.selectbox("Chart type", KINDS, key="ch_kind")

        x = y = split = None
        agg, top_n, bins, freq, pct = "sum", 10, 30, "Day", False
        sort_by, labels = "Largest first", True
        guess = next((i for i, c in enumerate(cols)
                      if c not in numeric and c not in dates and 2 <= data[c].nunique() <= 50), 0)
        needs_numbers = False

        if kind in ("Bar", "Line", "Area", "Stacked bar", "Pie", "Donut"):
            xlabel = {"Pie": "Slice by column", "Donut": "Slice by column"}.get(kind, "Group by column")
            x = st.selectbox(xlabel, cols, index=guess, key="ch_x")
            if kind == "Stacked bar":
                options = [c for c in cols if c != x]
                if not options:
                    problem = "A stacked bar needs at least two columns."
                else:
                    pick = next((i for i, c in enumerate(options) if c not in numeric and 2 <= data[c].nunique() <= 20), 0)
                    split = st.selectbox("Split each bar by", options, index=pick, key="ch_split")
            y = st.selectbox("Y value", [COUNT] + numeric, key="ch_y")
            needs_numbers = True
            if y != COUNT:
                agg = st.selectbox("Combine values by", ["sum", "mean", "median", "max", "min"], key="ch_agg")
            if x in dates and kind in ("Bar", "Line", "Area", "Stacked bar"):
                span = (dates[x].max() - dates[x].min()).days if dates[x].notna().any() else 0
                default = 2 if span > 180 else 1 if span > 45 else 0
                freq = st.selectbox("Group dates by", ["Day", "Week", "Month"], index=default, key="ch_freq")
            elif kind in ("Bar", "Stacked bar"):
                top_n = pick_count(st, "Top groups", data[x].nunique(), 30, 10, "ch_top")
            if kind in ("Pie", "Donut"):
                top_n = pick_count(st, "Top slices", data[x].nunique(), 7, 6, "ch_slices")
            if kind == "Bar" and x not in dates:
                sort_by = st.selectbox("Order bars", ["Largest first", "Smallest first", "A to Z"], key="ch_sort")
            if kind == "Stacked bar":
                pct = st.checkbox("Show as % of each bar", value=False, key="ch_pct")
            if kind in ("Bar", "Line", "Area"):
                labels = st.checkbox("Show value labels", value=True, key="ch_labels")
        elif kind == "Scatter":
            needs_numbers = True
            if len(numeric) < 2:
                problem = "A scatter chart needs at least two number columns."
            else:
                x = st.selectbox("X axis", numeric, key="ch_sx")
                y = st.selectbox("Y axis", numeric, index=1, key="ch_sy")
        elif kind == "Histogram":
            needs_numbers = True
            if not numeric:
                problem = "A histogram needs a number column."
            else:
                x = st.selectbox("Column", numeric, key="ch_hx")
                bins = st.slider("Number of bars", 10, 60, 30, key="ch_bins")
        elif kind == "Box plot":
            needs_numbers = True
            if not numeric:
                problem = "A box plot needs a number column."
            else:
                y = st.selectbox("Column to measure", numeric, key="ch_by")
                grp = st.selectbox("Compare by (optional)", ["(none)"] + [c for c in cols if c != y], key="ch_bg")
                x = None if grp == "(none)" else grp
        elif kind == "Correlation heatmap":
            if len(numeric) < 2:
                problem = "A heatmap needs at least two number columns."
        else:
            pass

        if converted:
            st.caption("Read as numbers, because most of their values are numbers saved as text: "
                       + ", ".join(converted[:6]) + ("..." if len(converted) > 6 else "") + ".")
        if needs_numbers:
            hint = hidden_note(cols, numeric, why_not)
            if hint:
                st.caption(hint)
        if problem is None:
            title = st.text_input("Chart title", auto_title(kind, x, y, agg, split),
                                  key=f"ch_title_{kind}_{x}_{y}_{agg}_{split}")

    with right:
        if problem is None:
            try:
                chart, plotted, note = build_chart(data, kind, x, y, agg, top_n, bins, freq, dates,
                                                   title=title, sort_by=sort_by, labels=labels,
                                                   split=split, pct=pct, numeric=numeric)
            except Exception as err:
                chart, note = None, f"This chart could not be built for this selection ({type(err).__name__})."
            if chart is None:
                problem = note
        if problem is not None:
            st.info(problem)
        else:
            try:
                st.altair_chart(chart, use_container_width=True, theme=None)
            except Exception as err:
                st.warning(f"This chart could not be drawn for this selection ({type(err).__name__}). "
                           "Try different columns or another chart type.")
            else:
                if note:
                    st.caption(note)
                st.caption(f"This chart uses the {source.lower()} file.")
                st.download_button("Download chart data (CSV)", plotted.to_csv(index=False).encode("utf-8"),
                                   file_name="chart_data.csv", mime="text/csv", key="ch_dl")
