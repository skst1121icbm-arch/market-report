# =========================================
# Market Breadth（構成銘柄数ウェイト版）
# =========================================
def fetch_market_breadth(market_rows=None, sector_rows=None):
    """
    上昇銘柄比率を、各セクターETFの構成銘柄数ウェイトで近似する。
    - sector_rows の change_pct > 0 を「そのセクターは上昇」とみなす
    - 上昇したセクターの構成銘柄数合計 / 全構成銘柄数合計 × 100
    """

    # 提案値（運用用の管理テーブル）
    SECTOR_COUNTS = {
        "テクノロジー": 69,
        "金融": 80,        # XLF は 80 holdings と確認可 [2](https://www.tutorial.ai/b/how-to-create-folder-in-github)
        "ヘルスケア": 61,
        "一般消費": 53,
        "生活必需": 38,
        "資本財": 78,
        "エネルギー": 23,
        "素材": 28,
        "通信": 24,
        "公益": 31,
        "不動産": 27,
    }

    try:
        weighted_adv = 0
        weighted_dec = 0
        weighted_total = 0

        if not sector_rows:
            return {
                "ratio": None,
                "state": "未取得",
            }

        for r in sector_rows:
            label = r.get("label")
            ch = r.get("change_pct")

            if label is None or ch is None:
                continue

            weight = SECTOR_COUNTS.get(label, 0)
            if weight == 0:
                continue

            weighted_total += weight

            if ch > 0:
                weighted_adv += weight
            else:
                weighted_dec += weight

        ratio = round((weighted_adv / weighted_total) * 100, 1) if weighted_total > 0 else None

        if ratio is None:
            state = "未取得"
        elif ratio >= 70:
            state = "強い強気"
        elif ratio >= 55:
            state = "強気"
        elif ratio >= 45:
            state = "中立"
        elif ratio >= 30:
            state = "弱気"
        else:
            state = "強い弱気"

        return {
            "ratio": ratio,
            "state": state,
        }

    except Exception as e:
        print("[ERROR] breadth:", e)
        return {
            "ratio": None,
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
        try:
            if float(spy.replace("%", "")) > 0:
                interpretation = "資金流入"
            else:
                interpretation = "資金流出"
        except Exception:
            interpretation = "未取得"

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
        for r in market_rows or []:
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
                    "notable": f"VIX={round(vix, 1)}",
                    "sentiment": sentiment,
                }

    except Exception:
        pass

    return {
        "put_call": None,
        "notable": None,
        "sentiment": "未取得",
    }
