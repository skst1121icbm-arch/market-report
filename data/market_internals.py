import re
import requests
4 import BeautifulSoupimport pandas as pd


REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


# =========================================================
# ① Breadth（Stooq 無料CSV）
# =========================================================
def fetch_market_breadth():
    urls = [
        (
            "https://stooq.com/q/d/l/?s=nyadv&f=sd2t2ohlcv&h&e=csv",
            "https://stooq.com/q/d/l/?s=nydec&f=sd2t2ohlcv&h&e=csv",
        ),
        (
            "https://stooq.com/q/d/l/?s=nyse_advances&f=sd2t2ohlcv&h&e=csv",
            "https://stooq.com/q/d/l/?s=nyse_declines&f=sd2t2ohlcv&h&e=csv",
        ),
    ]

    for adv_url, dec_url in urls:
        try:
            adv_df = pd.read_csv(adv_url)
            dec_df = pd.read_csv(dec_url)

            adv = int(float(adv_df.iloc[-1]["Close"]))
            dec = int(float(dec_df.iloc[-1]["Close"]))

            total = adv + dec
            ratio = round((adv / total) * 100, 2) if total > 0 else None

            if ratio is None:
                state = "未取得"
            elif ratio >= 60:
                state = "強気（市場全体が上昇）"
            elif ratio <= 40:
                state = "弱気（下落優勢）"
            else:
                state = "中立（方向感なし）"

            return {
                "adv": adv,
                "dec": dec,
                "ratio": ratio,
                "new_high": None,
                "new_low": None,
                "state": state,
            }

        except Exception:
            continue

    return {
        "adv": None,
        "dec": None,
        "ratio": None,
        "new_high": None,
        "new_low": None,
        "state": "取得失敗",
    }


# =========================================================
# ② ETFフロー（無料簡易版 = 価格proxy）
# =========================================================
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

    if spy:
        interpretation = "価格ベース簡易フロー推定"
    else:
        interpretation = "未取得（ETFフロー未接続）"

    return {
        "SPY": spy,
        "QQQ": qqq,
        "IWM": iwm,
        "interpretation": interpretation,
    }


# =========================================================
# ③ Options / Put-Call（無料簡易版）
# Cboe公開ページの簡易抽出 → ダメならVIX proxy
# =========================================================
def fetch_options_data(market_rows=None):
    try:
        url = "https://www.cboe.com/us/options/market_statistics/"
        res = requests.get(url, headers=REQUEST_HEADERS, timeout=20)
        res.raise_for_status()

        text = BeautifulSoup(res.text, "html.parser").get_text(" ", strip=True)

        m = re.search(r"Put/?Call[^0-9]*([0-1]\.\d{1,2})", text, flags=re.IGNORECASE)
        put_call = float(m.group(1)) if m else None

        if put_call is not None:
            sentiment = (
                "強気" if put_call < 0.8
                else "弱気" if put_call > 1.1
                else "中立"
            )

            return {
                "put_call": round(put_call, 2),
                "notable": "CBOE簡易取得",
                "sentiment": sentiment,
            }

    except Exception:
        pass

    # fallback: VIX proxy
    if market_rows:
        for r in market_rows:
            if r["label"] == "VIX":
                v = r.get("value")
                if v is not None:
                    try:
                        vv = float(v)
                        if vv < 15:
                            sentiment = "強気"
                        elif vv > 20:
                            sentiment = "弱気"
                        else:
                            sentiment = "中立"
                        return {
                            "put_call": None,
                            "notable": "VIX proxy",
                            "sentiment": sentiment,
                        }
                    except Exception:
                        pass

    return {
        "put_call": None,
        "notable": None,
        "sentiment": "未取得（Options未接続）",
    }


# =========================================================
# ④ 注目テーマ自動更新
# =========================================================
def detect_market_themes(sector_rows, market_rows=None, reasons=None):
    strong = [r["label"] for r in sector_rows if (r.get("change_pct") or 0) > 0]
    themes = []

    if "テクノロジー" in strong:
        themes.extend(["AI", "データセンター", "半導体"])

    if "資本財" in strong:
        themes.append("インフラ")

    if "エネルギー" in strong:
        themes.append("エネルギー")

    if "通信" in strong:
        themes.append("通信")

    text = " ".join(reasons or [])

    if "公益" in strong and "金利" in text:
        themes.append("ディフェンシブ")

    if market_rows:
        labels = {r["label"]: r for r in market_rows}

        copper = labels.get("銅")
        if copper and (copper.get("change_pct") or 0) > 0:
            themes.append("景気敏感")

        oil = labels.get("WTI原油")
        if oil and (oil.get("change_pct") or 0) > 0:
            themes.append("原油・エネルギー")

    if not themes:
        themes = ["テーマ不明（分散相場）"]

    return list(dict.fromkeys(themes))
