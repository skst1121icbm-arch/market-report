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


def fetch_latest_and_prev(series_id):
    """
    直近の有効な2件を返す
    戻り値:
      (latest_value, prev_value)
    """
    try:
        data = fred_get(
            "series/observations",
            {
                "series_id": series_id,
                "sort_order": "desc",
                "limit": 20,
            },
        )

        vals = []
        for o in data.get("observations", []):
            v = o.get("value")
            if v not in [None, ".", "NaN", ""]:
                vals.append(float(v))
            if len(vals) >= 2:
                break

        if len(vals) >= 2:
            return vals[0], vals[1]
        elif len(vals) == 1:
            return vals[0], None

    except Exception:
        return None, None

    return None, None


def fetch_us_rate_extras():
    # 2Y
    y2_latest, y2_prev = fetch_latest_and_prev(FRED_SERIES_IDS["米2年債利回り"])

    y2_change_pct = None
    if y2_latest is not None and y2_prev not in [None, 0]:
        try:
            y2_change_pct = round((y2_latest - y2_prev) / y2_prev * 100, 2)
        except Exception:
            y2_change_pct = None

    # 実質金利(10Y)
    real10_latest, _ = fetch_latest_and_prev(FRED_SERIES_IDS["実質金利(10Y)"])

    return {
        "米2年債利回り": y2_latest,
        "米2年債利回り_前回": y2_prev,
        "米2年債利回り_前日比_pct": y2_change_pct,
        "実質金利(10Y)": real10_latest,
    }
