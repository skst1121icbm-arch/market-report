import re
from logic.marketparse_numeric(value):from logic.market_calc import summarize_sector_attention
    if value is None:
        return None

    s = str(value).strip()
    if s in ["", "-", "--", "None", "nan", "N/A", "未取得"]:
        return None

    s = s.replace(",", "")
    m = re.search(r"[-+]?\d*\.?\d+", s)
    if not m:
        return None

    num = float(m.group())

    upper = s.upper()
    if "K" in upper:
        num *= 1_000
    elif "M" in upper:
        num *= 1_000_000
    elif "B" in upper:
        num *= 1_000_000_000

    return num


def _macro_direction(event_name: str) -> int:
    if not event_name:
        return 0

    s = str(event_name)

    growth_positive_when_higher = [
        "非農業部門雇用者数",
        "NFP",
        "雇用者数",
        "GDP",
        "小売売上高",
        "PMI",
        "景気一致指数",
        "景気先行指数",
        "鉱工業生産",
        "製造業受注",
        "消費支出",
        "家計調査",
    ]

    risk_on_when_lower = [
        "失業率",
        "新規失業保険申請件数",
        "失業保険継続受給者数",
    ]

    inflation_negative_when_higher = [
        "CPI",
        "消費者物価指数",
        "PPI",
        "生産者物価指数",
        "インフレ",
        "平均時給",
        "GDPデフレーター",
    ]

    for k in growth_positive_when_higher:
        if k in s:
            return +1

    for k in risk_on_when_lower:
        if k in s:
            return -1

    for k in inflation_negative_when_higher:
        if k in s:
            return -1

    return 0


def _score_macro_event(event: dict):
    event_name = event.get("event_name", "")
    actual = _parse_numeric(event.get("actual"))
    forecast = _parse_numeric(event.get("forecast"))
    importance = event.get("importance_label", "中")

    if actual is None or forecast is None:
        return 0, None

    direction = _macro_direction(event_name)
    if direction == 0:
        return 0, None

    surprise = actual - forecast

    base = 2 if importance == "高" else 1 if importance == "中" else 0.5

    if direction == +1:
        score = base if surprise > 0 else -base if surprise < 0 else 0
    else:
        score = base if surprise < 0 else -base if surprise > 0 else 0

    relation = "上振れ" if surprise > 0 else "下振れ" if surprise < 0 else "予想通り"
    tone = "リスクオン寄与" if score > 0 else "リスクオフ寄与" if score < 0 else "中立"

    reason = f"{event_name}が{relation}（結果={event.get('actual')} / 予想={event.get('forecast')}）→ {tone}"
    return score, reason


def _score_breadth(breadth: dict):
    score = 0
    reasons = []

    if not breadth:
        return score, reasons

    ratio = breadth.get("ratio")
    adv = breadth.get("adv")
    dec = breadth.get("dec")
    state = breadth.get("state")

    try:
        ratio_num = float(ratio)
    except Exception:
        ratio_num = None

    if ratio_num is not None:
        if ratio_num >= 60:
            score += 1
            reasons.append(f"上昇銘柄比率が高い（{ratio_num:.2f}%）")
        elif ratio_num <= 40:
            score -= 1
            reasons.append(f"上昇銘柄比率が低い（{ratio_num:.2f}%）")

    if adv is not None and dec is not None:
        try:
            if float(adv) > float(dec):
                score += 0.5
                reasons.append(f"Adv/Dec良好（{adv}/{dec}）")
            elif float(adv) < float(dec):
                score -= 0.5
                reasons.append(f"Adv/Dec悪化（{adv}/{dec}）")
        except Exception:
            pass

    if state:
        reasons.append(f"市場内部: {state}")

    return score, reasons


def _score_etf_flows(etf_flows: dict):
    score = 0
    reasons = []

    if not etf_flows:
        return score, reasons

    for name in ["SPY", "QQQ", "IWM"]:
        val = _parse_numeric(etf_flows.get(name))
        if val is None:
            continue

        if val > 0:
            score += 0.5
            reasons.append(f"{name}フロー流入（{etf_flows.get(name)}）")
        elif val < 0:
            score -= 0.5
            reasons.append(f"{name}フロー流出（{etf_flows.get(name)}）")

    if etf_flows.get("interpretation"):
        reasons.append(f"ETFフロー解釈: {etf_flows.get('interpretation')}")

    return score, reasons


def _score_options(options_data: dict):
    score = 0
    reasons = []

    if not options_data:
        return score, reasons

    put_call = options_data.get("put_call")
    notable = options_data.get("notable")
    sentiment = options_data.get("sentiment")

    try:
        p = float(put_call)
    except Exception:
        p = None

    if p is not None:
        if p < 0.8:
            score += 1
            reasons.append(f"Put/Call低水準（{p:.2f}）→ 強気")
        elif p > 1.1:
            score -= 1
            reasons.append(f"Put/Call高水準（{p:.2f}）→ 弱気")
        else:
            reasons.append(f"Put/Call中立（{p:.2f}）")

    if notable:
        reasons.append(f"オプション大口: {notable}")

    if sentiment:
        reasons.append(f"オプションセンチメント: {sentiment}")

    return score, reasons


def score_market(
    market_rows,
    sector_rows,
    recent_events,
    upcoming_events,
    breadth=None,
    etf_flows=None,
    options_data=None,
):
    score = 0
    reasons = []

    lookup = {r["label"]: r for r in market_rows}

    def ch(label):
        row = lookup.get(label)
        if not row:
            return None
        return row.get("change_pct")

    # 指数
    spx = ch("S&P500")
    ndq = ch("NASDAQ")
    dow = ch("NYダウ")
    nikkei = ch("日経平均")

    for name, val in [("S&P500", spx), ("NASDAQ", ndq), ("NYダウ", dow), ("日経平均", nikkei)]:
        if val is None:
            continue
        score += 1 if val > 0 else -1 if val < 0 else 0
        reasons.append(f"{name} {'上昇' if val > 0 else '下落' if val < 0 else '横ばい'}（{val:.2f}%）")

    # VIX
    vix = ch("VIX")
    if vix is not None:
        if vix >= 5:
            score -= 2
            reasons.append(f"VIXが大きく上昇（{vix:.2f}%）")
        elif vix > 0:
            score -= 1
            reasons.append(f"VIXが上昇（{vix:.2f}%）")
        elif vix < 0:
            score += 1
            reasons.append(f"VIXが低下（{vix:.2f}%）")

    # 10Y
    us10y = ch("米10年金利")
    if us10y is not None:
        if us10y >= 1.0:
            score -= 1
            reasons.append(f"米10年金利が上昇（{us10y:.2f}%）")
        elif us10y <= -1.0:
            score += 1
            reasons.append(f"米10年金利が低下（{us10y:.2f}%）")

    # セクター
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

    # Breadth / ETF / Options
    b_score, b_reasons = _score_breadth(breadth)
    score += b_score
    reasons.extend(b_reasons)

    f_score, f_reasons = _score_etf_flows(etf_flows)
    score += f_score
    reasons.extend(f_reasons)

    o_score, o_reasons = _score_options(options_data)
    score += o_score
    reasons.extend(o_reasons)

    # Macro
    for e in recent_events or []:
        macro_score, macro_reason = _score_macro_event(e)
        if macro_score != 0:
            score += macro_score
            reasons.append(macro_reason)

    for e in upcoming_events or []:
        if e.get("event_status") == "予定" and e.get("importance_label") == "高":
            score -= 0.5
            reasons.append(f"重要指標待ち: {e.get('event_name')}")

    return score, reasons


def classify_regime(score):
    if score >= 7:
        return "強めのリスクオン"
    elif score >= 2:
        return "ややリスクオン"
    elif score >= -1:
        return "中立"
    elif score >= -6:
        return "ややリスクオフ"
    else:
        return "強めのリスクオフ"


