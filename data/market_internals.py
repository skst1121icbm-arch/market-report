import pandas as pd


# =========================================
# Breadth（Stooq 無料CSV）
# 提案実装:
# - NYSE Advances
# - NYSE Declines
# を Stooq のCSVから取得する前提
# =========================================
def fetch_market_breadth():
    try:
        adv_url = "https://stooq.com/q/d/l/?s=nyse_advances&f=sd2t2ohlcv&h&e=csv"
        dec_url = "https://stooq.com/q/d/l/?s=nyse_declines&f=sd2t2ohlcv&h&e=csv"

        adv_df = pd.read_csv(adv_url)
        dec_df = pd.read_csv(dec_url)

        adv = int(float(adv_df.iloc[-1]["Close"]))
        dec = int(float(dec_df.iloc[-1]["Close"]))

        total = adv + dec
        ratio = round((adv / total) * 100, 2) if total > 0 else None

        if ratio is None:
            state = "未取得"
        elif ratio >= 60:
            state = "強気（市場全体が上昇）"
        elif ratio <= 40:
            state = "弱気（下落優勢）"
        else:
            state = "中立（方向感なし）"

        return {
            "adv": adv,
            "dec": dec,
            "ratio": ratio,
            "new_high": None,
            "new_low": None,
            "state": state,
        }

    except Exception as e:
        print(f"[WARN] Breadth fetch failed: {e}")
        return {
            "adv": None,
            "dec": None,
            "ratio": None,
            "new_high": None,
            "new_low": None,
            "state": "未取得（Breadth取得失敗）",
        }


# =========================================
# ETFフロー（現状は未取得）
# 実データソース接続時に差し替え
# =========================================
def fetch_etf_flows():
    return {
        "SPY": None,
        "QQQ": None,
        "IWM": None,
        "interpretation": "未取得（ETFフロー未接続）",
    }


# =========================================
# オプション（現状は未取得）
# 実データソース接続時に差し替え
# =========================================
def fetch_options_data():
    return {
        "put_call": None,
        "notable": None,
        "sentiment": "未取得（Options未接続）",
    }


# =========================================
# 注目テーマ自動更新
# セクター強弱 + 市場理由から自動生成
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

    text = " ".join(reasons or [])

    if "公益" in strong and "金利" in text:
        themes.append("ディフェンシブ")

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

    return list(dict.fromkeys(themes))
