from utils.datetime_utils import now_jstfrom utils.datetime_utils import now_j:
        return ""
    return str(text).replace("\n", "<br>")


def _fmt(v):
    try:
        return f"{float(v):.2f}"
    except:
        return "N/A"


def _find(label, rows):
    for r in rows:
        if r["label"] == label:
            return r
    return None


def _val_text(label, rows):
    r = _find(label, rows)
    if not r:
        return "N/A", "N/A"
    return _fmt(r.get("value")), r.get("change_text", "N/A")


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
    themes,
    rate_extras,
):

    today = now_jst().strftime("%Y-%m-%d")

    # マーケット
    sp_v, sp_c = _val_text("S&P500", market_rows)
    nd_v, nd_c = _val_text("NASDAQ", market_rows)
    dow_v, dow_c = _val_text("NYダウ", market_rows)
    rut_v, rut_c = _val_text("Russell2000", market_rows)
    nikkei_v, nikkei_c = _val_text("日経平均", market_rows)

    # ボラ
    vix_v, vix_c = _val_text("VIX", market_rows)

    # 金利
    y10_v, y10_c = _val_text("米10年金利", market_rows)
    y2_v = _fmt(rate_extras.get("米2年債利回り"))

    # 為替
    dxy_v, dxy_c = _val_text("DXY", market_rows)
    uj_v, uj_c = _val_text("USD/JPY", market_rows)
    eu_v, eu_c = _val_text("EUR/USD", market_rows)

    # コモディティ
    oil_v, oil_c = _val_text("WTI原油", market_rows)
    gold_v, gold_c = _val_text("ゴールド", market_rows)
    copper_v, copper_c = _val_text("銅", market_rows)

    html = f"""
    <html>
    <body>

    <h2>📊 Daily Market Checklist ({today})</h2>

    <h3>① マーケット</h3>
    S&P500 {sp_v} ({sp_c})<br>
    NASDAQ {nd_v} ({nd_c})<br>
    Dow {dow_v} ({dow_c})<br>
    Russell {rut_v} ({rut_c})<br>
    日経 {nikkei_v} ({nikkei_c})

    <h3>② ボラティリティ</h3>
    VIX {vix_v} ({vix_c})

    <h3>③ 金利</h3>
    10Y {y10_v} ({y10_c})<br>
    2Y {y2_v}

    <h3>④ 為替</h3>
    DXY {dxy_v} ({dxy_c})<br>
    USDJPY {uj_v} ({uj_c})<br>
    EURUSD {eu_v} ({eu_c})

    <h3>⑤ コモディティ</h3>
    原油 {oil_v} ({oil_c})<br>
    ゴールド {gold_v} ({gold_c})<br>
    銅 {copper_v} ({copper_c})

    <h3>⑥ Breadth</h3>
    {breadth}

    <h3>⑦ ETF</h3>
    {etf_flows}

    <h3>⑧ Options</h3>
    {options_data}

    <h3>⑨ テーマ</h3>
    {themes}

    <h3>⑩ AI</h3>
    {nl2br(ai_summary)}

    <h3>スコア</h3>
    {score} ({regime})

    </body>
    </html>
    """

    return html


def nl2br(text):
