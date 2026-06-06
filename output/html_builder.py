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


def _color_change(text):
    if not text:
        return ""

    s = str(text)
    if s.startswith("+"):
        return f'<span style="color:green">{s}</span>'
    elif s.startswith("-"):
        return f'<span style="color:red">{s}</span>'
    return s


def _warn(text):
    return f'<span style="color:red; font-weight:bold;">{text}</span>'


def _row(name, value, change):
    return f"""
    <tr>
      <td>{name}</td>
      <td style="text-align:right;">{_fmt_num(value) if value != "" else ""}</td>
      <td style="text-align:right;">{_color_change(change)}</td>
    </tr>
    """


def _simple_row(name, v1, v2=None):
    if v2 is None:
        return f"""
        <tr>
          <td>{name}</td>
          <td style="text-align:right;">{v1}</td>
        </tr>
        """
    return f"""
    <tr>
      <td>{name}</td>
      <td style="text-align:right;">{v1}</td>
      <td style="text-align:right;">{v2}</td>
    </tr>
    """


def _table(title, header_html, body_html):
    return f"""
    <h3>{title}</h3>
    <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse; width:100%;">
      {header_html}
      {body_html}
    </table>
    """


def _event_rows(events):
    rows = ""
    for e in events or []:
        rows += f"""
        <tr>
          <td>{e.get("country")}</td>
          <td>{e.get("event_name")}</td>
          <td style="text-align:right;">{e.get("forecast")}</td>
          <td style="text-align:right;">{e.get("actual")}</td>
          <td style="text-align:right;">{e.get("previous")}</td>
          <td>{e.get("event_status")}</td>
        </tr>
        """
    if not rows:
        rows = """
        <tr>
          <td colspan="6">なし</td>
        </tr>
        """
    return rows


# =========================
# HTML
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
    major_body = ""
    for label in ["S&P500", "NASDAQ", "NYダウ", "Russell2000", "日経平均"]:
        v, c = _val(label, market_rows)
        major_body += _row(label, v, c)

    major_table = _table(
        "主要指数",
        "<tr><th>項目</th><th>値</th><th>前日比</th></tr>",
        major_body
    )

    # ===== 金利 =====
    y10, y10c = _val("米10年金利", market_rows)

    y2 = rate_extras.get("米2年債利回り")
    y2_change = rate_extras.get("米2年債利回り_前日比_pct")

    try:
        y2_change_text = f"{y2_change:+.2f}%"
    except Exception:
        y2_change_text = ""

    try:
        spread = float(y10) - float(y2)
        spread_text = f"{spread:.2f}"
        spread_html = _warn(spread_text) if spread < 0 else spread_text
    except Exception:
        spread_html = "N/A"

    rate_body = ""
    rate_body += _row("米10年債利回り", y10, y10c)
    rate_body += _row("米2年債利回り", y2, y2_change_text)

    rate_table = _table(
        "金利",
        "<tr><th>項目</th><th>値</th><th>前日比</th></tr>",
        rate_body
    )

    rate_comment = f"""
    <p><b>10年債利回り - 2年債利回り:</b> {spread_html}</p>
    """

    # ===== 為替 =====
    fx_body = ""
    for label in ["DXY", "USD/JPY", "EUR/USD"]:
        v, c = _val(label, market_rows)
        fx_body += _row(label, v, c)

    fx_table = _table(
        "為替",
        "<tr><th>項目</th><th>値</th><th>前日比</th></tr>",
        fx_body
    )

    # ===== コモディティ =====
    com_body = ""
    for label in ["WTI原油", "ゴールド", "銅"]:
        v, c = _val(label, market_rows)
        com_body += _row(label, v, c)

    commodity_table = _table(
        "コモディティ",
        "<tr><th>項目</th><th>値</th><th>前日比</th></tr>",
        com_body
    )

    # ===== 仮想通貨 =====
    crypto_body = ""
    for label in ["BTC (USD)", "ETH (USD)", "XRP (USD)", "SOL (USD)"]:
        v, c = _val(label, market_rows)
        crypto_body += _row(label, v, c)

    crypto_table = _table(
        "仮想通貨",
        "<tr><th>項目</th><th>値</th><th>前日比</th></tr>",
        crypto_body
    )

    # ===== ETF =====
    etf_body = ""
    etf_body += _row("SPY", "", etf_flows.get("SPY"))
    etf_body += _row("QQQ", "", etf_flows.get("QQQ"))
    etf_body += _row("IWM", "", etf_flows.get("IWM"))

    etf_table = _table(
        "ETFフロー",
        "<tr><th>項目</th><th>値</th><th>前日比</th></tr>",
        etf_body
    )

    etf_comment = f"""
    <p><b>市場傾向の解釈:</b> {etf_flows.get("interpretation")}</p>
    """

    # ===== Options =====
    options_body = ""
    options_body += _simple_row("Put/Call", _fmt_num(options_data.get("put_call")))

    options_table = _table(
        "オプション",
        "<tr><th>指標</th><th>値</th></tr>",
        options_body
    )

    options_comment = f"""
    <p><b>センチメント:</b> {options_data.get("sentiment")}</p>
    """

    # ===== Breadth =====
    ratio = breadth.get("ratio")
    ratio_text = _fmt_pct(ratio)
    if ratio is not None and ratio <= 30:
        ratio_text = _warn(ratio_text)

    breadth_body = f"""
    <tr><td>上昇銘柄比率</td><td style="text-align:right;">{ratio_text}</td></tr>
    <tr><td>状態</td><td style="text-align:right;">{breadth.get("state")}</td></tr>
    """

    breadth_table = _table(
        "市場の広がり",
        "<tr><th>指標</th><th>値</th></tr>",
        breadth_body
    )

    # ===== セクター =====
    sector_body = ""
    for r in sector_rows:
        sector_body += f"""
        <tr>
          <td>{r['label']}</td>
          <td style="text-align:right;">{_color_change(r['change_text'])}</td>
        </tr>
        """

    sector_table = _table(
        "セクター",
        "<tr><th>セクター</th><th>前日比</th></tr>",
        sector_body
    )

    # ===== 経済指標（昨日 / 本日）=====
    yesterday_table = _table(
        "経済指標（昨日）",
        "<tr><th>国</th><th>指標</th><th>予想</th><th>結果</th><th>前回</th><th>区分</th></tr>",
        _event_rows(macro_payload.get("yesterday_events", []))
    )

    today_table = _table(
        "経済指標（本日）",
        "<tr><th>国</th><th>指標</th><th>予想</th><th>結果</th><th>前回</th><th>区分</th></tr>",
        _event_rows(macro_payload.get("today_events", []))
    )

    # ===== AI =====
    summary_html = ai_summary.replace("\n", "<br>")

    html = f"""
    <html>
    <body style="font-family:Arial; line-height:1.7;">

    <h2>Daily Market Report ({today})</h2>

    {major_table}
    {rate_table}
    {rate_comment}
    {fx_table}
    {commodity_table}
    {crypto_table}
    {etf_table}
    {etf_comment}
    {options_table}
    {options_comment}
    {breadth_table}
    {sector_table}
    {yesterday_table}
    {today_table}

    <h3>AIサマリー</h3>
    {summary_html}

    <h3>スコア</h3>
    {score} ({regime})<br>
    {signal}

    </body>
    </html>
    """

    return html
