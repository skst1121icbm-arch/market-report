from logic.market_calc import summarize_sector_attention


def score_market(market_rows, sector_rows, recent_events, upcoming_events):
    """
    既存 main.py の score_market 本文が全文取得できていないため、
    ここは依存が崩れにくい提案実装。
    必要なら、この枠の中身だけ既存ロジックへ差し替えてください。
    """
    score = 0
    reasons = []

    lookup = {r["label"]: r for r in market_rows}

    def ch(label):
        row = lookup.get(label)
        if not row:
            return None
        return row.get("change_pct")

    # 株式指数
    spx = ch("S&P500")
    ndq = ch("NASDAQ")
    dow = ch("NYダウ")
    nikkei = ch("日経平均")

    if spx is not None:
        if spx > 0:
            score += 1
            reasons.append(f"S&P500が上昇（{spx:.2f}%）")
        elif spx < 0:
            score -= 1
            reasons.append(f"S&P500が下落（{spx:.2f}%）")

    if ndq is not None:
        if ndq > 0:
            score += 1
            reasons.append(f"NASDAQが上昇（{ndq:.2f}%）")
        elif ndq < 0:
            score -= 1
            reasons.append(f"NASDAQが下落（{ndq:.2f}%）")

    if dow is not None:
        if dow > 0:
            score += 1
            reasons.append(f"NYダウが上昇（{dow:.2f}%）")
        elif dow < 0:
            score -= 1
            reasons.append(f"NYダウが下落（{dow:.2f}%）")

    if nikkei is not None:
        if nikkei > 0:
            score += 1
            reasons.append(f"日経平均が上昇（{nikkei:.2f}%）")
        elif nikkei < 0:
            score -= 1
            reasons.append(f"日経平均が下落（{nikkei:.2f}%）")

    # ボラティリティ
    vix = ch("VIX")
    if vix is not None:
        if vix >= 3:
            score -= 2
            reasons.append(f"VIXが大きく上昇（{vix:.2f}%）")
        elif vix > 0:
            score -= 1
            reasons.append(f"VIXが上昇（{vix:.2f}%）")
        elif vix < 0:
            score += 1
            reasons.append(f"VIXが低下（{vix:.2f}%）")

    # 金利
    us10y = ch("米10年金利")
    if us10y is not None:
        if us10y >= 1.0:
            score -= 1
            reasons.append(f"米10年金利が上昇（{us10y:.2f}%）")
        elif us10y <= -1.0:
            score += 1
            reasons.append(f"米10年金利が低下（{us10y:.2f}%）")

    # セクターの広がり
    sector_attention = summarize_sector_attention(sector_rows)
    leaders = [x["label"] for x in sector_attention["leaders"]]
    laggards = [x["label"] for x in sector_attention["laggards"]]

    if "テクノロジー" in leaders:
        score += 1
        reasons.append("テクノロジーが上位セクター")
    if "金融" in leaders:
        score += 1
        reasons.append("金融が上位セクター")
    if "公益" in leaders or "生活必需" in leaders:
        score -= 1
        reasons.append("ディフェンシブセクターが相対優位")

    if "テクノロジー" in laggards:
        score -= 1
        reasons.append("テクノロジーが下位セクター")

    # 経済イベント（軽めに反映）
    for e in recent_events or []:
        if e.get("importance_label") == "高":
            score += 0
            reasons.append(f'重要指標通過: {e.get("event_name", "N/A")}')

    for e in upcoming_events or []:
        if e.get("importance_label") == "高":
            score -= 0
            reasons.append(f'重要指標予定: {e.get("event_name", "N/A")}')

    return score, reasons


def classify_regime(score):
    if score >= 5:
        return "強めのリスクオン"
    elif score >= 2:
        return "ややリスクオン"
    elif score >= -1:
        return "中立"
    elif score >= -4:
        return "ややリスクオフ"
    else:
        return "強めのリスクオフ"
``