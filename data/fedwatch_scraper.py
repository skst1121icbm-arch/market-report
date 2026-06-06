import re
import requests
import pandas as pd
from bs4 import BeautifulSoup


FEDWATCH_URL = "https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,ja;q=0.8",
}


def _safe_float(v):
    if v is None:
        return None
    s = str(v).strip().replace("%", "").replace(",", "")
    if s in ["", "None", "nan", "-", "—", "."]:
        return None
    try:
        return float(s)
    except Exception:
        return None


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _range_midpoint(range_text: str):
    """
    例:
      "350-375"   -> 3.625
      "3.50-3.75" -> 3.625
      "425-450"   -> 4.375
    """
    if not range_text:
        return None

    s = str(range_text).strip()
    s = s.replace(" ", "")

    m = re.match(r"^(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)$", s)
    if not m:
        return None

    a = float(m.group(1))
    b = float(m.group(2))

    # 350-375 のような表記なら % に戻す
    if a > 50 and b > 50:
        a = a / 100.0
        b = b / 100.0

    return (a + b) / 2.0


def _expected_midpoint_from_table(df: pd.DataFrame, prob_col: str):
    """
    Target Rate Range × Probability から期待ミッドポイントを計算
    """
    df = _normalize_columns(df)

    range_col = None
    for c in df.columns:
        cl = c.lower()
        if "target" in cl and "rate" in cl:
            range_col = c
            break
        if "range" in cl:
            range_col = c
            break

    if range_col is None or prob_col not in df.columns:
        return None

    total_prob = 0.0
    weighted = 0.0

    for _, row in df.iterrows():
        midpoint = _range_midpoint(row.get(range_col))
        prob = _safe_float(row.get(prob_col))

        if midpoint is None or prob is None:
            continue

        total_prob += prob
        weighted += midpoint * prob

    if total_prob <= 0:
        return None

    return weighted / total_prob


def _find_probability_table_from_html(html: str):
    """
    公開ページ内の確率表らしき table を拾う。
    pandas.read_html ベースの best-effort 実装。
    """
    try:
        tables = pd.read_html(html)
    except Exception as e:
        print("[WARN] pd.read_html failed:", e)
        return None

    print("DEBUG FedWatch tables:", len(tables))

    for idx, df in enumerate(tables):
        df = _normalize_columns(df)
        cols = [str(c) for c in df.columns]

        print(f"DEBUG table[{idx}] cols =", cols)

        # 緩めに判定
        has_target = any("target" in str(c).lower() for c in cols) or any("range" in str(c).lower() for c in cols)
        if has_target:
            return df

    return None


def _detect_probability_columns(df: pd.DataFrame):
    """
    Current / 1 day ago 列をゆるく判定する
    """
    cols = [str(c).strip() for c in df.columns]

    current_col = None
    day_ago_col = None

    for c in cols:
        cl = c.lower()

        # Current
        if current_col is None and "current" in cl:
            current_col = c

        # 1 day ago の複数表記に対応
        if day_ago_col is None:
            if (
                "1 day" in cl
                or "one day" in cl
                or "day ago" in cl
                or "previous day" in cl
                or "1d" in cl
            ):
                day_ago_col = c

    return current_col, day_ago_col


def fetch_fedwatch_rate_cuts_scrape(current_target_midpoint=3.625):
    """
    FedWatch公開ページから利下げ折込回数を推定する。

    戻り値:
        (cuts_current, cuts_change)

    例:
        cuts_current = 2.25
        cuts_change  = -0.25
    """
    try:
        res = requests.get(FEDWATCH_URL, headers=HEADERS, timeout=30)
        res.raise_for_status()
        html = res.text
    except Exception as e:
        print("[WARN] FedWatch page fetch failed:", e)
        return None, None

    print("DEBUG FedWatch HTML length:", len(html))

    df = _find_probability_table_from_html(html)
    print("DEBUG table found:", df is not None)

    if df is None:
        print("[WARN] FedWatch probability table not found")
        return None, None

    current_col, day_ago_col = _detect_probability_columns(df)
    print("DEBUG current_col:", current_col)
    print("DEBUG day_ago_col:", day_ago_col)

    if current_col is None:
        print("[WARN] FedWatch current probability column not found")
        return None, None

    implied_current = _expected_midpoint_from_table(df, current_col)
    implied_prev = _expected_midpoint_from_table(df, day_ago_col) if day_ago_col else None

    print("DEBUG implied_current:", implied_current)
    print("DEBUG implied_prev:", implied_prev)

    if implied_current is None:
        print("[WARN] FedWatch implied current midpoint not computed")
        return None, None

    # 25bpごとの利下げ回数換算
    cuts_current = round((current_target_midpoint - implied_current) / 0.25, 2)

    if implied_prev is not None:
        prev_cuts = round((current_target_midpoint - implied_prev) / 0.25, 2)
        cuts_change = round(cuts_current - prev_cuts, 2)
    else:
        # 前日が拾えないときは N/Aにせず 0.0 扱いにしたいならここを変える
        cuts_change = None

    return cuts_current, cuts_change


def fetch_fedwatch_rate_cuts():
    """
    将来 API 版へ差し替えやすいラッパー
    """
    return fetch_fedwatch_rate_cuts_scrape(current_target_midpoint=3.625)
