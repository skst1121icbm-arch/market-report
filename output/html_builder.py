from utils.datetime_utils import now_jst


# =========================
# 基本フォーマット
# =========================
def _fmt_num(v):
    try:
        return f"{float(v):.2f}"
    except:
        return "N/A"


def _fmt_pct(v):
    try:
        return f"{float(v):.2f}%"
    except:
        return "N/A"


def _safe(v):
    if v in [None, "", "None"]:
        return "N/A"
    return str(v)


def _find(label, rows):
    for r in rows:
        if r["label"] == label:
            return r
    return None


def _val(label, rows):
    r = _find(label, rows)
    if not r:
        return None, None
    return r.get("value"), r.get("change_text")


def _color(text):
    if not text:
        return ""

    if str(text).startswith("+"):
        return f'<span style="color:green">{text}</span>'
    elif str(text).startswith("-"):
        return f'<span style="color:red">{text}</span>'

    return text


def _warn(text):
    return f'<span style="color:red;font-weight:bold;">{text}</span>'


# =========================
# AI整形
# =========================
def _render_summary(text):
    if not text:
        return "N/A"

    lines = text.split("\n")
    out = []

    for i, l in enumerate(lines):
        if i == 0 and l.startswith("要約:"):
            out.append(f"<b>{l}</b>")
        else:
            out.append(l)

    return "<br>".join(out)


# =========================
# ★変換
# =========================
def _to_stars(e):
    txt = f"{_safe(e.get('importance_label'))} {_safe(e.get('event_status'))}"

    if "高" in txt or "重要" in txt:
        return "★★★"
    elif "中" in txt:
        return "★★"
    return "★"


# =========================
# テーブル
# =========================
def _table3(title, rows):
    body = ""
    for name, v, c in rows:
        body += f"""
        <tr>
        <td>{name}</td>
        <td style='text-align:right'>{_fmt_num(v)}</td>
        <td style='text-align:right'>{_color(c)}</td>
        </tr>
        """

    return f"""
    <h3>{title}</h3>
    <table border='1' style='border-collapse:collapse;width:100%'>
    <tr style='background:#eaf3ff'>
        <th>項目</th><th>値</th><th>前日比</th>
    </tr>
    {body}
    </table>
    """


def _table2(title, rows):
    body = ""
    for k, v in rows:
        body += f"""
        <tr>
        <td>{k}</td>
        <td style='text-align:right'>{v}</td>
        </tr>
        """

    return f"""
    <h3>{title}</h3>
    <table border='1' style='border-collapse:collapse;width:100%'>
    <tr style='background:#eaf3ff'>
        <th>項目</th><th>値</th>
    </tr>
    {body}
    </table>
    """


def _econ(title, events):
    body = ""

    if not events:
        body = "<tr><td>なし</td></tr>"
    else:
        for e in events:
            body += f"""
            <tr>
            <td>{_safe(e.get('country'))}</td>
            <td>{_safe(e.get('event_name'))}</td>
            <td>{_safe(e.get('forecast'))}</td>
            <td>{_safe(e.get('actual'))}</td>
            <td>{_safe(e.get('previous'))}</td>
            <td>{_to_stars(e)}</td>
            </tr>
            """

    return f"""
    <h3>📅 {title}</h3>
    <table border='1' style='border-collapse:collapse;width:100%'>
    <tr style='background:#eaf3ff'>
      <th>国</th><th>指標</th><th>予想</th>
      <th>結果</th><th>前回</th><th>重要度</th>
    </tr>
    {body}
    </table>
    """


# =========================
# メイン
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

    major = _table3("🚀 主要指数", [
        ("S&P500", *_val("S&P500", market_rows)),
        ("NASDAQ", *_val("NASDAQ", market_rows)),
        ("NYダウ", *_val("NYダウ", market_rows)),
        ("Russell2000", *_val("Russell2000", market_rows)),
        ("日経平均", *_val("日経平均", market_rows)),
    ])

    rate = _table3("✅ 金利", [
        ("米10年債利回り", *_val("米10年金利", market_rows)),
        ("米2年債利回り", rate_extras.get("米2年債利回り"), "")
    ])

    try:
        spread = float(_val("米10年金利", market_rows)[0]) - float(rate_extras.get("米2年債利回り"))
        spread = f"{spread:.2f}"
    except:
        spread = "N/A"

    breadth_table = _table2("📈 市場の広がり", [
        ("上昇銘柄比率", _fmt_pct(breadth.get("ratio"))),
        ("状態", _safe(breadth.get("state")))
    ])

    sector = _table2("セクター", [
        (r["label"], _color(r["change_text"])) for r in sector_rows
    ])

    econ_y = _econ("経済指標（昨日）", macro_payload.get("yesterday_events"))
    econ_t = _econ("経済指標（本日）", macro_payload.get("today_events"))

    summary = f"<h3>🧠 まとめ</h3><div>{_render_summary(ai_summary)}</div>"

    return f"""
    <html>
    <body style='font-family:Arial'>
    <h2>Daily Market Report ({today})</h2>

    {major}
    {rate}
    <p><b>10Y-2Y:</b> {spread}</p>
    {breadth_table}
    {sector}
    {econ_y}
    {econ_t}
    {summary}

    <h3>スコア</h3>
    {score} ({regime})<br>{signal}

    </body>
    </html>
    """
