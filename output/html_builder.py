from utils.datetime_utils import now_jst


# =========================
# format
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
    return "N/A" if v in [None, "", "None"] else str(v)


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


def _color(v):
    if not v:
        return ""
    if str(v).startswith("+"):
        return f'<span style="color:#0a8f2a;">{v}</span>'
    if str(v).startswith("-"):
        return f'<span style="color:#c62828;">{v}</span>'
    return v


def _warn(v):
    return f'<span style="color:#c62828;font-weight:bold;">{v}</span>'


# =========================
# summary
# =========================
def _summary(text):
    if not text:
        return "N/A"

    lines = text.split("\n")

    # ✅ 最初の1行（要約）のみ太字
    if lines:
        lines[0] = f"<b>{lines[0]}</b>"

    return "<br>".join(lines)


# =========================
# stars
# =========================
def _stars(e):
    txt = f"{_safe(e.get('importance_label'))} {_safe(e.get('event_status'))}"

    if "高" in txt or "重要" in txt:
        return "★★★"
    elif "中" in txt:
        return "★★"
    return "★"


# =========================
# table style
# =========================
TABLE_STYLE = """
border-collapse:collapse;
width:100%;
table-layout:fixed;
"""

TH = "background:#eaf3ff;padding:8px;text-align:left"
TD = "padding:8px;border-bottom:1px solid #eee"


# =========================
# table helpers
# =========================
def _table3(title, rows):
    body = ""
    for name, v, c in rows:
        body += f"""
        <tr>
        <td style="{TD}">{name}</td>
        <td style="{TD};text-align:right">{_fmt_num(v)}</td>
        <td style="{TD};text-align:right">{_color(c)}</td>
        </tr>
        """

    return f"""
    <h3>{title}</h3>
    <table style="{TABLE_STYLE}">
    <tr>
        <th style="{TH}">項目</th>
        <th style="{TH}">値</th>
        <th style="{TH}">前日比</th>
    </tr>
    {body}
    </table>
    """


def _table2(title, rows):
    body = ""
    for k, v in rows:
        body += f"""
        <tr>
        <td style="{TD}">{k}</td>
        <td style="{TD};text-align:right">{v}</td>
        </tr>
        """

    return f"""
    <h3>{title}</h3>
    <table style="{TABLE_STYLE}">
    <tr>
        <th style="{TH}">項目</th>
        <th style="{TH}">値</th>
    </tr>
    {body}
    </table>
    """


def _econ(title, events):
    body = ""

    for e in events or []:
        body += f"""
        <tr>
        <td style="{TD}">{_safe(e.get('country'))}</td>
        <td style="{TD}">{_safe(e.get('event_name'))}</td>
        <td style="{TD}">{_safe(e.get('forecast'))}</td>
        <td style="{TD}">{_safe(e.get('actual'))}</td>
        <td style="{TD}">{_safe(e.get('previous'))}</td>
        <td style="{TD};text-align:center">{_stars(e)}</td>
        </tr>
        """

    return f"""
    <h3>📅 {title}</h3>
    <table style="{TABLE_STYLE}">
    <tr>
        <th style="{TH}">国</th>
        <th style="{TH}">指標</th>
        <th style="{TH}">予想</th>
        <th style="{TH}">結果</th>
        <th style="{TH}">前回</th>
        <th style="{TH}">重要度</th>
    </tr>
    {body}
    </table>
    """


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
    major = _table3("🚀 主要指数", [
        ("S&P500", *_val("S&P500", market_rows)),
        ("NASDAQ", *_val("NASDAQ", market_rows)),
        ("NYダウ", *_val("NYダウ", market_rows)),
        ("Russell2000", *_val("Russell2000", market_rows)),
        ("日経平均", *_val("日経平均", market_rows)),
    ])

    # ===== 金利
    y10, y10c = _val("米10年金利", market_rows)
    y2 = rate_extras.get("米2年債利回り")

    y2_change = rate_extras.get("米2年債利回り_前日比_pct")
    try:
        y2c = f"{y2_change:+.2f}%"
    except:
        y2c = ""

    rate = _table3("✅ 金利", [
        ("米10年債利回り", y10, y10c),
        ("米2年債利回り", y2, y2c),
    ])

    # スプレッド
    try:
        spread_val = float(y10) - float(y2)
        spread = f"{spread_val:.2f}"
        if spread_val < 0:
            spread = _warn(spread)
    except:
        spread = "N/A"

    # ===== 為替
    fx = _table3("💱 為替", [
        ("DXY", *_val("DXY", market_rows)),
        ("USD/JPY", *_val("USD/JPY", market_rows)),
        ("EUR/USD", *_val("EUR/USD", market_rows)),
    ])

    # ===== コモディティ
    com = _table3("🛢️ コモディティ", [
        ("WTI原油", *_val("WTI原油", market_rows)),
        ("ゴールド", *_val("ゴールド", market_rows)),
        ("銅", *_val("銅", market_rows)),
    ])

    # ===== 仮想通貨
    crypto = _table3("🪙 仮想通貨", [
        ("BTC", *_val("BTC (USD)", market_rows)),
        ("ETH", *_val("ETH (USD)", market_rows)),
        ("XRP", *_val("XRP (USD)", market_rows)),
        ("SOL", *_val("SOL (USD)", market_rows)),
    ])

    # ===== Breadth
    r = breadth.get("ratio")
    r_txt = _fmt_pct(r)

    if r is not None and r <= 30:
        r_txt = _warn(r_txt)

    breadth_tbl = _table2("📈 市場の広がり", [
        ("上昇銘柄比率", r_txt),
        ("状態", _safe(breadth.get("state")))
    ])

    # ===== セクター
    sector_tbl = _table2("✅ セクター", [
        (r["label"], _color(r["change_text"]))
        for r in sector_rows
    ])

    # ===== 経済指標
    econ_y = _econ("経済指標（昨日）", macro_payload.get("yesterday_events"))
    econ_t = _econ("経済指標（本日）", macro_payload.get("today_events"))

    # ===== まとめ
    summary = f"""
    <h3>🧠 まとめ</h3>
    <div>{_summary(ai_summary)}</div>
    """

    # ===== スコア（アイコン追加）
    score_block = f"""
    <h3>📊 スコア</h3>
    {score} ({regime})<br>
    {signal}
    """

    # ===== HTML
    return f"""
    <html>
    <body style="font-family:Arial;max-width:960px;margin:auto">

    <h2>Daily Market Report ({today})</h2>

    {major}
    {rate}
    <p><b>10Y-2Y:</b> {spread}</p>

    {fx}
    {com}
    {crypto}

    {breadth_tbl}
    {sector_tbl}

    {econ_y}
    {econ_t}

    {summary}
    {score_block}

    </body>
    </html>
    """
