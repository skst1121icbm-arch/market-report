from utils.datetime_utils import now_jst
from html import escape

# =========================
# HELPERS
# =========================
def _safe(v):
    if v in [None, "", "None"]:
        return ""
    return str(v)


def _stars(e):
    txt = _safe(e.get("importance_label"))
    if "高" in txt:
        return "★★★"
    if "中" in txt:
        return "★★"
    return "★"


def _section_title(icon, title):
    return f"<h3>{icon} {escape(title)}</h3>"


def _table_open():
    return "<table border='1' cellspacing='0' cellpadding='4'>"


def _table_close():
    return "</table><br>"


def _th(text):
    return f"<th>{escape(text)}</th>"


def _td(text):
    return f"<td>{text}</td>"


# =========================
# 経済指標テーブル
# =========================
def _table_econ(title_icon, title, events):
    body = ""

    if not events:
        body += "<tr><td colspan='6'>該当なし（条件に一致する指標なし）</td></tr>"
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
# MAIN HTML
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

    # =========================
    # 経済指標
    # =========================

    # ✅ 重要経済指標（名前変更のみ）
    econ_super_important = _table_econ(
        "🚨",
        "重要経済指標",
        macro_payload.get("super_important_events", []),
    )

    econ_today = _table_econ(
        "📅",
        "経済指標（本日）",
        macro_payload.get("today_events", []),
    )

    econ_week = _table_econ(
        "📅",
        "経済指標（今週・重要）",
        macro_payload.get("week_events", []),
    )

    econ_yesterday = _table_econ(
        "📅",
        "経済指標（昨日）",
        macro_payload.get("yesterday_events", []),
    )

    # ✅ 補足（UX向上）
    econ_week_comment = """
    <div style="font-size:12px;color:#666;">
    ※ 今週の未発表かつ重要度★★以上の指標のみ表示
    </div>
    """

    # =========================
    # まとめ
    # =========================
    summary_section = f"""
    <h3>🧠 まとめ</h3>
    {escape(str(ai_summary))}
    """

    # =========================
    # スコア
    # =========================
    score_section = f"""
    <h3>📊 スコア</h3>
    {escape(str(score))} ({escape(_safe(regime))})<br>
    {escape(_safe(signal))}
    """

    # =========================
    # 最終HTML
    # =========================
    return f"""
    <h2>Daily Market Report ({today})</h2>

    {econ_super_important}
    {econ_today}
    {econ_week}
    {econ_week_comment}
    {econ_yesterday}

    {summary_section}
    {score_section}
    """
