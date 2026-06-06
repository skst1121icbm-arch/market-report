def generate_trend_signal(score, market_rows, sector_attention, recent, upcoming):

    details = []

    # 指数の動き
    for r in market_rows:
        change = r.get("change_text")
        if change and change != "N/A":
            details.append(f"{r['label']} {change}")

    # セクター
    leaders = [x["label"] for x in sector_attention.get("leaders", [])]
    laggards = [x["label"] for x in sector_attention.get("laggards", [])]

    if leaders:
        details.append("強い: " + ", ".join(leaders))

    if laggards:
        details.append("弱い: " + ", ".join(laggards))

    # 経済イベント
    if upcoming:
        names = [e.get("event_name") for e in upcoming if e.get("event_name")]
        if names:
            details.append("注目イベント: " + ", ".join(names[:3]))

    # スコア判定
    if score >= 5:
        signal = "上昇トレンド"
    elif score <= -5:
        signal = "下落警戒"
    else:
        signal = "レンジ"

    return signal, details
