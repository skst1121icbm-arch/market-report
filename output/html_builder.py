from utils.datetime_utils import now_jstfrom utils.datetime_utils import now_j        return ""
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
# 色付け
# ============================
def _colorize_change(text):
    if not text or text == "N/A":
        return text

    if str(text).startswith("+"):
        return f'<span style="color:#0a8f2a;"><b>{text}</b></span>'
    elif str(text).startswith("-"):
        return f'<span style="color:#c62828;"><b>{text}</b></span>'
    return text


def _colorize_state(text):
    if not text:
        return "未取得"

    s = str(text)

    if "強気" in s or "上昇" in s or "流入" in s:
        return f'<span style="color:#0a8f2a;"><b>{s}</b></span>'

    if "弱気" in s or "下落" in s or "流出" in s or "警戒" in s:
        return f'<span style="color:#c62828;"><b>{s}</b></span>'

    return f"<b>{s}</b>"


def _build_sector_html(sector_rows):
    lines = []
    for r in sector_rows:
        label = r.get("label", "")
        change = _colorize_change(r.get("change_text", "N/A"))
        lines.append(f"{label} {change}")
    return "<br>".join(lines)


# ============================
# HTML生成
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

    # ========= Market Breadth =========
    ratio_txt = _fmt_pct(breadth.get("ratio"))
    breadth_state = _colorize_state(breadth.get("state"))

    # ========= セクター =========
    sector_html = _build_sector_html(sector_rows)

    # ========= ETF =========
    spy = _colorize_change(etf_flows.get("SPY"))
    qqq = _colorize_change(etf_flows.get("QQQ"))
    iwm = _colorize_change(etf_flows.get("IWM"))
    etf_state = _colorize_state(etf_flows.get("interpretation"))

    # ========= Options =========
    pcr = options_data.get("put_call")
    notable = options_data.get("notable")
    options_state = _colorize_state(options_data.get("sentiment"))

    # ========= スコア周辺 =========
    regime_html = _colorize_state(regime)
    signal_html = _colorize_state(signal)

    html = f"""
    <html>
    <body style="font-family:Arial, sans-serif; line-height:1.7; color:#222;">

    <h2>📊 Daily Market Checklist ({today})</h2>

    <h3>① マーケット</h3>
    S&amp;P500 {sp_v} ({_colorize_change(sp_c)})<br>
    NASDAQ {nd_v} ({_colorize_change(nd_c)})<br>
    Dow {dow_v} ({_colorize_change(dow_c)})<br>
    Russell {rut_v} ({_colorize_change(rut_c)})<br>
    日経 {nik_v} ({_colorize_change(nik_c)})

    <h3>② ボラティリティ</h3>
    VIX {vix_v} ({_colorize_change(vix_c)})

    <h3>③ 金利</h3>
    10Y {y10_v} ({_colorize_change(y10_c)})<br>
    2Y {y2_v}

    <h3>④ 為替</h3>
    DXY {dxy_v} ({_colorize_change(dxy_c)})<br>
    USDJPY {uj_v} ({_colorize_change(uj_c)})<br>
    EURUSD {eu_v} ({_colorize_change(eu_c)})

    <h3>⑤ コモディティ</h3>
    原油 {oil_v} ({_colorize_change(oil_c)})<br>
    ゴールド {gold_v} ({_colorize_change(gold_c)})<br>
    銅 {cop_v} ({_colorize_change(cop_c)})

    <h3>📈 ⑥ Market Breadth</h3>
    上昇銘柄比率: <b>{ratio_txt}</b><br>
    👉 状態: {breadth_state}

    <h3>📊 ⑦ セクター別分析</h3>
    {sector_html}

    <h3>💰 ⑧ ETFフロー</h3>
    SPY / QQQ / IWM: {spy} / {qqq} / {iwm}<br>
    👉 解釈: {etf_state}

    <h3>😨 ⑨ Options</h3>
    Put/Call: {_fmt_num(pcr)}<br>
    👉 {notable}<br>
    👉 センチメント: {options_state}

    <h3>🧠 ⑩ AIサマリー</h3>
    <div style="background:#f8f9fb; padding:12px; border-radius:8px;">
        {nl2br(ai_summary)}
    </div>

    <h3>📊 スコア</h3>
    {score} ({regime_html})<br>
    シグナル: {signal_html}

    </body>
    </html>
    """

    return html


# ============================
# 基本フォーマット
# ============================
def nl2br(text):
    if not text:
