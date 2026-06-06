# =========================================
# Breadth（疑似）
# =========================================
def fetch_market_breadth(market_rows=None):

    try:
        lookup = {r["label"]: r for r in market_rows} if market_rows else {}

        adv = 0
        dec = 0

        for name in ["S&P500", "NASDAQ", "NYダウ"]:
            r = lookup.get(name)

            if r and r.get("change_pct") is not None:
                if r["change_pct"] > 0:
                    adv += 1
                else:
                    dec += 1

        total = adv + dec

        ratio = round((adv / total) * 100, 2) if total > 0 else None

        if ratio is None:
            state = "未取得"
        elif ratio >= 66:
            state = "強気（上昇優勢）"
        elif ratio <= 34:
            state = "弱気（下落優勢）"
        else:
            state = "中立"

        return {
            "adv": adv,
            "dec": dec,
            "ratio": ratio,
            "new_high": None,
            "new_low": None,
            "state": state,
        }

    except Exception as e:
        print("[ERROR] breadth:", e)
        return {
            "adv": None,
            "dec": None,
            "ratio": None,
            "state": "取得失敗",
        }


# =========================================
# ETFフロー（proxy）
# =========================================
def fetch_etf_flows(market_rows=None):
    try:
        lookup = {r["label"]: r for r in market_rows} if market_rows else {}

        def conv(label):
            r = lookup.get(label)
            if not r or r.get("change_pct") is None:
                return None
            sign = "+" if r["change_pct"] > 0 else ""
            return f"{sign}{r['change_pct']:.2f}%"

        spy = conv("S&P500")
        qqq = conv("NASDAQ")
        iwm = conv("Russell2000")

        interpret = "未取得"

        if spy:
            if float(spy.replace("%", "")) > 0:
                interpret = "資金流入"
            else:
                interpret = "資金流出"

        return {
            "SPY": spy,
            "QQQ": qqq,
            "IWM": iwm,
            "interpretation": interpret,
        }

    except Exception as e:
        print("[ERROR] etf:", e)
        return {}


# =========================================
# Options（VIXベース）
# =========================================
def fetch_options_data(market_rows=None):

    try:
        for r in market_rows:
            if r["label"] == "VIX":

                vix = r.get("value")

                if vix is None:
                    break

                if vix < 15:
                    sentiment = "強気"
                elif vix > 20:
                    sentiment = "弱気"
                else:
                    sentiment = "中立"

                return {
                    "put_call": round(vix / 20, 2),
                    "notable": f"VIX={vix}",
                    "sentiment": sentiment,
                }

    except Exception:
        pass

    return {
        "put_call": None,
        "notable": None,
        "sentiment": "未取得",
    }


# =========================================
# テーマ
# =========================================
def detect_market_themes(sector_rows, market_rows=None, reasons=None):

    strong = [r["label"] for r in sector_rows if (r.get("change_pct") or 0) > 0]

    themes = []

    if "テクノロジー" in strong:
        themes += ["AI", "半導体"]

    if "エネルギー" in strong:
        themes.append("エネルギー")

    if not themes:
        themes = ["分散相場"]

    return list(dict.fromkeys(themes))
