def fetch_market_breadth():
    return {
        "adv": None,
        "dec": None,
        "ratio": None,
        "new_high": None,
        "new_low": None,
        "state": "未取得（Breadth未接続）",
    }


def fetch_etf_flows():
    return {
        "SPY": None,
        "QQQ": None,
        "IWM": None,
        "interpretation": "未取得（ETFフロー未接続）",
    }


def fetch_options_data():
    return {
        "put_call": None,
        "notable": None,
        "sentiment": "未取得（Options未接続）",
    }


def detect_market_themes(sector_rows):

    strong = [r["label"] for r in sector_rows if (r.get("change") or 0) > 0]

    themes = []

    if "テクノロジー" in strong:
        themes.extend(["AI", "データセンター", "半導体"])

    if "エネルギー" in strong:
        themes.append("エネルギー")

    if "資本財" in strong:
        themes.append("インフラ")

    if not themes:
        themes = ["テーマ分散"]

    return list(dict.fromkeys(themes))
