from utils.datetime_utils import now_jst
import re
from html import escape

# =========================
# BASIC
# =========================
def _safe(v):
    if v in [None, "", "None"]:
        return "N/A"
    return str(v)


def _color_change(v):
    if not v:
        return ""
    s = str(v)

    if s.startswith("+"):
        return f'<span style="color:#16a34a; font-weight:600;">{escape(s)}</span>'
    elif s.startswith("-"):
        return f'<span style="color:#dc2626; font-weight:600;">{escape(s)}</span>'

    return escape(s)


def _sector_change(v):
    if not v:
        return ""
    s = str(v)

    if s.startswith("+"):
        return f'<span style="color:#16a34a; font-weight:700;">{escape(s)}</span>'
    elif s.startswith("-"):
        return f'<span style="color:#dc2626; font-weight:700;">{escape(s)}</span>'

    return escape(s)


# =========================
# SUMMARY（新仕様）
# =========================
def _clean_summary_text(text: str):
    if not text:
        return "主因: N/A<br>市場の反応: N/A<br>結論: N/A"

    s = str(text)
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("**", "")
    s = re.sub(r"^\s*要約:\s*", "", s)
    s = re.sub(r"\s+", " ", s).strip()

    if len(s) > 200:
        s = s[:200] + "…"

    parts = [p.strip() for p in s.split("。") if p.strip()]

    main = parts[0] if len(parts) > 0 else "N/A"
    reaction = parts[1] if len(parts) > 1 else "N/A"
    conclusion = parts[2] if len(parts) > 2 else "N/A"

    return (
        f"<strong>主因:</strong> {escape(main)}<br>"
        f"<strong>市場の反応:</strong> {escape(reaction)}<br>"
        f"<strong>結論:</strong> {escape(conclusion)}"
    )


# =========================
# TABLE
# =========================
def _table(title, headers, rows):
    html = f"<h3>{title}</h3>"
    html += '<table style="width:100%; border-collapse:collapse;">'

    html += "<tr>"
    for h in headers:
        html += f'<th style="border-bottom:1px solid #ddd;">{h}</th>'
    html += "</tr>"

    for row in rows:
        html += "<tr>"
        for cell in row:
            html += f'<td style="border-bottom:1px solid #eee; text-align:center;">{cell}</td>'
        html += "</tr>"

    html += "</table>"
    return html


def _table_econ(title, events):
    rows = []

    for e in events or []:
        name = _safe(e.get("event_name"))

        # CPI強調
        if "CPI" in name:
            name = f'<span style="background:#dc2626;color:white;padding:2px 4px;">{escape(name)}</span>'

        # 高重要度
        if "高" in str(e.get("importance_label")):
            name = f"<strong>{name}</strong>"

        rows.append([
            _safe(e.get("country")),
            name,
            _safe(e.get("forecast")),
            _safe(e.get("actual")),
            _safe(e.get("previous")),
            e.get("importance_label"),
        ])

    return _table(title, ["国","指標","予想","結果","前回","重要度"], rows)


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
    for label in ["S&P500","NASDAQ","NYダウ","Russell2000","日経平均","VIX"]:
        v = next((r.get("value") for r in market_rows if r["label"] == label), "N/A")
        c = next((r.get("change_text") for r in market_rows if r["label"] == label), "")
        major_rows.append([label, v, _color_change(c)])

    major_table = _table("🚀 主要指数", ["項目","値","前日比"], major_rows)

    # ===== セクター =====
    sector_data = []
    for r in sector_rows:
        sector_data.append([r["label"], _sector_change(r.get("change_text"))])
    sector_table = _table("✅ セクター", ["セクター","前日比"], sector_data)

    # ===== 経済指標 =====
    econ_super = _table_econ("🚨 重要経済指標", macro_payload.get("super_important_events", []))
    econ_today = _table_econ("📅 経済指標（本日）", macro_payload.get("today_events", []))
    econ_week = _table_econ("📅 経済指標（今週・重要）", macro_payload.get("week_events", []))
    econ_y = _table_econ("📅 経済指標（昨日）", macro_payload.get("yesterday_events", []))

    return f"""
<h2>Daily Market Report ({today})</h2>

{major_table}
{sector_table}

{econ_super}
{econ_today}
{econ_week}
{econ_y}

<h3>🧠 まとめ</h3>
{_clean_summary_text(ai_summary)}

<h3>📊 スコア</h3>
{score} ({regime})<br>{signal}
"""
