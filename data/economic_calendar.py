from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import re
import requests
from bs4 import BeautifulSoup

JST = ZoneInfo("Asia/Tokyo")

INVESTING_CALENDAR_URL = "https://jp.investing.com/economic-calendar"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7",
}

# 通貨コード→国コード（必要に応じて拡張）
CURRENCY_TO_COUNTRY = {
    "USD": "US",
    "JPY": "JP",
    "EUR": "EU",
    "GBP": "UK",
    "CAD": "CA",
    "AUD": "AU",
    "NZD": "NZ",
    "CHF": "CH",
    "CNY": "CN",
    "CNH": "CN",
    "HKD": "HK",
    "KRW": "KR",
    "SGD": "SG",
    "INR": "IN",
    "BRL": "BR",
    "THB": "TH",
    "TWD": "TW",
    "ZAR": "ZA",
}

# 必要国だけに絞るならここを変更
TARGET_COUNTRIES = {"US", "JP"}


# =========================
# UTIL
# =========================
def _safe(v):
    if v in [None, "", "None"]:
        return ""
    return str(v).strip()


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\u3000", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _to_iso_date_from_jp(text: str) -> str:
    """
    例:
      2026年6月5日金曜日 -> 2026-06-05
      2026年6月6日 土曜日 -> 2026-06-06
    """
    m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", text)
    if not m:
        return ""
    yyyy, mm, dd = m.groups()
    return f"{int(yyyy):04d}-{int(mm):02d}-{int(dd):02d}"


def _importance_to_label(raw_importance: str) -> str:
    """
    InvestingのHTMLは重要性列が記号/アイコンになっていることがあるので、
    とりあえず文字列が入っていればそのまま、なければ空。
    """
    txt = _safe(raw_importance)
    if not txt:
        return ""
    return txt


def _country_from_currency(currency: str) -> str:
    return CURRENCY_TO_COUNTRY.get(_safe(currency), _safe(currency))


# =========================
# PARSER
# =========================
def _parse_calendar_rows(html: str):
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.find_all("tr")

    events = []
    current_date = ""

    for tr in rows:
        cells = tr.find_all(["td", "th"])
        texts = [_normalize_text(c.get_text(" ", strip=True)) for c in cells]
        texts = [t for t in texts if t]

        if not texts:
            continue

        # 日付見出し行
        if len(texts) == 1 and re.search(r"\d{4}年\d{1,2}月\d{1,2}日", texts[0]):
            current_date = _to_iso_date_from_jp(texts[0])
            continue

        # ヘッダー行スキップ
        header_join = " ".join(texts)
        if "時間" in header_join and "通貨" in header_join and "結果" in header_join:
            continue

        # データ行想定
        # 代表的には:
        # [時間, 通貨, 重要性, 指標, 結果, 予想, 前回]
        # または重要性が省略されて:
        # [時間, 通貨, 指標, 結果, 予想, 前回]
        if len(texts) >= 7:
            time_text = texts[0]
            currency = texts[1]
            importance = texts[2]
            event_name = texts[3]
            actual = texts[4]
            forecast = texts[5]
            previous = texts[6]
        elif len(texts) == 6:
            time_text = texts[0]
            currency = texts[1]
            importance = ""
            event_name = texts[2]
            actual = texts[3]
            forecast = texts[4]
            previous = texts[5]
        else:
            continue

        # 時刻っぽくない行は除外
        if not re.match(r"^\d{2}:\d{2}$", _safe(time_text)):
            continue

        country = _country_from_currency(currency)

        if TARGET_COUNTRIES and country not in TARGET_COUNTRIES:
            continue

        # 当日ついていない行は採用しない
        if not current_date:
            continue

        item = {
            "event_date_jst": current_date,
            "event_time_jst": time_text,
            "country": country,
            "event_name": event_name,
            "forecast": forecast,
            "actual": actual,
            "previous": previous,
            "importance_label": _importance_to_label(importance),
            "event_status": "結果" if _safe(actual) not in ["", "N/A", "-"] else "予定",
        }
        events.append(item)

    return events


# =========================
# FETCH
# =========================
def fetch_investing_economic_events():
    res = requests.get(INVESTING_CALENDAR_URL, headers=HEADERS, timeout=30)
    res.raise_for_status()

    events = _parse_calendar_rows(res.text)

    # デバッグしたいときは有効化
    # print("[DEBUG] investing events =", len(events))

    return events


# 既存runner互換のため関数名は維持
def fetch_minkabu_economic_events():
    return fetch_investing_economic_events()


# =========================
# SPLIT
# =========================
def split_events_for_mail(events, now_jst):
    today = now_jst.date()
    yesterday = today - timedelta(days=1)

    yesterday_events = []
    today_events = []

    for e in events or []:
        d = _safe(e.get("event_date_jst"))
        if not d:
            continue

        try:
            dt = datetime.strptime(d, "%Y-%m-%d").date()
        except Exception:
            continue

        if dt == yesterday:
            yesterday_events.append(e)
        elif dt == today:
            today_events.append(e)

    return {
        "yesterday_events": yesterday_events,
        "today_events": today_events,
    }
