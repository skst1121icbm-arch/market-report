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

    s = str(text)
    if s.startswith("+"):
        return f'<span style="color:#0a8f2a; font-weight:600;">{s}</span>'
    elif s.startswith("-"):
        return f'<span style="color:#c62828; font-weight:600;">{s}</span>'
    return s


def _warn(text):
    return f'<span style="color:#c62828; font-weight:700;">{text}</span>'


# =========================
# AI要約
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
# テーブル共通スタイル
# =========================
TABLE_STYLE = """
width:100%;
border-collapse:collapse;
table-layout:fixed;
font-size:14px;
"""

TH_STYLE = """
background:#eaf3ff;
padding:10px;
border-bottom:1px solid #d9e3f0;
"""

TD_STYLE = """
padding:10px;
border-bottom:1px solid #eceff4;
"""


def _th(txt):
    return f'<th style="{TH_STYLE}">{txt}</th>'


def _td(txt, align="left"):
    style = TD_STYLE + f"text-align:{align};"
    return f'<td style="{style}">{txt}</td>'


def _title(icon, text):
    return f"<h3>{icon} {text}</h3>"


def _table(header, body):
    return f"""
    <table style="{TABLE_STYLE}">
    {header}
    {body}
    </table>
    """


# =========================
# 3列テーブル
# =========================
def _table3(icon, title, rows):
    body = ""
    for name, v, c in rows:
        body += "<tr>"
        body += _td(name)
        body += _td(_fmt_num(v), "right")
        body += _td(_color(c), "right")
        body += "</tr>"

    return (
        _title(icon, title)
        + _table(
            "<tr>" + _th("項目") + _th("値") + _th("前日比") + "</tr>",
            body,
        )
    )


# =========================
# 2列テーブル
# =========================
def _table2(icon, title, rows, col2="値"):
    body = ""
    for a, b in rows:
        body += "<tr>"
        body += _td(a)
        body += _td(b, "right")
        body += "</tr>"

    return (
        _title(icon, title)
        + _table(
            "<tr>" + _th("項目") + _th(col2) + "</tr>",
            body,
        )
    )


# =========================
# 経済指標
# =========================
def _econ_table(title, events):
    body = ""

    if not events:
        body += "<tr>" + _td("なし") + _td("")*5 + "</tr>"

    else:
        for e in events:
            body += "<tr>"
            body += _td(_safe(e.get("country")))
            body += _td(_safe(e.get("event_name")))
            body += _td(_safe(e.get("forecast")), "right")
            body += _td(_safe(e.get("actual")), "right")
            body += _td(_safe(e.get("previous")), "right")
            body += _td(_to_stars(e), "center")
            body += "</tr>"

    return (
        _title("📅", title)
        + _table(
            "<tr>"
            + _th("国")
            + _th("指標")
            + _th("予想")
            + _th("結果")
            + _th("前回")
            + _th("重要度")
            + "</tr>",
            body,
        )
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

    # ===== 指数
    major = _table3("🚀", "主要指数", [
        (*_val("S&P500", market_rows),),
        (*_val("NASDAQ", market_rows),),
        (*_val("NYダウ", market_rows),),
        (*_val("Russell2000", market_rows),),
        (*_val("日経平均", market_rows),),
    ])

    # ===== 金利
    y10, y10c = _val("米10年金利", market_rows)
    y2 = rate_extras.get("米2年債利回り")

    try:
        y2c = f"{rate_extras.get('米2年債利回り_前日比_pct'):+.2f}%"
    except:
        y2c = ""

    rate = _table3("✅", "金利", [
        ("米10年債利回り", y10, y10c),
        ("米2年債利回り", y2, y2c),
    ])

    try:
        spread = float(y10) - float(y2)
        spread = f"{spread:.2f}"
        if float(spread) < 0:
            spread = _warn(spread)
    except:
        spread = "N/A"

    rate_comment = f"<p><b>10Y-2Y:</b> {spread}</p>"

    # ===== 為替
    fx = _table3("💱", "為替", [
        (*_val("DXY", market_rows),),
        (*_val("USD/JPY", market_rows),),
        (*_val("EUR/USD", market_rows),),
    ])

    # ===== コモディティ
    com = _table3("🛢️", "コモディティ", [
        (*_val("WTI原油", market_rows),),
        (*_val("ゴールド", market_rows),),
        (*_val("銅", market_rows),),
    ])

    # ===== 仮想通貨
    crypto = _table3("🪙", "仮想通貨", [
        (*_val("BTC (USD)", market_rows),),
        (*_val("ETH (USD)", market_rows),),
        (*_val("XRP (USD)", market_rows),),
        (*_val("SOL (USD)", market_rows),),
    ])

    # ===== ETF
    etf = _table2("💰", "ETFフロー", [
        ("SPY", _color(etf_flows.get("SPY"))),
        ("QQQ", _color(etf_flows.get("QQQ"))),
        ("IWM", _color(etf_flows.get("IWM"))),
    ], "前日比")

    etf_comment = f"<p><b>市場傾向:</b> {_safe(etf_flows.get('interpretation'))}</p>"

    # ===== Options
    options = _table2("🎯", "オプション", [
        ("Put/Call", _fmt_num(options_data.get("put_call")))
    ])

    options_comment = f"<p><b>センチメント:</b> {_safe(options_data.get('sentiment'))}</p>"

    # ===== Breadth
    ratio = breadth.get("ratio")
    ratio_txt = _fmt_pct(ratio)

    if ratio and ratio <= 30:
        ratio_txt = _warn(ratio_txt)

    breadth_table = _table2("📈", "市場の広がり", [
        ("上昇銘柄比率", ratio_txt),
        ("状態", _safe(breadth.get("state")))
    ])

    # ===== セクター
    sector_rows2 = []
    for r in sector_rows:
        sector_rows2.append((r["label"], _color(r["change_text"])))

    sector_table = _table2("✅", "セクター", sector_rows2, "前日比")

    # ===== 経済指標
    econ_y = _econ_table("経済指標（昨日）", macro_payload.get("yesterday_events"))
    econ_t = _econ_table("経済指標（本日）", macro_payload.get("today_events"))

    # ===== まとめ
    summary = f"""
    <div style="background:#f8f9fb;padding:12px;border-radius:8px;">
    {_render_summary(ai_summary)}
    </div>
    """

    # ===== スコア
    score_sec = f"<p>{score} ({regime})<br>{signal}</p>"

    return f"""
    <html>
    <body style="font-family:Arial;max-width:960px;margin:auto;">

    <h2>Daily Market Report ({today})</h2>

    {major}
    {rate}
    {rate_comment}
    {fx}
    {com}
    {crypto}
    {etf}
    {etf_comment}
    {options}
    {options_comment}
    {breadth_table}
    {sector_table}
    {econ_y}
    {econ_t}

    <h3>🧠 まとめ</h3>
    {summary}

    <h3>✅ スコア</h3>
    {score_sec}

    </body>
    </html>
    """
