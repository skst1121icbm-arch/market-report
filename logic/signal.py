def generate_trend_signal(score, market_rows, sector_attention, recent, upcoming):

    details = []

    for r in market_rows:
        if r.get("change_text"):
            details.append(f"{r['label']} {r['change_text']}")

    leaders = [x["label"] for x in sector_attention["leaders"]]
    laggards = [x["label"] for x in sector_attention["laggards"]]

    if leaders:
        details.append("強い: " + ", ".join(leaders))
    if laggards:
        details.append("弱い: " + ", ".join(laggards))

    if score >= 5:
        signal = "上昇トレンド"
    elif score <= -5:
        signal = "下落警戒"
    else:
        signal = "レンジ"

    return signal, details
