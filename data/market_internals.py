import re
import requests
import pandas as pd
from bs4 import BeautifulSoup


REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


# =========================================================
# ① Breadth（無料簡易版: Stooq CSV）
# =========================================================
def fetch_market_breadth():
    """
    非公式の無料CSV取得。
    取得できない場合は未取得として返す。
    """
    try:
        adv_url = "https://stooq.com/q/d/l/?s=nyadv&f=sd2t2ohlcv&h&e=csv"
        dec_url = "https://stooq.com/q/d/l/?s=nydec&f=sd2t2ohlcv&h&e=csv"

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


# =========================================================
# ② ETFフロー（無料簡易版: etf.com 公開ページを非公式スクレイピング）
# ソースでは etf.com に Flow Tool があることは確認できますが、
# 公式API仕様ではなく、以下は提案実装です。[2](https://bing.com/search?q=how+to+create+folder+in+github+web+ui+steps)
# =========================================================
def _extract_first_flow_for_ticker(page_text: str, ticker: str):
    """
    ページテキストから ticker 周辺の $xxxM / $xxxB をゆるく拾う提案実装
    """
    if not page_text:
        return None

    # 例: "SPY ... $1.2B" / "QQQ ... -$0.5B"
    patterns = [
        rf"{ticker}[^$\-+]*([+\-]?\$?\d+(?:\.\d+)?[MB])",
        rf"{ticker}.*?([+\-]?\$?\d+(?:\.\d+)?[MB])",
    ]

    for p in patterns:
        m = re.search(p, page_text, flags=re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(1).replace("$", "")

    return None


def _proxy_flow_from_market_rows(market_rows):
    """
    etf.com で取れない時の予備:
    指数の前日比を「流れの proxy」として出す
    """
    lookup = {r["label"]: r for r in market_rows} if market_rows else {}

    def conv(label):
        row = lookup.get(label)
        if not row:
            return None
        ch = row.get("change_pct")
        if ch is None:
            return None
        sign = "+" if ch > 0 else ""
        return f"{sign}{ch:.2f}%"

    spy = conv("S&P500")
    qqq = conv("NASDAQ")
    iwm = conv("Russell2000")

    if spy is None and qqq is None and iwm is None:
        interpretation = "未取得（ETFフロー未接続）"
    else:
        interpretation = "価格変化を proxy とした簡易フロー推定"

    return {
        "SPY": spy,
        "QQQ": qqq,
        "IWM": iwm,
        "interpretation": interpretation,
    }


def fetch_etf_flows(market_rows=None):
    """
    1) etf.com の公開ページを非公式に読む
    2) 取れなければ market_rows を使って proxy を返す
    """
    try:
        url = "https://www.etf.com/etfanalytics/etf-fund-flows-tool"
        res = requests.get(url, headers=REQUEST_HEADERS, timeout=20)
        res.raise_for_status()

        text = BeautifulSoup(res.text, "html.parser").get_text(" ", strip=True)

        spy = _extract_first_flow_for_ticker(text, "SPY")
        qqq = _extract_first_flow_for_ticker(text, "QQQ")
        iwm = _extract_first_flow_for_ticker(text, "IWM")

        if spy or qqq or iwm:
            interpretation = "etf.com 公開ページからの簡易抽出"
            return {
                "SPY": spy,
                "QQQ": qqq,
                "IWM": iwm,
                "interpretation": interpretation,
            }

    except Exception as e:
        print(f"[WARN] ETF flow scrape failed: {e}")

    return _proxy_flow_from_market_rows(market_rows)


# =========================================================
# ③ Options / Put-Call（無料簡易版: Cboe 公開ページを非公式に読む）
# ソースでは Cboe Historical Data と Put/Call Ratio archive の存在を確認できます。[1](https://qiita.com/kura_yu/items/9e3fcbc8e0f6d55bbf05)
# ただし、以下は公式API仕様ではない提案実装です。
# =========================================================
def fetch_options_data(market_rows=None):
    try:
        url = "https://www.cboe.com/us/options/market_statistics/historical_data/"
        res = requests.get(url, headers=REQUEST_HEADERS, timeout=20)
        res.raise_for_status()

        text = BeautifulSoup(res.text, "html.parser").get_text(" ", strip=True)

        # "Put/Call Ratio" 周辺の数値を雑に拾う
        m = re.search(r"Put/?Call Ratio[^0-9]*([0-9]+(?:\.[0-9]+)?)", text, flags=re.IGNORECASE)
        put_call = float(m.group(1)) if m else None

        notable = "Cboe 公開ページ由来の簡易抽出"
        if put_call is None:
            sentiment = "未取得（Cboeページから比率抽出できず）"
        else:
            if put_call < 0.8:
                sentiment = "強気"
            elif put_call > 1.1:
                sentiment = "弱気"
            else:
                sentiment = "中立"

        if put_call is not None:
            return {
                "put_call": round(put_call, 2),
                "notable": notable,
                "sentiment": sentiment,
            }

    except Exception as e:
        print(f"[WARN] Options scrape failed: {e}")

    # fallback: VIXベース簡易センチメント
    if market_rows:
        for r in market_rows:
            if r["label"] == "VIX":
                v = r.get("value")
                if v is not None:
                    try:
                        vv = float(v)
                        if vv < 15:
                            sentiment = "強気"
                        elif vv > 20:
                            sentiment = "弱気"
                        else:
                            sentiment = "中立"
                        return {
                            "put_call": None,
                            "notable": "VIXベース推定",
                            "sentiment": sentiment,
                        }
                    except Exception:
                        pass

    return {
        "put_call": None,
        "notable": None,
        "sentiment": "未取得（Options未接続）",
    }


# =========================================================
# ④ 注目テーマの自動更新
# =========================================================
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
