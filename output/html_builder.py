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


def _color_change(v):
    if not v:
        return ""
    return escape(str(v))


def _warn(text):
    return f'{escape(str(text))}'

# =========================
# SUMMARY
# =========================
def _clean_summary_text(text: str) -> str:
    if not text:
        return "N/A"

    s = str(text)
    s = re.sub(r"", "", s, flags=re.IGNORECASE)
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

    return "".join(blocks) if blocks else "N/A"

# =========================
# IMPORTANCE
# =========================
def _stars(e):
    txt = f"{_safe(e.get('importance_label'))} {_safe(e.get('event_status'))}"
    if "高" in txt or "重要" in txt:
        return "★★★"
    elif "中" in txt:
        return "★★"
    return "★"

# =========================
# TABLE HELPERS
# =========================
def _table_open():
    return "<table border='1' cellspacing='0' cellpadding='4'>"


def _table_close():
    return "</table><br>"


def _th(text):
    return f"<th>{escape(str(text))}</th>"


def _td(text):
    return f"<td>{text}</td>"


def _section_title(icon, title):
    return f"<h3>{icon} {escape(title)}</h3>"

# =========================
# TABLES
# =========================
def _table_3col(title_icon, title, rows):
    body = ""
    for name, value, change in rows:
        body += "<tr>"
        body += _td(escape(str(name)))
        body += _td(_fmt_num(value) if value not in ["", None] else "")
        body += _td(_color_change(change))
        body += "</tr>"

    return (
        _section_title(title_icon, title)
        + _table_open()
        + "<tr>" + _th("項目") + _th("値") + _th("前日比") + "</tr>"
        + body
        + _table_close()
    )


def _table_2col(title_icon, title, rows, col1="項目", col2="値"):
    body = ""
    for left, right in rows:
        body += "<tr>"
        body += _td(escape(str(left)))
        body += _td(right)
        body += "</tr>"

    return (
        _section_title(title_icon, title)
        + _table_open()
        + "<tr>" + _th(col1) + _th(col2) + "</tr>"
        + body
        + _table_close()
    )


def _table_econ(title_icon, title, events):
    body = ""

    if not events:
        body += "<tr><td colspan='6'>なし</td></tr>"
    else:
        for e in events:
            body += "<tr>"
            body += _td(escape(_safe(e.get("country"))))
            body += _td(escape(_safe(e.get("event_name"))))
            body += _td(escape(_safe(e.get("forecast"))))
            body += _td(escape(_safe(e.get("actual"))))
            body += _td(escape(_safe(e.get("previous"))))
            body += _td(_stars(e))
            body += "</tr>"

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
        + body
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

    # 主要指数
    major_rows = []
    for label in ["S&P500", "NASDAQ", "NYダウ", "Russell2000", "日経平均"]:
        v, c = _val(label, market_rows)
        major_rows.append((label, v, c))

    major_table = _table_3col("🚀", "主要指数", major_rows)

    # ===== 経済指標 =====
    econ_yesterday = _table_econ(
        "📅",
        "経済指標（昨日）",
        macro_payload.get("yesterday_events", []),
    )

    econ_today = _table_econ(
        "📅",
        "経済指標（本日）",
        macro_payload.get("today_events", []),
    )

    # ✅ 今週重要（追加）
    econ_week = _table_econ(
        "📅",
        "経済指標（今週・重要）",
        macro_payload.get("week_events", []),
    )

    # ===== まとめ =====
    summary_section = f"""
    <h3>🧠 まとめ</h3>
    {_clean_summary_text(ai_summary)}
    """

    # ===== スコア =====
    score_section = f"""
    <h3>📊 スコア</h3>
    {escape(str(score))} ({escape(_safe(regime))})<br>
    {escape(_safe(signal))}
    """

    return f"""
    <h2>Daily Market Report ({today})</h2>

    {major_table}

    {econ_yesterday}
    {econ_today}
    {econ_week}

    {summary_section}
    {score_section}
    """
