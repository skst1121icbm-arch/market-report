import re
from logic.market_calc import summarize_sector_attention


# 数値変換
def _parse_numeric(value):
    if value is None:
        return None

    s = str(value).strip()
    if s in ["", "-", "--", "None", "nan", "N/A", "未取得"]:
        return None

    s = s.replace(",", "")
    m = re.search(r"[-+]?\d*\.?\d+", s)
    if not m:
        return None

    return float(m.group())


# Breadth
def _score_breadth(breadth):

    score = 0
    reasons = []

    if not breadth:
        return score, reasons

    ratio = breadth.get("ratio")
    adv = breadth.get("adv")
    dec = breadth.get("dec")

    try:
        r = float(ratio)
    except:
        r = None

    if r is not None:
        if r >= 60:
            score += 1
            reasons.append(f"上昇銘柄比率が高い（{r}%）")
        elif r <= 40:
            score -= 1
            reasons.append(f"上昇銘柄比率が低い（{r}%）")

    try:
        if float(adv) > float(dec):
            score += 0.5
            reasons.append(f"Adv優勢（{adv}/{dec}）")
        else:
            score -= 0.5
            reasons.append(f"Dec優勢（{adv}/{dec}）")
    except:
        pass

    return score, reasons


# ETFフロー
def _score_etf_flows(etf_flows):

    score = 0
    reasons = []

    if not etf_flows:
        return score, reasons

    for k in ["SPY", "QQQ", "IWM"]:
        v = _parse_numeric(etf_flows.get(k))
        if v is None:
            continue

        if v > 0:
            score += 0.5
            reasons.append(f"{k}流入")
        else:
            score -= 0.5
            reasons.append(f"{k}流出")

    return score, reasons


# オプション
def _score_options(opt):

    score = 0
    reasons = []

    try:
        p = float(opt.get("put_call"))
    except:
        p = None

    if p is not None:
        if p < 0.8:
            score += 1
            reasons.append("強気オプション")
        elif p > 1.1:
            score -= 1
            reasons.append("弱気オプション")

    return score, reasons


# メイン
def score_market(
    market_rows,
    sector_rows,
    recent_events,
    upcoming_events,
    breadth=None,
    etf_flows=None,
    options_data=None
):

    score = 0
    reasons = []

    lookup = {r["label"]: r for r in market_rows}

    def ch(label):
        r = lookup.get(label)
        return r.get("change_pct") if r else None

    # 指数
    for name in ["S&P500", "NASDAQ", "NYダウ", "日経平均"]:
        val = ch(name)
        if val is None:
            continue

        if val > 0:
            score += 1
        elif val < 0:
            score -= 1

        reasons.append(f"{name}:{val}%")

    # VIX
    vix = ch("VIX")
    if vix is not None:
        if vix > 5:
            score -= 2
        elif vix > 0:
            score -= 1
        else:
            score += 1

    # Breadth
    s, r = _score_breadth(breadth)
    score += s
    reasons += r

    # ETF
    s, r = _score_etf_flows(etf_flows)
    score += s
    reasons += r

    # Options
    s, r = _score_options(options_data)
    score += s
    reasons += r

    return score, reasons


def classify_regime(score):
    if score >= 5:
        return "強気"
    elif score >= 1:
        return "やや強気"
    elif score >= -1:
        return "中立"
    elif score >= -5:
        return "弱気"
    else:
        return "強弱気"
