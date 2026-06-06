from utils.datetime_utils import now_jst
import re
from html import escape

# =========================
# BASIC HELPERS
# =========================
def _fmt_num(v):
    if v in [None, "", "None"]:
        return "N/A"
    try:
        return f"{float(v):.2f}"
    except Exception:
        return escape(str(v))


def _fmt_pct(v):
    if v in [None, "", "None"]:
        return "N/A"
    try:
        return f"{float(v):.2f}%"
    except Exception:
        return escape(str(v))


def _safe(v):
    if v in [None, "", "None"]:
        return "N/A"
    return str(v)


def _find(label, rows):
    for r in rows or []:
        if r.get("label") == label:
            return r
    return None


def _val(label, rows):
    r = _find(label, rows)
    if not r:
        return None, ""
    return r.get("value"), r.get("change_text", "")

# ✅ 色付け（今回のメイン）
def _color_change(v):
    if not v:
        return ""
    s = str(v)

    if s.startswith("+"):
        return f'<span style="color:#16a34a;">{escape(s)}</span>'  # 緑
    elif s.startswith("-"):
        return f'<span style="color:#dc2626;">{escape(s)}</span>'  # 赤

    return escape(s)


def _warn(text):
    return f'<span style="color:#dc2626;">{escape(str(text))}</span>'


# =========================
# SUMMARY
# =========================
def _clean_summary_text(text: str) -> str:
    if not text:
        return "N/A"

    s = str(text)
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("**", "")

    lines = s.split("\n")
    blocks = []

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        esc = escape(line)
        if i == 0 and line.startswith("要約:"):
            blocks.append(f"<strong>{esc}</strong><br>")
        else:
            blocks.append(f"{esc}<br>")

    return "".join(blocks)


# =========================
# IMPORTANCE
# =========================
def _stars(e):
    txt = f"{_safe(e.get('importance_label'))} {_safe(e.get('event_status'))}"
    if "高" in txt:
        return "★★★"
    elif "中" in txt:
        return "★★"
    return "★"


# =========================
# TABLE STYLE（縦線なし）
# =========================
def _table_open():
    return '<table style="width:100%; border-collapse:collapse;">'


def _table_close():
    return "</table><br>"


def _th(text):
    return f'''
<th style="border-bottom:1px solid #ddd; padding:6px; text-align:center;">
{escape(str(text))}
</th>
'''


def _td(text, align="center", colspan=None):
    colspan_attr = f' colspan="{colspan}"' if colspan else ""
    return f'''
<td{colspan_attr} style="border-bottom:1px solid #eee; padding:6px; text-align:{align};">
{text}
</td>
'''


def _section_title(icon, title):
    return f'<h3 style="margin-top:16px;">{icon} {escape(title)}</h3>'


# =========================
# TABLES
# =========================
def _table_3col(title_icon, title, rows):
    body = []
    for name, value, change in rows:
        body.append("<tr>")
        body.append(_td(escape(str(name))))
        body.append(_td(_fmt_num(value)))
        body.append(_td(_color_change(change)))
        body.append("</tr>")

    return (
        _section_title(title_icon, title)
        + _table_open()
        + "<tr>" + _th("項目") + _th("値") + _th("前日比") + "</tr>"
        + "".join(body)
        + _table_close()
    )


def _table_2col(title_icon, title, rows, col1="項目", col2="値"):
    body = []
    for left, right in rows:
        body.append("<tr>")
        body.append(_td(escape(str(left))))
        body.append(_td(right))
        body.append("</tr>")

    return (
        _section_title(title_icon, title)
        + _table_open()
        + "<tr>" + _th(col1) + _th(col2) + "</tr>"
        + "".join(body)
        + _table_close()
    )


def _table_econ(title_icon, title, events):
    body = []

    if not events:
        body.append("<tr>")
        body.append(_td("該当なし（条件に一致する指標なし）", colspan=6))
        body.append("</tr>")
    else:
        for e in events:
            body.append("<tr>")
            body.append(_td(_safe(e.get("country"))))
            body.append(_td(_safe(e.get("event_name"))))
            body.append(_td(_safe(e.get("forecast"))))
            body.append(_td(_safe(e.get("actual"))))
            body.append(_td(_safe(e.get("previous"))))
            body.append(_td(_stars(e)))
            body.append("</tr>")

    return (
        _section_title(title_icon, title)
        + _table_open()
        + "<tr>"
        + _th("国")
        + _th("指標")
        + _th("予想")
        + _th("結果")
        + _th("前回")
        + _th("重要度")
        + "</tr>"
        + "".join(body)
        + _table_close()
    )


# =========================
# MAIN
# =========================
def build_html(
    market_rows,
    sector_rows,
    score,
    regime,
    signal,
    signal_details,
    reasons,
    ai_summary,
    macro_payload,
    breadth,
    etf_flows,
    options_data,
    rate_extras,
):
    today = now_jst().strftime("%Y-%m-%d")

    # ===== 主要指数 =====
    major_rows = []
    for label in ["S&P500", "NASDAQ", "NYダウ", "Russell2000", "日経平均"]:
        v, c = _val(label, market_rows)
        major_rows.append((label, v, c))
    major_table = _table_3col("🚀", "主要指数", major_rows)

    # ===== 金利 =====
    y10, y10c = _val("米10年金利", market_rows)
    y2 = rate_extras.get("米2年債利回り")
    y2_change = rate_extras.get("米2年債利回り_前日比_pct")

    try:
        y2_change_text = f"{y2_change:+.2f}%"
    except:
        y2_change_text = "N/A"

    rate_rows = [
        ("米10年債利回り", y10, y10c),
        ("米2年債利回り", y2, y2_change_text),
    ]

    rate_table = _table_3col("✅", "金利", rate_rows)

    # ===== 為替 =====
    fx_rows = []
    for label in ["DXY", "USD/JPY", "EUR/USD"]:
        v, c = _val(label, market_rows)
        fx_rows.append((label, v, c))
    fx_table = _table_3col("💱", "為替", fx_rows)

    # ===== 経済指標 =====
    econ_super = _table_econ("🚨", "重要経済指標", macro_payload.get("super_important_events", []))
    econ_today = _table_econ("📅", "経済指標（本日）", macro_payload.get("today_events", []))
    econ_week = _table_econ("📅", "経済指標（今週・重要）", macro_payload.get("week_events", []))
    econ_yesterday = _table_econ("📅", "経済指標（昨日）", macro_payload.get("yesterday_events", []))

    summary_section = f"<h3>🧠 まとめ</h3>{_clean_summary_text(ai_summary)}"
    score_section = f"<h3>📊 スコア</h3>{score} ({regime})<br>{signal}"

    return f"""
<h2>Daily Market Report ({today})</h2>

{major_table}
{rate_table}
{fx_table}

{econ_super}
{econ_today}
{econ_week}
{econ_yesterday}

{summary_section}
{score_section}
"""
