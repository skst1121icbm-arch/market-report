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


def _row(name, value, change):
    return f"""
    <tr>
      <td>{name}</td>
      <td style="text-align:right;">{_fmt_num(value)}</td>
      <td style="text-align:right;">{_color(change)}</td>
    </tr>
    """


def _simple_row(name, value):
    return f"""
    <tr>
      <td>{name}</td>
      <td style="text-align:right;">{value}</td>
    </tr>
    """


def _table(title, header, body):
    return f"""
    <h3>{title}</h3>
    <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;">
      {header}
      {body}
    </table>
    """


# =========================
# main HTML
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

    # ===== 主要指数 =====
    body = ""
    for label in ["S&P500", "NASDAQ", "NYダウ", "Russell2000", "日経平均"]:
        v, c = _val(label, market_rows)
        body += _row(label, v, c)

    major = _table(
        "主要指数",
        "<tr><th>項目</th><th>値</th><th>前日比</th></tr>",
        body
    )

    # ===== 金利 =====
    y10, y10c = _val("米10年金利", market_rows)
    y2 = rate_extras.get("米2年債利回り")

    try:
        spread = float(y10) - float(y2)
        spread_text = f"{spread:.2f}"
    except:
        spread_text = "N/A"

    body = ""
    body += _row("米10年債利回り", y10, y10c)
    body += _row("米2年債利回り", y2, "")

    rate_table = _table(
        "金利",
        "<tr><th>項目</th><th>値</th><th>前日比</th></tr>",
        body
    )

    rate_comment = f"""
    <p><b>10年債利回り - 2年債利回り:</b> {spread_text}</p>
    """

    # ===== 為替 =====
    body = ""
    for l in ["DXY", "USD/JPY", "EUR/USD"]:
        v, c = _val(l, market_rows)
        body += _row(l, v, c)

    fx = _table(
        "為替",
        "<tr><th>項目</th><th>値</th><th>前日比</th></tr>",
        body
    )

    # ===== コモディティ =====
    body = ""
    for l in ["WTI原油", "ゴールド", "銅"]:
        v, c = _val(l, market_rows)
        body += _row(l, v, c)

    commodity = _table(
        "コモディティ",
        "<tr><th>項目</th><th>値</th><th>前日比</th></tr>",
        body
    )

    # ===== 仮想通貨 =====
    body = ""
    for l in ["BTC (USD)", "ETH (USD)", "XRP (USD)", "SOL (USD)"]:
        v, c = _val(l, market_rows)
        body += _row(l, v, c)

    crypto = _table(
        "仮想通貨",
        "<tr><th>項目</th><th>値</th><th>前日比</th></tr>",
        body
    )

    # ===== ETF =====
    body = ""
    body += _row("SPY", "", etf_flows.get("SPY"))
    body += _row("QQQ", "", etf_flows.get("QQQ"))
    body += _row("IWM", "", etf_flows.get("IWM"))

    etf_table = _table(
        "ETFフロー",
        "<tr><th>銘柄</th><th>値</th><th>前日比</th></tr>",
        body
    )

    etf_comment = f"""
    <p><b>市場傾向の解釈:</b> {etf_flows.get("interpretation")}</p>
    """

    # ===== Options =====
    body = ""
    body += _simple_row("Put/Call", options_data.get("put_call"))

    options_table = _table(
        "オプション",
        "<tr><th>指標</th><th>値</th></tr>",
        body
    )

    options_comment = f"""
    <p><b>センチメント:</b> {options_data.get("sentiment")}</p>
    """

    # ===== Breadth =====
    breadth_table = _table(
        "市場の広がり",
        "<tr><th>指標</th><th>値</th></tr>",
        f"""
        <tr><td>上昇銘柄比率</td><td>{_fmt_pct(breadth.get("ratio"))}</td></tr>
        <tr><td>状態</td><td>{breadth.get("state")}</td></tr>
        """
    )

    # ===== セクター =====
    body = ""
    for r in sector_rows:
        body += f"""
        <tr>
          <td>{r['label']}</td>
          <td style="text-align:right;">{_color(r['change_text'])}</td>
        </tr>
        """

    sector_table = _table(
        "セクター",
        "<tr><th>セクター</th><th>前日比</th></tr>",
        body
    )

    # ===== HTML =====
    html = f"""
    <html>
    <body>

    <h2>Daily Market Report</h2>

    {major}
    {rate_table}
    {rate_comment}
    {fx}
    {commodity}
    {crypto}
    {etf_table}
    {etf_comment}
    {options_table}
    {options_comment}
    {breadth_table}
    {sector_table}

    <h3>AIサマリー</h3>
    {ai_summary.replace("\n","<br>")}

    <h3>スコア</h3>
    {score} ({regime})<br>
    {signal}

    </body>
    </html>
    """

    return html
