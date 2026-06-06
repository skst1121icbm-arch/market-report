import re
import requests
import pandas as pd
from bs4 import BeautifulSoup


# =========================================
# ✅ Breadth（Stooq無料CSV）
# =========================================
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
            ratio = round((adv / total) * 100, 2)

            state = (
                "強気" if ratio >= 60
                else "弱気" if ratio <= 40
                else "中立"
            )

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


# =========================================
# ✅ ETFフロー（無料簡易版）
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

    if spy:
        if float(spy.replace("%", "")) > 0:
            interpretation = "資金流入"
        else:
            interpretation = "資金流出"
    else:
        interpretation = "未取得"

    return {
        "SPY": spy,
        "QQQ": qqq,
        "IWM": iwm,
        "interpretation": interpretation,
    }


# =========================================
# ✅ Options（簡易版）
# =========================================
def fetch_options_data(market_rows=None):

    try:
        url = "https://www.cboe.com/us/options/market_statistics/"
        res = requests.get(url, timeout=10)

        text = BeautifulSoup(res.text, "html.parser").get_text()

        m = re.search(r"([0-1]\.[0-9]{1,2})", text)
        put_call = float(m.group(1)) if m else None

        if put_call is not None:
            if put_call < 0.8:
                sentiment = "強気"
            elif put_call > 1.1:
                sentiment = "弱気"
            else:
                sentiment = "中立"

            return {
                "put_call": put_call,
                "notable": "CBOE簡易",
                "sentiment": sentiment,
            }

    except Exception:
        pass

    return {
        "put_call": None,
        "notable": "VIX proxy",
        "sentiment": "未取得",
    }


# =========================================
# ✅ テーマ
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
