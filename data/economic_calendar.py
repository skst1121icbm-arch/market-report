from datetime import datetime, timedelta
from zoneinfo import Zone:from zoneinfo import ZoneInfo
        item = dict(e)

        date = _normalize_date(item.get("event_date_jst"))
        country = item.get("country", "")
        name = item.get("event_name", "")

        for rule in KNOWN_EVENT_FIXES:
            if (
                date == rule["date"]
                and country == rule["country"]
                and _match(name, rule["keywords"])
            ):
                item.update({
                    "forecast": rule["forecast"],
                    "actual": rule["actual"],
                    "previous": rule["previous"],
                    "importance_label": rule["importance_label"],
                    "event_status": rule["event_status"],
                })

        result.append(item)

    return result


# =========================
# メイン
# =========================
def fetch_minkabu_economic_events():
    raw_events = scrape_minkabu()

    print("DEBUG: events count =", len(raw_events))

    return apply_fixes(raw_events)


# =========================
# 日付分割
# =========================
def split_events_for_mail(events, now_jst):
    today = now_jst.date()
    yesterday = today - timedelta(days=1)

    y_events = []
    t_events = []

    for e in events:
        d = e.get("event_date_jst")

        try:
            dt = datetime.strptime(d, "%Y-%m-%d").date()
        except:
            continue

        if dt == yesterday:
            y_events.append(e)
        elif dt == today:
            t_events.append(e)

    return {
        "yesterday_events": y_events,
        "today_events": t_events,
    }
``
import requests
from bs4 import BeautifulSoup

JST = ZoneInfo("Asia/Tokyo")


# =========================
# NFP補正
# =========================
KNOWN_EVENT_FIXES = [
    {
        "date": "2026-06-05",
        "country": "US",
        "keywords": ["非農業部門雇用者数", "NFP"],
        "forecast": "85K",
        "actual": "172K",
        "previous": "179K",
        "importance_label": "高",
        "event_status": "結果",
    }
]


# =========================
# 共通関数
# =========================
def _safe(v):
    if not v:
        return ""
    return str(v).strip()


def _normalize_date(v):
    if hasattr(v, "strftime"):
        return v.strftime("%Y-%m-%d")

    s = str(v).replace("/", "-")
    return s[:10]


def _match(name, keywords):
    return any(k in name for k in keywords)


# =========================
# Minkabu取得
# =========================
def scrape_minkabu():
    url = "https://minkabu.jp/indicators"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    res = requests.get(url, headers=headers)
    res.raise_for_status()

    soup = BeautifulSoup(res.text, "html.parser")

    rows = soup.select("table tr")

    events = []

    current_date = datetime.now(JST).strftime("%Y-%m-%d")

    for r in rows:
        cols = r.find_all("td")
        if len(cols) < 6:
            continue

        try:
            event = {
                "event_date_jst": current_date,
                "country": _safe(cols[0].text),
                "event_name": _safe(cols[1].text),
                "forecast": _safe(cols[2].text),
                "actual": _safe(cols[3].text),
                "previous": _safe(cols[4].text),
                "importance_label": _safe(cols[5].text),
                "event_status": "結果",
            }

            events.append(event)

        except Exception:
            continue

    return events


# =========================
# 補正
# =========================
def apply_fixes(events):
    result = []

