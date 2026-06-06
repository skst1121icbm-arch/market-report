import requests


def fetch_fear_greed():
    """
    CNN Fear & Greed Index を取得

    戻り値:
        (score, rating)
        例: (42, "fear")
    """

    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"

        res = requests.get(url, timeout=20)
        res.raise_for_status()

        data = res.json()

        fg = data.get("fear_and_greed", {})
        score = fg.get("score")
        rating = fg.get("rating")

        return score, rating

    except Exception as e:
        print("[WARN] FearGreed fetch failed:", e)
        return None, None
