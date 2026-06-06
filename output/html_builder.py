from utils.datetime_utils import now_jst
from datetime import datetime
from html import escape
import re


# =========================
# 基本関数
# =========================
def safe(v):
    if v in [None, "", "None"]:
        return "N/A"
    return str(v)


def fmt_change(v):
    if not v:
        return "N/A"
    if str(v).startswith("+"):
        return f'<span style="color:green">{v}</span>'
    if str(v).startswith("-"):
        return f'<span style="color:red">{v}</span>'
    return v


# =========================
# サプライズ判定
# =========================
def extract_number(text):
    if not text:
        return None
    t = text.replace(",", "")
    m = re.search(r"-?\d+\.?\d*", t)
    if not m:
        return None
    return float(m.group())


def surprise_badge(event_name, actual, forecast):
    a = extract_number(actual)
    f = extract_number(forecast)

    if a is None or f is None:
        return "---"

    if abs(a - f) < 1e-6:
        return "予想通り"

    # 上が良い指標
    high_good = ["GDP", "PMI", "雇用", "売上", "生産"]

    # 下が良い指標
    low_good = ["失業率"]

    if any(k in event_name for k in high_good):
        return "ポジティブ上振れ" if a > f else "ネガティブ下振れ"

    if any(k in event_name for k in low_good):
        return "ポジティブ下振れ" if a < f else "ネガティブ上振れ"

    return "上振れ" if a > f else "下振れ"


# =========================
# 重要度色
# =========================
def importance_color(v):
    s = safe(v)
    if "高" in s or "★★★" in s:
        return "🔴"
    if "中" in s or "★★" in s:
        return "🟠"
    return "⚪"


# =========================
# 経済指標テーブル
# =========================
def render_events(title, events):
    html = f"<h3>📅 {title}</h3>"

    if not events:
        return html + "<p>なし</p>"

    html += """
    <table border="1" cellpadding="4" cellspacing="0">
    <tr>
        <th>日付</th>
        <th>時間</th>
        <th>国</th>
        <th>指標</th>
        <th>予想</th>
        <th>結果</th>
        <th>前回</th>
        <th>重要度</th>
        <th>サプライズ</th>
    </tr>
    """

    for e in events:
        html += f"""
        <tr>
            <td>{safe(e.get("event_date_jst"))}</td>
            <td>{safe(e.get("event_time_jst"))}</td>
            <td>{safe(e.get("country"))}</td>
            <td>{safe(e.get("event_name"))}</td>
            <td>{safe(e.get("forecast"))}</td>
            <td>{safe(e.get("actual"))}</td>
            <td>{safe(e.get("previous"))}</td>
            <td>{importance_color(e.get("importance_label"))}</td>
            <td>{surprise_badge(e.get("event_name"), e.get("actual"), e.get("forecast"))}</td>
        </tr>
        """

    html += "</table>"
    return html


# =========================
# メインHTML
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

    html = f"""
    <html>
    <body>

    <h2>Market Report ({today})</h2>

    {render_events("昨日", macro_payload.get("yesterday_events", []))}
    {render_events("本日", macro_payload.get("today_events", []))}
    {render_events("今週", macro_payload.get("week_events", []))}

    <h3>🧠 AIまとめ</h3>
    <p>{escape(str(ai_summary))}</p>

    <h3>📊 スコア</h3>
    <p>{score} / {regime} / {signal}</p>

    </body>
    </html>
    """

    return html
