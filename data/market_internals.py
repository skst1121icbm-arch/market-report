import random


# =========================================
# Breadth（市場内部）
# =========================================
def fetch_market_breadth():
    adv = random.randint(1500, 3000)
    dec = random.randint(1000, 2500)

    ratio = adv / (adv + dec) * 100

    new_high = random.randint(50, 300)
    new_low = random.randint(20, 200)

    # 状態判定
    if ratio > 60 and adv > dec:
        state = "強気（市場全体が上昇）"
    elif ratio < 40:
        state = "弱気（下落優勢）"
    else:
        state = "中立（方向感なし）"

    return {
        "adv": adv,
        "dec": dec,
        "ratio": round(ratio, 2),
        "new_high": new_high,
        "new_low": new_low,
        "state": state,
    }


# =========================================
# ETFフロー（簡易）
# =========================================
def fetch_etf_flows():

    return {
        "SPY": "+1.2B",
        "QQQ": "-0.5B",
        "IWM": "+0.3B",
        "interpretation": "大型株に資金流入、ハイテクに一部調整",
    }


# =========================================
# オプション（簡易）
# =========================================
def fetch_options_data():

    put_call = round(random.uniform(0.7, 1.3), 2)

    if put_call < 0.8:
        sentiment = "強気"
    elif put_call > 1.1:
        sentiment = "弱気"
    else:
        sentiment = "中立"

    return {
        "put_call": put_call,
        "notable": "NVDA コールに大口フロー",
        "sentiment": sentiment,
    }


# =========================================
# テーマ自動生成
# =========================================
def detect_market_themes(sector_rows):

    themes = []

    strong = [r["label"] for r in sector_rows if r["change"] > 0]

    if "テクノロジー" in strong:
        themes.append("AI")
        themes.append("データセンター")

    if "エネルギー" in strong:
        themes.append("原油・エネルギー")

    if "資本財" in strong:
        themes.append("インフラ")

    if not themes:
        themes = ["テーマ不明（分散相場）"]

    return themes
