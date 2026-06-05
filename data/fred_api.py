import os
import requests

from config.settings import FRED_BASE_URL, FRED_SERIES_IDS


def fred_get(path, params=None):
    api_key = os.getenv("FRED_API_KEY")

    if not api_key:
        raise ValueError("FRED_API_KEY 未設定")

    params = params or {}
    params["api_key"] = api_key
    params["file_type"] = "json"

    url = f"{FRED_BASE_URL}/{path}"

    res = requests.get(url, params=params, timeout=20)
    res.raise_for_status()

    return res.json()


def fetch_latest(series_id):
    try:
        data = fred_get(
            "series/observations",
            {
                "series_id": series_id,
                "sort_order": "desc",
                "limit": 10,
            },
        )

        for o in data.get("observations", []):
            v = o.get("value")

            if v not in [None, ".", "NaN", ""]:
                return float(v)

    except Exception:
        return None

    return None


def fetch_us_rate_extras():
    return {
        "米2年債利回り": fetch_latest(FRED_SERIES_IDS["米2年債利回り"]),
        "実質金利(10Y)": fetch_latest(FRED_SERIES_IDS["実質金利(10Y)"]),
    }
