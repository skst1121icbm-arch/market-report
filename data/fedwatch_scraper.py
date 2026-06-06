import re
import json
import math
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
    if s in ["", "None", "nan", "-", "—"]:
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
      "350-375" -> 3.625
      "3.50-3.75" -> 3.625
      "425-450" -> 4.375
    """
    if not range_text:
        return None
    s = str(range_text).strip().replace(" ", "")
    m = re.match(r"^(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)$", s)
    if not m:
        return None

    a, b = float(m.group(1)), float(m.group(2))

    # 350-375 のようなbps表記っぽければ % に直す
    if a > 50 and b > 50:
        a = a / 100.0
        b = b / 100.0

    return (a + b) / 2.0


def _expected_midpoint_from_table(df: pd.DataFrame, prob_col: str):
    """
    表の各ターゲットレンジ × 確率から期待ミッドポイントを計算する
    """
    df = _normalize_columns(df)

    # ターゲットレンジ列候補
    range_col = None
    for c in df.columns:
        cl = c.lower()
        if "target" in cl and "rate" in cl:
            range_col = c
            break
        if "rate" in cl and ("range" in cl or "target" in cl):
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

    # %表記の確率なら 100 で割らなくても比率計算では相殺される
    return weighted / total_prob


def _find_probability_table_from_html(html: str):
    """
    公開ページのHTMLから、FedWatchの確率表っぽいテーブルを探す。
    heuristic:
      - 'Target Rate' 系の列
      - Current / 1 Day Ago / 1 Week Ago / 1 Month Ago 系の列
    """
    try:
        tables = pd.read_html(html)
    except Exception:
        return None

    for df in tables:
        df = _normalize_columns(df)
        cols = [c.lower() for c in df.columns]

        has_target = any(("target" in c and "rate" in c) for c in cols) or any("range" in c for c in cols)
        has_prob = any("current" in c for c in cols) or any("1 day" in c for c in cols) or any("one day" in c for c in cols)

        if has_target and has_prob:
            return df

    return None


def _extract_embedded_json_tables(html: str):
    """
    ページ内埋め込みJSONらしき<script>から表データらしきものを探す補助。
    ※ ページ構造変更に強くするための保険。見つからなければ None。
    """
    soup = BeautifulSoup(html, "html.parser")
    scripts = soup.find_all("script")

    # 完全汎用のため、JSONっぽい script をざっくり探索
    candidate_texts = []
    for sc in scripts:
        txt = sc.string or sc.get_text() or ""
        txt = txt.strip()
        if not txt:
            continue
        if "Current" in txt and "Target" in txt and ("FedWatch" in txt or "probab" in txt.lower()):
            candidate_texts.append(txt)

    # ここでは無理に構造断定せず、今回は fallback 用に何もしない
    return None


def fetch_fedwatch_rate_cuts_scrape(current_target_midpoint=3.625):
    """
    非公式スクレイピング案:
      - 公開ページから確率表を探す
      - Current / 1 Day Ago の期待ミッドポイントを計算
      - 現在のFFターゲット・ミッドポイントとの差分を25bp刻みで
        「利下げ折込回数」に換算する

    戻り値:
      (cuts_current, cuts_change)
        - cuts_current: 現在時点の想定利下げ回数
        - cuts_change: 前日比変化
    """
    try:
        res = requests.get(FEDWATCH_URL, headers=HEADERS, timeout=30)
        res.raise_for_status()
        html = res.text
    except Exception as e:
        print("[WARN] FedWatch page fetch failed:", e)
        return None, None

    df = _find_probability_table_from_html(html)

    if df is None:
        # 埋め込みJSON fallback（今回は保険のみ）
        _extract_embedded_json_tables(html)
        print("[WARN] FedWatch probability table not found in public HTML")
        return None, None

    cols = [str(c).strip() for c in df.columns]

    # Current列候補
    current_col = None
    day_ago_col = None

    for c in cols:
        cl = c.lower()
        if current_col is None and "current" in cl:
            current_col = c
        if day_ago_col is None and ("1 day" in cl or "one day" in cl):
            day_ago_col = c

    if current_col is None:
        print("[WARN] FedWatch current probability column not found")
        return None, None

    implied_current = _expected_midpoint_from_table(df, current_col)
    implied_prev = _expected_midpoint_from_table(df, day_ago_col) if day_ago_col else None

    if implied_current is None:
        print("[WARN] FedWatch implied current midpoint could not be computed")
        return None, None

    # 25bp単位で換算
    # 現在midpointより低ければ「利下げ折込」
    cuts_current = round((current_target_midpoint - implied_current) / 0.25, 2)

    # マイナス（利上げ織り込み）は 0 未満になり得るので、そのまま返す
    cuts_change = None
    if implied_prev is not None:
        prev_cuts = round((current_target_midpoint - implied_prev) / 0.25, 2)
        cuts_change = round(cuts_current - prev_cuts, 2)

    return cuts_current, cuts_change


def fetch_fedwatch_rate_cuts():
    """
    将来差し替えやすいラッパー
    """
    return fetch_fedwatch_rate_cuts_scrape(current_target_midpoint=3.625)
