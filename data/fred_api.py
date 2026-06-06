import os
import requests


FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"


def _safe_float(v):
    try:
        if v in [None, "", ".", "None"]:
            return None
        return float(v)
    except Exception:
        return None


def _get_latest_two_observations(series_id: str, api_key: str):
    """
    FREDから指定シリーズの最新2件（有効な数値のみ）を取得する。
    戻り値:
        (latest_value, previous_value)
    """
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 10,  # 欠損 "." を飛ばすため少し多め
    }

    res = requests.get(FRED_BASE_URL, params=params, timeout=30)
    res.raise_for_status()
    data = res.json()

    observations = data.get("observations", [])
    values = []

    for obs in observations:
        val = _safe_float(obs.get("value"))
        if val is not None:
            values.append(val)
        if len(values) >= 2:
            break

    latest = values[0] if len(values) >= 1 else None
    prev = values[1] if len(values) >= 2 else None
    return latest, prev


def fetch_us_rate_extras():
    """
    米金利の補助データを返す。

    返却キー:
      - 米2年債利回り
      - 米2年債利回り_前回
      - 米2年債利回り_前日比_pct
      - 実質金利(10Y)
      - 実質金利(10Y)_前回
      - 実質金利_前日比
      - 利下げ折込回数
      - 利下げ折込回数_変化
    """
    api_key = os.getenv("FRED_API_KEY")

    if not api_key:
        return {
            "米2年債利回り": None,
            "米2年債利回り_前回": None,
            "米2年債利回り_前日比_pct": None,
            "実質金利(10Y)": None,
            "実質金利(10Y)_前回": None,
            "実質金利_前日比": None,
            "利下げ折込回数": None,
            "利下げ折込回数_変化": None,
        }

    extras = {}

    # =========================
    # 1) 米2年債利回り（DGS2）
    # =========================
    try:
        dgs2_latest, dgs2_prev = _get_latest_two_observations("DGS2", api_key)

        extras["米2年債利回り"] = dgs2_latest
        extras["米2年債利回り_前回"] = dgs2_prev

        if dgs2_latest is not None and dgs2_prev not in [None, 0]:
            extras["米2年債利回り_前日比_pct"] = ((dgs2_latest - dgs2_prev) / dgs2_prev) * 100
        else:
            extras["米2年債利回り_前日比_pct"] = None

    except Exception as e:
        print("[WARN] DGS2 fetch failed:", e)
        extras["米2年債利回り"] = None
        extras["米2年債利回り_前回"] = None
        extras["米2年債利回り_前日比_pct"] = None

    # =========================
    # 2) 実質金利（DFII10）
    # =========================
    try:
        real_latest, real_prev = _get_latest_two_observations("DFII10", api_key)

        extras["実質金利(10Y)"] = real_latest
        extras["実質金利(10Y)_前回"] = real_prev

        if real_latest is not None and real_prev is not None:
            extras["実質金利_前日比"] = real_latest - real_prev
        else:
            extras["実質金利_前日比"] = None

    except Exception as e:
        print("[WARN] DFII10 fetch failed:", e)
        extras["実質金利(10Y)"] = None
        extras["実質金利(10Y)_前回"] = None
        extras["実質金利_前日比"] = None

    # =========================
    # 3) 利下げ折込回数
    # =========================
    # 今回確認できたFRED系列では、FEDFUNDSは月次系列。
    # この実装では保守的に N/A 扱い（None）にしておく。
    extras["利下げ折込回数"] = None
    extras["利下げ折込回数_変化"] = None

    return extras
