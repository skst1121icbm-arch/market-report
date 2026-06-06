def fetch_market_breadth(market_rows=None):

    try:
        # ✅ proxy（指数で疑似Breadth）
        lookup = {r["label"]: r for r in market_rows} if market_rows else {}

        sp = lookup.get("S&P500")
        nd = lookup.get("NASDAQ")
        dow = lookup.get("NYダウ")

        score = 0
        adv = 0
        dec = 0

        for r in [sp, nd, dow]:
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
