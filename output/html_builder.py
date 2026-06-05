from utils.datetime_utils import now_jst


def fmt(v):
    try:
        return f"{float(v):.2f}"
    except:
        return "N/A"


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

    def find(label):
        for r in market_rows:
            if r["label"] == label:
                return fmt(r["value"]), r["change_text"]
        return "N/A", "N/A"

    sp = find("S&P500")
    nd = find("NASDAQ")
    dow = find("NYダウ")
    rut = find("Russell2000")
    nik = find("日経平均")

    vix = find("VIX")
    y10 = find("米10年金利")

    y2 = fmt(rate_extras.get("米2年債利回り"))

    usd = find("USD/JPY")
    dxy = find("DXY")
    eur = find("EUR/USD")

    oil = find("WTI原油")
    gold = find("ゴールド")
    copper = find("銅")

    def ev(e):
        t = e["event_dt_jst"].strftime("%m/%d %H:%M") if e.get("event_dt_jst") else "-"
        return f"{t} {e['event_name']}"

    html = f"""
    <html>
    <body style="font-family:Arial">

    <h2>📊 Daily Market Checklist {today}</h2>

    <h3>① マーケット</h3>
    S&P500 {sp}<br>
    NASDAQ {nd}<br>
    Dow {dow}<br>
    Russell {rut}<br>
    日経 {nik}

    <h3>② 金利</h3>
    10Y {y10}<br>
    2Y {y2}

    <h3>③ 為替</h3>
    USDJPY {usd}<br>
    DXY {dxy}<br>
    EURUSD {eur}

    <h3>④ コモディティ</h3>
    原油 {oil}<br>
    ゴールド {gold}<br>
    銅 {copper}

    <h3>⑤ 市場内部</h3>
    Adv/Dec {breadth.get('adv')} / {breadth.get('dec')}<br>
    状態 {breadth.get('state')}

    <h3>⑥ ETFフロー</h3>
    SPY {etf_flows.get('SPY')}<br>
    QQQ {etf_flows.get('QQQ')}<br>

    <h3>⑦ オプション</h3>
    PutCall {options_data.get('put_call')}<br>
    {options_data.get('sentiment')}

    <h3>⑧ テーマ</h3>
    {", ".join(themes)}

    <h3>⑨ 経済指標</h3>
    {'<br>'.join(ev(e) for e in macro_payload['today_events'])}

    <h3>⑩ AI</h3>
    {ai_summary}

    <h3>スコア</h3>
    {score} ({regime})

    </body>
    </html>
    """

    return html
