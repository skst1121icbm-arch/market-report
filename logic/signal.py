from logic.market_calc import summarize_sector_attention


def generate_trend_signal(score, market_rows, sector_attention, recent_events, upcoming_events):
    """
    返り値:
      signal: str
      signal_details: list[str]
    """
    lookup = {r["label"]: r for r in market_rows}
    details = []

    def ch(label):
        row = lookup.get(label)
        if not row:
            return None
        return row.get("change_pct")

    if score >= 5:
        signal = "上昇トレンド優勢"
    elif score >= 2:
        signal = "やや上向き"
    elif score >= -1:
        signal = "方向感乏しい"
    elif score >= -4:
        signal = "やや下向き"
    else:
        signal = "下落警戒"

    vix = ch("VIX")
    usd_jpy = ch("USD/JPY")
    nasdaq = ch("NASDAQ")
    spx = ch("S&P500")

    if spx is not None:
        details.append(f"S&P500 {spx:+.2f}%")
    if nasdaq is not None:
        details.append(f"NASDAQ {nasdaq:+.2f}%")
    if vix is not None:
        details.append(f"VIX {vix:+.2f}%")
    if usd_jpy is not None:
        details.append(f"USD/JPY {usd_jpy:+.2f}%")

    leaders = [x["label"] for x in sector_attention.get("leaders", [])]
    laggards = [x["label"] for x in sector_attention.get("laggards", [])]

    if leaders:
        details.append("強いセクター: " + ", ".join(leaders))
    if laggards:
        details.append("弱いセクター: " + ", ".join(laggards))

    high_recent = [e.get("event_name") for e in (recent_events or []) if e.get("importance_label") == "高"]
    high_upcoming = [e.get("event_name") for e in (upcoming_events or []) if e.get("importance_label") == "高"]

    if high_recent:
        details.append("直近重要指標: " + ", ".join(high_recent[:3]))
    if high_upcoming:
        details.append("今後の重要指標: " + ", ".join(high_upcoming[:3]))

    return signal, details