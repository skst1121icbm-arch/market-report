from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests

JST = ZoneInfo("Asia/Tokyo")

API_URL = "https://api.tradingeconomics.com/calendar?c=guest:guest"

# =========================
# 日本語マッピング
# =========================
COUNTRY_MAP = {
    "United States": "米国",
    "Japan": "日本",
    "Euro Area": "ユーロ圏",
    "China": "中国",
    "United Kingdom": "英国",
}

EVENT_NAME_MAP = {
    "Interest Rate Decision": "政策金利",
    "Consumer Price Index": "消費者物価指数",
    "Inflation Rate": "インフレ率",
    "GDP Growth Rate": "GDP成長率",
    "Non Farm Payrolls": "非農業部門雇用者数",
    "Unemployment Rate": "失業率",
    "Retail Sales": "小売売上高",
    "Trade Balance": "貿易収支",
}

SUPER_IMPORTANT_KEYWORDS = [
    "CPI",
    "消費者物価指数",
    "政策金利",
    "雇用統計",
    "非農業部門雇用者数",
    "失業率",
    "GDP",
]

# =========================
# 共通処理
# =========================
def _safe(v):
    return "" if v is None else str(v).strip()


def _translate_event(name):
    for key, jp in EVENT_NAME_MAP.items():
        if key in name:
            return jp
    return name


def _translate_country(country):
    return COUNTRY_MAP.get(country, country)


def _importance_rank(importance):
    """
    TradingEconomics:
    1 / 2 / 3
    """
    try:
        v = int(importance)
        return v
    except:
        return 1


# =========================
# メイン取得
# =========================
def fetch_economic_events():
    try:
        res = requests.get(API_URL, timeout=15)
        res.raise_for_status()

        data = res.json()

        events = []

        for item in data:
            date_str = item.get("Date")

            if not date_str:
                continue

            # ISO → datetime
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00")).astimezone(JST)

            event_name_en = _safe(item.get("Event"))
            country_en = _safe(item.get("Country"))

            event = {
                "event_date_jst": dt.strftime("%Y-%m-%d"),
                "event_time_jst": dt.strftime("%H:%M"),
                "country": _translate_country(country_en),
                "event_name": _translate_event(event_name_en),
                "forecast": _safe(item.get("Forecast")),
                "actual": _safe(item.get("Actual")),
                "previous": _safe(item.get("Previous")),
                "importance_label": str(item.get("Importance")),
                "importance_rank": _importance_rank(item.get("Importance")),
                "event_status": "予定" if not item.get("Actual") else "結果",
            }

            events.append(event)

        print("[INFO] TradingEconomics events:", len(events))

        return events

    except Exception as e:
        print("[ERROR] TradingEconomics fetch:", e)
        return []


# =========================
# 時刻処理
# =========================
def _parse_event_datetime_jst(event):
    try:
        date_str = event.get("event_date_jst")
        time_str = event.get("event_time_jst", "00:00")

        return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M").replace(tzinfo=JST)

    except Exception:
        return None


# =========================
# 分類処理（既存ロジック維持）
# =========================
def split_events_for_mail(events, now_dt):
    now = now_dt.astimezone(JST)

    today = now.date()
    yesterday = today - timedelta(days=1)

    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    yesterday_events = []
    today_events = []
    week_events = []
    super_important_events = []

    for e in events:
        dt = _parse_event_datetime_jst(e)

        if not dt:
            continue

        event_date = dt.date()

        # 昨日
        if event_date == yesterday and e.get("importance_rank", 0) >= 2:
            yesterday_events.append(e)

        # 今日
        if event_date == today and e.get("importance_rank", 0) >= 2:
            today_events.append(e)

        # 今週
        if today < event_date <= end_of_week and e.get("event_status") == "予定":
            week_events.append(e)

        # 超重要
        name = e.get("event_name", "")
        if event_date >= today and any(k in name for k in SUPER_IMPORTANT_KEYWORDS):
            super_important_events.append(e)

    # ソート
    yesterday_events.sort(key=lambda x: (x["event_time_jst"], x["country"]))
    today_events.sort(key=lambda x: (x["event_time_jst"], x["country"]))
    week_events.sort(key=lambda x: (x["event_date_jst"], x["event_time_jst"], x["country"]))

    print(
        "[INFO]",
        f"yesterday={len(yesterday_events)}",
        f"today={len(today_events)}",
        f"week={len(week_events)}",
        f"super={len(super_important_events)}",
    )

    return {
        "super_important_events": super_important_events,
        "yesterday_events": yesterday_events,
        "today_events": today_events,
        "week_events": week_events,
    }
    
#=========================
# backward compatibility
# =========================
# 旧:Minkabu関数との互換維持
def fetch_minkabu_economic_events():
    return fetch_economic_events()


