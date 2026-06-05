import os
import requests


def _safe_get_json(url, timeout=10):
    if not url:
        return None

    try:
        res = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=timeout,
        )
        res.raise_for_status()
        return res.json()
    except Exception:
        return None


# =========================================
# Breadth（NYSE Adv/Dec 等）
# 期待する JSON 例:
# {
#   "adv": 2100,
#   "dec": 1300,
#   "ratio": 61.76,
#   "new_high": 120,
#   "new_low": 45
# }
# =========================================
def fetch_market_breadth():
    url = os.getenv("MARKET_BREADTH_URL")
    data = _safe_get_json(url)

    if not data:
        return {
            "adv": None,
            "dec": None,
            "ratio": None,
            "new_high": None,
            "new_low": None,
            "state": "未取得（Breadthデータソース未接続）",
        }

    adv = data.get("adv")
    dec = data.get("dec")
    ratio = data.get("ratio")
    new_high = data.get("new_high")
    new_low = data.get("new_low")

    state = "未取得"
    try:
        ratio_num = float(ratio) if ratio is not None else None
        if ratio_num is not None:
            if ratio_num >= 60:
                state = "強気（市場全体が上昇）"
            elif ratio_num <= 40:
                state = "弱気（下落優勢）"
            else:
                state = "中立（方向感なし）"
    except Exception:
        state = "未取得"

    return {
        "adv": adv,
        "dec": dec,
        "ratio": ratio,
        "new_high": new_high,
        "new_low": new_low,
        "state": state,
    }


# =========================================
# ETFフロー（SPY / QQQ / IWM）
# 期待する JSON 例:
# {
#   "SPY": "+1.2B",
#   "QQQ": "-0.5B",
#   "IWM": "+0.3B"
# }
# 補足:
# ETF flow の日次安定APIはこの場で確認できておらず、
# Nasdaq Data Link の ETFF は Premium です。[3](https://data.nasdaq.com/databases/ETFF/documentation?anchor=data-organization)
# =========================================
def fetch_etf_flows():
    url = os.getenv("ETF_FLOWS_URL")
    data = _safe_get_json(url)

    if not data:
        return {
            "SPY": None,
            "QQQ": None,
            "IWM": None,
            "interpretation": "未取得（ETFフローデータソース未接続）",
        }

    spy = data.get("SPY")
    qqq = data.get("QQQ")
    iwm = data.get("IWM")

    interpretation = "中立"
    text = " ".join([str(x) for x in [spy, qqq, iwm] if x is not None])

    if "+" in text:
        interpretation = "一部ETFに資金流入"
    if "-" in text and "+" not in text:
        interpretation = "ETF全体で資金流出寄り"

    return {
        "SPY": spy,
        "QQQ": qqq,
        "IWM": iwm,
        "interpretation": interpretation,
    }


# =========================================
# オプションデータ
# 期待する JSON 例:
# {
#   "put_call": 0.92,
#   "notable": "NVDA コールに大口フロー",
#   "sentiment": "中立"
# }
#
# Cboe には Put/Call Ratio のヒストリカルページがあります。[2](https://www.cboe.com/us/options/market_statistics/historical_data/)
# ただし、この場では安定した無料JSONエンドポイントは確認できていないため、
# URL は環境変数経由で差し込み前提にしています。
# =========================================
def fetch_options_data():
    url = os.getenv("OPTIONS_DATA_URL")
    data = _safe_get_json(url)

    if not data:
        return {
            "put_call": None,
            "notable": None,
            "sentiment": "未取得（オプションデータソース未接続）",
        }

    put_call = data.get("put_call")
    notable = data.get("notable")
    sentiment = data.get("sentiment")

    if sentiment in [None, ""]:
        try:
            p = float(put_call)
            if p < 0.8:
                sentiment = "強気"
            elif p > 1.1:
                sentiment = "弱気"
            else:
                sentiment = "中立"
        except Exception:
            sentiment = "未取得"

    return {
        "put_call": put_call,
        "notable": notable,
        "sentiment": sentiment,
    }


# =========================================
# 注目テーマの自動更新
# セクター強弱 + 市場要因から決める
# =========================================
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

    # reasons から補完
    text = " ".join(reasons or [])

    if "公益" in strong and "金利" in text:
        themes.append("ディフェンシブ")

    # market_rows を見て簡易補完
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

    # 重複削除
    return list(dict.fromkeys(themes))
