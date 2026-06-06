from utils.datetime_utils import now_jst


# ============================
# フォーマット
# ============================
def nl2br(text):
    if not text:
        return ""
    return str(text).replace("\n", "<br>")


def _fmt_num(v):
    try:
        return f"{float(v):.2f}"
    except:
        return "N/A"


def _fmt_pct(v):
    try:
        return f"{float(v):.1f}%"
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
        return "N/A", "N/A"
    return _fmt_num(r.get("value")), r.get("change_text", "N/A")


# ============================
# HTML生成（最終版）
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

    # ========= 市場 =========
    sp_v, sp_c = _val("S&P500", market_rows)
    nd_v, nd_c = _val("NASDAQ", market_rows)
    dow_v, dow_c = _val("NYダウ", market_rows)
    rut_v, rut_c = _val("Russell2000", market_rows)
    nik_v, nik_c = _val("日経平均", market_rows)

    # ========= ボラ =========
    vix_v, vix_c = _val("VIX", market_rows)

    # ========= 金利 =========
    y10_v, y10_c = _val("米10年金利", market_rows)
    y2_v = _fmt_num(rate_extras.get("米2年債利回り"))

    # ========= 為替 =========
    dxy_v, dxy_c = _val("DXY", market_rows)
    uj_v, uj_c = _val("USD/JPY", market_rows)
    eu_v, eu_c = _val("EUR/USD", market_rows)

    # ========= コモディティ =========
    oil_v, oil_c = _val("WTI原油", market_rows)
    gold_v, gold_c = _val("ゴールド", market_rows)
    cop_v, cop_c = _val("銅", market_rows)

    # ========= Breadth =========
    ratio_txt = _fmt_pct(breadth.get("ratio"))
    state = breadth.get("state")

    # ========= セクター分析 =========
    sector_html = "<br>".join(
        f"{r['label']} {r['change_text']}"
        for r in sector_rows
    )

    # ========= HTML =========
    html = f"""
    <html>
    <body style="font-family:Arial; line-height:1.7;">

    <h2>📊 Daily Market Checklist ({today})</h2>

    <h3>① マーケット</h3>
    S&P500 {sp_v} ({sp_c})<br>
    NASDAQ {nd_v} ({nd_c})<br>
    Dow {dow_v} ({dow_c})<br>
    Russell {rut_v} ({rut_c})<br>
    日経 {nik_v} ({nik_c})

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
    銅 {cop_v} ({cop_c})

    <h3>📈 ⑥ Market Breadth</h3>
    上昇銘柄比率: <b>{ratio_txt}</b><br>
    👉 状態: <b>{state}</b>

    <h3>📊 ⑦ セクター別分析</h3>
    {sector_html}

    <h3>💰 ⑧ ETFフロー</h3>
    SPY / QQQ / IWM: {etf_flows.get("SPY")} / {etf_flows.get("QQQ")} / {etf_flows.get("IWM")}<br>
    👉 解釈: {etf_flows.get("interpretation")}

    <h3>😨 ⑨ Options</h3>
    Put/Call: {options_data.get("put_call")}<br>
    👉 {options_data.get("notable")}<br>
    👉 センチメント: {options_data.get("sentiment")}

    <h3>🧠 ⑩ AIサマリー</h3>
    {nl2br(ai_summary)}

    <h3>📊 スコア</h3>
    {score} ({regime})<br>
    シグナル: {signal}

    </body>
    </html>
    """

    return html
