# =========================================
# Market Breadth（完全版）
# =========================================
def fetch_market_breadth(market_rows=None, sector_rows=None):

    try:
        lookup = {r["label"]: r for r in market_rows} if market_rows else {}

        # =========================
        # ① Advance / Decline
        # =========================
        adv = 0
        dec = 0

        targets = ["S&P500", "NASDAQ", "NYダウ", "Russell2000"]

        for name in targets:
            r = lookup.get(name)

            if not r or r.get("change_pct") is None:
                continue

            if r["change_pct"] > 0:
                adv += 1
            else:
                dec += 1

        total = adv + dec
        ratio = round((adv / total) * 100, 1) if total > 0 else None

        # =========================
        # ② New High / New Low（セクター代用）
        # =========================
        new_high = 0
        new_low = 0

        if sector_rows:
            for r in sector_rows:

                ch = r.get("change_pct")

                if ch is None:
                    continue

                if ch > 1.5:
                    new_high += 1
                elif ch < -1.5:
                    new_low += 1

        # =========================
        # ③ 状態
        # =========================
        if ratio is None:
            state = "未取得"
        elif ratio >= 70:
            state = "強い強気（全面上昇）"
        elif ratio >= 55:
            state = "強気"
        elif ratio >= 45:
            state = "中立"
        elif ratio >= 30:
            state = "弱気"
        else:
            state = "強い弱気（全面安）"

        return {
            "adv": adv,
            "dec": dec,
            "ratio": ratio,
            "new_high": new_high,
            "new_low": new_low,
            "state": state,
        }

    except Exception as e:
        print("[ERROR] breadth:", e)
        return {
            "adv": None,
            "dec": None,
            "ratio": None,
            "new_high": None,
            "new_low": None,
            "state": "取得失敗",
        }


# =========================================
# ETFフロー（proxy）
# =========================================
def fetch_etf_flows(market_rows=None):

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

    interpretation = "未取得"

    if spy:
        if float(spy.replace("%", "")) > 0:
            interpretation = "資金流入"
        else:
            interpretation = "資金流出"

    return {
        "SPY": spy,
        "QQQ": qqq,
        "IWM": iwm,
        "interpretation": interpretation,
    }


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

                if vix < 13:
                    sentiment = "強気"
                elif vix < 18:
                    sentiment = "やや強気"
                elif vix < 23:
                    sentiment = "中立"
                else:
                    sentiment = "弱気"

                put_call = round(0.5 + (vix - 10) / 30, 2)

                return {
                    "put_call": put_call,
                    "notable": f"VIX={round(vix,1)}",
                    "sentiment": sentiment,
                }

    except:
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
