from utils.datetime_utils import now_jst


 = _value_and_change("NYダウ", market_rows)def nl2br(text):
    rut_v, rut_c = _value_and_change("Russell2000", market_rows)
    nikkei_v, nikkei_c = _value_and_change("日経平均", market_rows)

    # 金利
    y10_v, y10_c = _value_and_change("米10年金利", market_rows)
    y2_val = rate_extras.get("米2年債利回り")
    y2_v = _fmt_num(y2_val)
    real10_v = _fmt_num(rate_extras.get("実質金利(10Y)"))

    try:
        spread_2s10s = float(y10_v) - float(y2_v)
        spread_2s10s_txt = f"{spread_2s10s:.2f}"
    except Exception:
        spread_2s10s_txt = "N/A"

    # 為替
    dxy_v, dxy_c = _value_and_change("DXY", market_rows)
    uj_v, uj_c = _value_and_change("USD/JPY", market_rows)
    eu_v, eu_c = _value_and_change("EUR/USD", market_rows)

    # ボラ
    vix_v, vix_c = _value_and_change("VIX", market_rows)

    # コモディティ
    oil_v, oil_c = _value_and_change("WTI原油", market_rows)
    gold_v, gold_c = _value_and_change("ゴールド", market_rows)
    copper_v, copper_c = _value_and_change("銅", market_rows)

    # セクター
    strong = [r["label"] for r in sector_rows if (r.get("change_pct") or 0) > 0]
    weak = [r["label"] for r in sector_rows if (r.get("change_pct") or 0) < 0]

    # 経済指標
    y_events = macro_payload.get("yesterday_events", [])
    t_events = macro_payload.get("today_events", [])

    # Breadth
    adv = _fmt_opt(breadth.get("adv"))
    dec = _fmt_opt(breadth.get("dec"))
    ratio = _fmt_opt(breadth.get("ratio"))
    nh = _fmt_opt(breadth.get("new_high"))
    nl = _fmt_opt(breadth.get("new_low"))
    breadth_state = _fmt_opt(breadth.get("state"))

    # ETF
    spy_flow = _fmt_opt(etf_flows.get("SPY"))
    qqq_flow = _fmt_opt(etf_flows.get("QQQ"))
    iwm_flow = _fmt_opt(etf_flows.get("IWM"))
    etf_interp = _fmt_opt(etf_flows.get("interpretation"))

    # Options
    put_call = _fmt_opt(options_data.get("put_call"))
    notable = _fmt_opt(options_data.get("notable"))
    opt_sent = _fmt_opt(options_data.get("sentiment"))

    html = f"""
    <html>
    <body style="font-family:Arial,sans-serif; line-height:1.7;">
        <h2>📊 Daily Market Checklist ({today})</h2>

        <h3>🕒 ① マーケット全体の方向性</h3>
        S&amp;P500: {sp_v} ({sp_c})<br>
        NASDAQ: {nd_v} ({nd_c})<br>
        Dow: {dow_v} ({dow_c})<br>
        Russell2000: {rut_v} ({rut_c})<br>
        日経平均: {nikkei_v} ({nikkei_c})<br><br>
        👉 一言まとめ: {signal}

        <h3>🏦 ② 金利・債券</h3>
        米10年債利回り: {y10_v} ({y10_c})<br>
        米2年債利回り: {y2_v}<br>
        長短金利差（2Y-10Y）: {spread_2s10s_txt}<br>
        実質金利（10Y）: {real10_v}

        <h3>💱 ③ 為替</h3>
        DXY: {dxy_v} ({dxy_c})<br>
        USD/JPY: {uj_v} ({uj_c})<br>
        EUR/USD: {eu_v} ({eu_c})

        <h3>😨 ④ ボラティリティ</h3>
        VIX: {vix_v} ({vix_c})

        <h3>🛢️ ⑤ コモディティ</h3>
        WTI原油: {oil_v} ({oil_c})<br>
        ゴールド: {gold_v} ({gold_c})<br>
        銅: {copper_v} ({copper_c})

        <h3>🧭 ⑥ セクター強弱</h3>
        強い: {", ".join(strong) if strong else "なし"}<br>
        弱い: {", ".join(weak) if weak else "なし"}

        <h3>📈 ⑦ 市場内部（Breadth）</h3>
        騰落銘柄数（Adv/Dec）: {adv} / {dec}<br>
        上昇銘柄比率: {ratio}<br>
        新高値 / 新安値: {nh} / {nl}<br>
        👉 状態: {breadth_state}

        <h3>💰 ⑧ 資金フロー・ポジショニング</h3>
        ETFフロー（SPY / QQQ / IWM）: {spy_flow} / {qqq_flow} / {iwm_flow}<br>
        Put/Callレシオ: {put_call}<br>
        目立つオプション動き: {notable}<br>
        👉 解釈: {etf_interp}<br>
        👉 オプションセンチメント: {opt_sent}

        <h3>🎯 ⑨ 注目テーマ</h3>
        {", ".join(themes) if themes else "なし"}

        <h3>🗓️ ⑩ 経済指標・イベント</h3>
        <b>昨日</b><br>
        {"<br>".join(_event_line(e) for e in y_events) if y_events else "なし"}<br><br>
        <b>今日</b><br>
        {"<br>".join(_event_line(e) for e in t_events) if t_events else "なし"}

        <h3>🧠 ⑪ AI総括</h3>
        <div>{nl2br(ai_summary)}</div>

        <h3>📊 ⑫ スコア / レジーム</h3>
        score: {score} / regime: {regime}

        <h3>📌 理由</h3>
        <div>{"<br>".join(reasons)}</div>
    </body>
    </html>
    """
    return html
    if not text:
        return ""
    return str(text).replace("\n", "<br>")


def _fmt_num(v):
    try:
        return f"{float(v):.2f}"
    except Exception:
        return "N/A"


def _fmt_opt(v):
    if v in [None, "", "None"]:
        return "未取得"
    return str(v)


def _find_row(label, rows):
    for r in rows:
        if r["label"] == label:
            return r
    return None


def _value_and_change(label, rows):
    r = _find_row(label, rows)
    if not r:
        return "N/A", "N/A"

    value = _fmt_num(r.get("value"))
    change_text = r.get("change_text", "N/A")
    return value, change_text


def _event_line(e):
    time_str = (
        e["event_dt_jst"].strftime("%m/%d %H:%M")
        if e.get("event_dt_jst")
        else "未定"
    )

    status = e.get("event_status", "")
    name = e.get("event_name", "")
    forecast = _fmt_opt(e.get("forecast"))
    actual = _fmt_opt(e.get("actual"))
    previous = _fmt_opt(e.get("previous"))

    if status == "結果":
        return f"{time_str} {name}｜予想:{forecast} / 結果:{actual} / 前回:{previous}"
    return f"{time_str} {name}｜予想:{forecast} / 前回:{previous}"


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
    sp_v, sp_c = _value_and_change("S&P500", market_rows)
    nd_v, nd_c = _value_and_change("NASDAQ", market_rows)
