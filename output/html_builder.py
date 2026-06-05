from utils.datetime_utils import now_jst


# 数値フォーマット
def fmt(v):
    try:
        return f"{float(v):.2f}"
    except:
        return "N/A"


def find(label, rows):
    for r in rows:
        if r["label"] == label:
            return r
    return None


def get_val(label, rows):
    r = find(label, rows)
    if not r:
        return ("N/A", "N/A")
    return (
        fmt(r.get("value")),
        r.get("change_text", "N/A"),
    )


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
):

    today = now_jst().strftime("%Y-%m-%d")

    # =========================
    # 市場
    # =========================
    sp_v, sp_c = get_val("S&P500", market_rows)
    nd_v, nd_c = get_val("NASDAQ", market_rows)
    dow_v, dow_c = get_val("NYダウ", market_rows)
    r2k_v, r2k_c = get_val("ラッセル2000", market_rows)
    nikkei_v, nikkei_c = get_val("日経平均", market_rows)

    # =========================
    # 金利
    # =========================
    y10_v, y10_c = get_val("米10年金利", market_rows)
    y2_v, y2_c = get_val("米2年金利", market_rows)

    try:
        spread = float(y10_v) - float(y2_v)
        spread = f"{spread:.2f}"
    except:
        spread = "N/A"

    # =========================
    # 為替
    # =========================
    dxy_v, dxy_c = get_val("DXY", market_rows)
    uj_v, uj_c = get_val("USD/JPY", market_rows)
    eu_v, eu_c = get_val("EUR/USD", market_rows)

    # =========================
    # ボラ
    # =========================
    vix_v, vix_c = get_val("VIX", market_rows)

    # =========================
    # コモディティ
    # =========================
    oil_v, oil_c = get_val("原油", market_rows)
    gold_v, gold_c = get_val("ゴールド", market_rows)
    copper_v, copper_c = get_val("銅", market_rows)

    # =========================
    # セクター
    # =========================
    strong = [r["label"] for r in sector_rows if r["change"] > 0]
    weak = [r["label"] for r in sector_rows if r["change"] < 0]

    # =========================
    # 経済指標
    # =========================
    def ev(e):
        t = e["event_dt_jst"].strftime("%m/%d %H:%M") if e.get("event_dt_jst") else "-"
        return f"{t} {e['event_name']}（予想:{e['forecast']} / 結果:{e['actual']}）"

    y_events = "<br>".join([ev(e) for e in macro_payload["yesterday_events"]]) or "なし"
    t_events = "<br>".join([ev(e) for e in macro_payload["today_events"]]) or "なし"

    # =========================
    # HTML
    # =========================
    html = f"""
    <html>
    <body style="font-family:Arial; line-height:1.6">
    <h2>📊 Daily Market Checklist ({today})</h2>

    <h3>🕒 ① マーケット</h3>
    S&P500: {sp_v} ({sp_c})<br>
    NASDAQ: {nd_v} ({nd_c})<br>
    Dow: {dow_v} ({dow_c})<br>
    Russell2000: {r2k_v} ({r2k_c})<br>
    日経平均: {nikkei_v} ({nikkei_c})

    <p><b>👉 一言まとめ：</b> {signal}</p>

    <h3>🏦 ② 金利</h3>
    10年: {y10_v} ({y10_c})<br>
    2年: {y2_v} ({y2_c})<br>
    長短差: {spread}

    <h3>💱 ③ 為替</h3>
    DXY: {dxy_v} ({dxy_c})<br>
    USD/JPY: {uj_v} ({uj_c})<br>
    EUR/USD: {eu_v} ({eu_c})

    <h3>😨 ④ ボラ</h3>
    VIX: {vix_v} ({vix_c})

    <h3>🛢️ ⑤ コモディティ</h3>
    原油: {oil_v} ({oil_c})<br>
    ゴールド: {gold_v} ({gold_c})<br>
    銅: {copper_v} ({copper_c})

    <h3>🧭 ⑥ セクター</h3>
    強い: {", ".join(strong)}<br>
    弱い: {", ".join(weak)}

    <h3>📊 ⑦ 市場内部（Breadth）</h3>
    Adv/Dec: データ未取得<br>
    上昇比率: 未取得<br>
    新高値/新安値: 未取得<br>
    👉 状態: データ取得未実装（今後拡張可）

    <h3>🎯 注目テーマ</h3>
    AI / データセンター / 半導体 / エネルギー / ドローン

    <h3>🧠 AI総括</h3>
    {ai_summary}

    <h3>🗓️ 経済指標</h3>
    <b>昨日</b><br>{y_events}<br>
    <b>今日</b><br>{t_events}

    <h3>📊 スコア</h3>
    {score} ({regime})

    <h3>📌 理由</h3>
    {"<br>".join(reasons)}

    </body>
    </html>
    """

    return html
