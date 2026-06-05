import os
import requests
from datetime import datetime
from config.settings import FRED_BASE_URL, MAJOR_RELEASE_KEYWORDS

def fred_get(path, params=None):
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        raise ValueError("FRED_API_KEY が未設定です。")

    params = params or {}
    params["api_key"] = api_key
    params["file_type"] = "json"

    url = f"{FRED_BASE_URL}/{path}"
    res = requests.get(url, params=params)
    res.raise_for_status()
    return res.json()

def is_major_release(release_name):
    s = str(release_name)
    return any(k.lower() in s.lower() for k in MAJOR_RELEASE_KEYWORDS)

def parse_date_only(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        return None

def fetch_fred_latest_result(series_id):
    try:
        data = fred_get(
            "series/observations",
            {
                "series_id": series_id,
                "sort_order": "desc",
                "limit": 2,
            }
        )
        obs = data.get("observations", [])
        vals = [o for o in obs if o.get("value") not in [None, ".", "NaN", "nan"]]

        if not vals:
            return None

        return vals[0].get("value")

    except Exception:
        return None
