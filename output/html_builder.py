from utils.datetime_utils import now_jst


# ============================
# format
"""# ============================
    <tr>
      <td>{name}</td>
      <td style="text-align:right;">{value}</td>
      <td style="text-align:right;">{_color(change)}</td>
    </tr>
    """


# ============================
# HTML
# ============================
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

    # ========= MARKET =========
    data = ""

    # 指数
    for label in ["S&P500", "NASDAQ", "NYダウ", "Russell2000", "日経平均"]:
        v, c, _ = _val(label, market_rows)
        data += _row(label, v, c)

    # VIX
    v, c, _ = _val("VIX", market_rows)
    data += _row("VIX", v, c)

    # 金利
    y10, y10c, _ = _val("米10年金利", market_rows)
    y2 = rate_extras.get("米2年債利回り")
    y2c = ""  # 必要なら追加

    # ✅ スプレッド
    try:
        spread = float(y10) - float(y2)
        spread = f"{spread:.2f}"
    except:
        spread = "N/A"

    data += _row("米10年債利回り", y10, y10c)
    data += _row("米2年債利回り", _fmt_num(y2), "")
    data += _row("10Y-2Y", spread, "")

    # 為替
    for label in ["DXY", "USD/JPY", "EUR/USD"]:
        v, c, _ = _val(label, market_rows)
        data += _row(label, v, c)

    # コモディティ
    for label in ["WTI原油", "ゴールド", "銅"]:
        v, c, _ = _val(label, market_rows)
        data += _row(label, v, c)

    # 仮想通貨
    for label in ["BTC (USD)", "ETH (USD)", "XRP (USD)", "SOL (USD)"]:
        v, c, _ = _val(label, market_rows)
        data += _row(label, v, c)

    # ETF
    data += _row("SPY", "", etf_flows.get("SPY"))
    data += _row("QQQ", "", etf_flows.get("QQQ"))
    data += _row("IWM", "", etf_flows.get("IWM"))

    market_table = f"""
    <h3>マーケット</h3>
    <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;">
      <tr>
        <th>項目</th>
        <th>値</th>
        <th>前日比</th>
      </tr>
      {data}
    </table>
    """

    # ========= BREADTH =========
    breadth_table = f"""
    <h3>市場の広がり（騰落の強さ）</h3>
    <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;">
      <tr>
        <th>上昇銘柄比率</th>
        <th>状態</th>
      </tr>
      <tr>
        <td>{_fmt_pct(breadth.get("ratio"))}</td>
        <td>{breadth.get("state")}</td>
      </tr>
    </table>
    """

    # ========= SECTOR =========
    sector_rows_html = ""
    for r in sector_rows:
        sector_rows_html += f"""
        <tr>
          <td>{r['label']}</td>
          <td style="text-align:right;">{_color(r['change_text'])}</td>
        </tr>
        """

    sector_table = f"""
    <h3>セクター</h3>
    <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;">
      <tr>
        <th>セクター</th>
        <th>前日比</th>
      </tr>
      {sector_rows_html}
    </table>
    """

    # ========= ECONOMIC =========
    econ_rows = ""
    for e in (macro_payload.get("yesterday_events", []) + macro_payload.get("today_events", [])):
        econ_rows += f"""
        <tr>
          <td>{e.get("country")}</td>
          <td>{e.get("event_name")}</td>
          <td>{e.get("forecast")}</td>
          <td>{e.get("actual")}</td>
          <td>{e.get("previous")}</td>
        </tr>
        """

    econ_table = f"""
    <h3>経済指標</h3>
    <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;">
      <tr>
        <th>国</th>
        <th>指標</th>
        <th>予想</th>
        <th>結果</th>
        <th>前回</th>
      </tr>
      {econ_rows}
    </table>
    """

    # ========= AI =========
    summary = ai_summary.replace("\n", "<br>")

    html = f"""
    <html>
    <body>

    <h2>Daily Market Report ({today})</h2>

    {market_table}
    {breadth_table}
    {sector_table}
    {econ_table}

    <h3>AIサマリー</h3>
    {summary}

    <h3>スコア</h3>
    {score} ({regime})<br>
    シグナル: {signal}

    </body>
    </html>
    """

    return html
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
        return None, None, None

    return (
        _fmt_num(r.get("value")),
        r.get("change_text"),
        r.get("change_pct")
    )


def _color(text):
    if not text:
        return ""

    if str(text).startswith("+"):
        return f'<span style="color:green">{text}</span>'
    elif str(text).startswith("-"):
        return f'<span style="color:red">{text}</span>'

    return text


def _row(name, value, change):
