from utils.datetime_utils import now_jst


# ============================
# 基本フォーマット
# ============================
def nl2br(text):
    if not text:
        return ""
    return str(text).replace("\n", "<br>")


def _fmt_num(v):
    try:
        return f"{float(v):.2f}"
    except Exception:
        return "N/A"


def _fmt_pct(v):
    try:
        return f"{float(v):.1f}%"
    except Exception:
        return "N/A"


def _fmt_opt(v):
    if v in [None, "", "None"]:
        return "未取得"
    return str(v)


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

    s = str(text)
    if s.startswith("+"):
        return f'<span style="color:#0a8f2a; font-weight:600;">{s}</span>'
    elif s.startswith("-"):
        return f'<span style="color:#c62828; font-weight:600;">{s}</span>'
    return s


def _colorize_state(text):
    if not text:
        return "未取得"

    s = str(text)

    if "強気" in s or "上昇" in s or "流入" in s:
        return f'<span style="color:#0a8f2a; font-weight:700;">{s}</span>'

    if "弱気" in s or "下落" in s or "流出" in s or "警戒" in s:
        return f'<span style="color:#c62828; font-weight:700;">{s}</span>'

    return f"<b>{s}</b>"


# ============================
# 表レンダリング
# ============================
def _build_table(title, rows_html):
    return f"""
    <div style="margin: 16px 0 24px 0;">
        <div style="font-weight:700; margin-bottom:8px;">{title}</div>
        <table style="border-collapse:collapse; width:100%; font-size:14px;">
            <thead>
                <tr style="background:#f3f4f6;">
                    <th style="text-align:left; padding:8px; border:1px solid #e5e7eb;">項目</th>
                    <th style="text-align:right; padding:8px; border:1px solid #e5e7eb;">値</th>
                    <th style="text-align:right; padding:8px; border:1px solid #e5e7eb;">前日比</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
    """


def _market_row(label, value, change):
    return f"""
    <tr>
        <td style="padding:8px; border:1px solid #e5e7eb;">{label}</td>
        <td style="padding:8px; border:1px solid #e5e7eb; text-align:right;">{value}</td>
        <td style="padding:8px; border:1px solid #e5e7eb; text-align:right;">{_colorize_change(change)}</td>
    </tr>
    """


def _build_sector_table(sector_rows):
    rows_html = ""
    for r in sector_rows:
        rows_html += _market_row(
            r.get("label", ""),
            "",
            r.get("change_text", "N/A"),
        )

    return f"""
    <div style="margin: 16px 0 24px 0;">
        <div style="font-weight:700; margin-bottom:8px;">セクター別分析</div>
        <table style="border-collapse:collapse; width:100%; font-size:14px;">
            <thead>
                <tr style="background:#f3f4f6;">
                    <th style="text-align:left; padding:8px; border:1px solid #e5e7eb;">セクター</th>
                    <th style="text-align:right; padding:8px; border:1px solid #e5e7eb;">前日比</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
    """


def _country_name(country):
    if country == "JP":
        return "日本"
    if country == "US":
        return "米国"
    return str(country or "")


def _event_table(title, events):
    rows = ""

    for e in events or []:
        dt = e.get("event_dt_jst")
        time_str = dt.strftime("%m/%d %H:%M") if dt else "未定"

        rows += f"""
        <tr>
            <td style="padding:8px; border:1px solid #e5e7eb;">{_country_name(e.get("country"))}</td>
            <td style="padding:8px; border:1px solid #e5e7eb;">{time_str}</td>
            <td style="padding:8px; border:1px solid #e5e7eb;">{_fmt_opt(e.get("event_name"))}</td>
            <td style="padding:8px; border:1px solid #e5e7eb; text-align:right;">{_fmt_opt(e.get("forecast"))}</td>
            <td style="padding:8px; border:1px solid #e5e7eb; text-align:right;">{_fmt_opt(e.get("actual"))}</td>
            <td style="padding:8px; border:1px solid #e5e7eb; text-align:right;">{_fmt_opt(e.get("previous"))}</td>
            <td style="padding:8px; border:1px solid #e5e7eb;">{_fmt_opt(e.get("event_status"))}</td>
        </tr>
        """

    if not rows:
        rows = """
        <tr>
            <td colspan="7" style="padding:8px; border:1px solid #e5e7eb;">なし</td>
        </tr>
        """

    return f"""
    <div style="margin: 16px 0 24px 0;">
        <div style="font-weight:700; margin-bottom:8px;">{title}</div>
        <table style="border-collapse:collapse; width:100%; font-size:14px;">
            <thead>
                <tr style="background:#f3f4f6;">
                    <th style="text-align:left; padding:8px; border:1px solid #e5e7eb;">国</th>
                    <th style="text-align:left; padding:8px; border:1px solid #e5e7eb;">時刻</th>
                    <th style="text-align:left; padding:8px; border:1px solid #e5e7eb;">指標</th>
                    <th style="text-align:right; padding:8px; border:1px solid #e5e7eb;">予想</th>
                    <th style="text-align:right; padding:8px; border:1px solid #e5e7eb;">結果</th>
                    <th style="text-align:right; padding:8px; border:1px solid #e5e7eb;">前回</th>
                    <th style="text-align:left; padding:8px; border:1px solid #e5e7eb;">区分</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
    </div>
    """


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

    # ========= マーケット =========
    nik_v, nik_c = _val("日経平均", market_rows)
    dow_v, dow_c = _val("NYダウ", market_rows)
    nd_v, nd_c = _val("NASDAQ", market_rows)
    sp_v, sp_c = _val("S&P500", market_rows)
    vix_v, vix_c = _val("VIX", market_rows)
    y10_v, y10_c = _val("米10年金利", market_rows)
    gold_v, gold_c = _val("ゴールド", market_rows)
    btc_v, btc_c = _val("BTC (USD)", market_rows)
    uj_v, uj_c = _val("USD/JPY", market_rows)

    market_rows_html = ""
    market_rows_html += _market_row("日経平均", nik_v, nik_c)
    market_rows_html += _market_row("NYダウ", dow_v, dow_c)
    market_rows_html += _market_row("NASDAQ", nd_v, nd_c)
    market_rows_html += _market_row("S&P500", sp_v, sp_c)
    market_rows_html += _market_row("VIX", vix_v, vix_c)
    market_rows_html += _market_row("米10年金利", y10_v, y10_c)
    market_rows_html += _market_row("GOLD (USD)", gold_v, gold_c)
    market_rows_html += _market_row("BTC (USD)", btc_v, btc_c)
    market_rows_html += _market_row("USD/JPY", uj_v, uj_c)

    market_section = _build_table("マーケット", market_rows_html)

    # ========= 仮想通貨 =========
    eth_v, eth_c = _val("ETH (USD)", market_rows)
    xrp_v, xrp_c = _val("XRP (USD)", market_rows)
    sol_v, sol_c = _val("SOL (USD)", market_rows)

    crypto_rows_html = ""
    crypto_rows_html += _market_row("BTC (USD)", btc_v, btc_c)
    crypto_rows_html += _market_row("ETH (USD)", eth_v, eth_c)
    crypto_rows_html += _market_row("XRP (USD)", xrp_v, xrp_c)
    crypto_rows_html += _market_row("SOL (USD)", sol_v, sol_c)

    crypto_section = _build_table("仮想通貨", crypto_rows_html)

    # ========= 為替 / 金利 / コモディティ（必要なら個別表示も維持） =========
    dxy_v, dxy_c = _val("DXY", market_rows)
    eu_v, eu_c = _val("EUR/USD", market_rows)
    oil_v, oil_c = _val("WTI原油", market_rows)
    cop_v, cop_c = _val("銅", market_rows)
    y2_v = _fmt_num(rate_extras.get("米2年債利回り"))

    extra_rows_html = ""
    extra_rows_html += _market_row("DXY", dxy_v, dxy_c)
    extra_rows_html += _market_row("EUR/USD", eu_v, eu_c)
    extra_rows_html += _market_row("WTI原油", oil_v, oil_c)
    extra_rows_html += _market_row("銅", cop_v, cop_c)
    extra_rows_html += _market_row("米2年債利回り", y2_v, "")

    extra_section = _build_table("追加指標", extra_rows_html)

    # ========= Market Breadth =========
    ratio_txt = _fmt_pct(breadth.get("ratio"))
    breadth_state = _colorize_state(breadth.get("state"))

    breadth_section = f"""
    <div style="margin: 16px 0 24px 0;">
        <div style="font-weight:700; margin-bottom:8px;">Market Breadth</div>
        上昇銘柄比率: <b>{ratio_txt}</b><br>
        👉 状態: {breadth_state}
    </div>
    """

    # ========= セクター別分析 =========
    sector_section = _build_sector_table(sector_rows)

    # ========= ETF =========
    spy = _colorize_change(etf_flows.get("SPY"))
    qqq = _colorize_change(etf_flows.get("QQQ"))
    iwm = _colorize_change(etf_flows.get("IWM"))
    etf_state = _colorize_state(etf_flows.get("interpretation"))

    etf_section = f"""
    <div style="margin: 16px 0 24px 0;">
        <div style="font-weight:700; margin-bottom:8px;">ETFフロー</div>
        SPY / QQQ / IWM: {spy} / {qqq} / {iwm}<br>
        👉 解釈: {etf_state}
    </div>
    """

    # ========= Options =========
    pcr = options_data.get("put_call")
    notable = options_data.get("notable")
    options_state = _colorize_state(options_data.get("sentiment"))

    options_section = f"""
    <div style="margin: 16px 0 24px 0;">
        <div style="font-weight:700; margin-bottom:8px;">Options</div>
        Put/Call: {_fmt_num(pcr)}<br>
        👉 {_fmt_opt(notable)}<br>
        👉 センチメント: {options_state}
    </div>
    """

    # ========= 経済指標 =========
    y_events = macro_payload.get("yesterday_events", [])
    t_events = macro_payload.get("today_events", [])

    econ_yesterday_section = _event_table("経済指標（前回結果）", y_events)
    econ_today_section = _event_table("経済指標（本日予定 / 結果）", t_events)

    # ========= スコア / シグナル =========
    regime_html = _colorize_state(regime)
    signal_html = _colorize_state(signal)

    score_section = f"""
    <div style="margin: 16px 0 24px 0;">
        <div style="font-weight:700; margin-bottom:8px;">スコア</div>
        {score} ({regime_html})<br>
        シグナル: {signal_html}
    </div>
    """

    # ========= AIサマリー =========
    ai_section = f"""
    <div style="margin: 16px 0 24px 0;">
        <div style="font-weight:700; margin-bottom:8px;">AIサマリー</div>
        <div style="background:#f8f9fb; padding:12px; border-radius:8px;">
            {nl2br(ai_summary)}
        </div>
    </div>
    """

    html = f"""
    <html>
    <body style="font-family:Arial, sans-serif; line-height:1.7; color:#222; max-width:900px; margin:20px auto;">

    {market_section}

    {crypto_section}

    {extra_section}

    {breadth_section}

    {sector_section}

    {etf_section}

    {options_section}

    {econ_yesterday_section}

    {econ_today_section}

    {ai_section}

    {score_section}

    </body>
    </html>
    """

    return html
