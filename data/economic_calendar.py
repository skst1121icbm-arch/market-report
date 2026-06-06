from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# =========================
# TIMEZONE
# =========================
JST = ZoneInfo("Asia/Tokyo")


# =========================
# NFP等の既知補正
# =========================
KNOWN_EVENT_FIXES = [
    {
        "date": "2026-06-05",
        "country": "US",
        "keywords": ["非農業部門雇用者数", "NFP"],
        "forecast": "85K",
        "actual": "172K",
        "previous": "179K",
        "importance": "高",
        "status": "結果",
    },
    {
        "date": "2026-06-05",
        "country": "US",
        "keywords": ["失業率"],
        "forecast": "4.3%",
        "actual": "4.3%",
        "previous": "4.3%",
        "importance": "高",
        "status": "結果",
    },
]


# =========================
# UTIL
# =========================
def _safe(v):
    if v in [None, "", "None"]:
        return ""
    return str(v).strip()


def _normalize_date(v):
    if v is None:
        return ""

    if hasattr(v, "strftime"):
        try:
            return v.strftime("%Y-%m-%d")
        except:
            pass

    s = str(v).strip().replace("/", "-")

    if len(s) >= 10:
        return s[:10]

    return s


def _match(name, keywords):
    name = _safe(name)
    for k in keywords:
        if k in name:
            return True
    return False


# =========================
# FIX LOGIC
# =========================
def apply_fixes(events):
    result = []

    for e in events or []:
        item = dict(e)

        event_date = _normalize_date(item.get("event_date_jst"))
        country = _safe(item.get("country"))
        name = _safe(item.get("event_name"))

        for rule in KNOWN_EVENT_FIXES:
            if (
                event_date == rule["date"]
                and country == rule["country"]
                and _match(name, rule["keywords"])
            ):
                item["forecast"] = rule["forecast"]
                item["actual"] = rule["actual"]
                item["previous"] = rule["previous"]
                item["importance_label"] = rule["importance"]
                item["event_status"] = rule["status"]
                break

        result.append(item)

    return result


# =========================
# MAIN FETCH
# =========================
def fetch_minkabu_economic_events():
    """
    🔴 ここにあなたの既存スクレイピング処理を入れる
    """

    raw_events = []  # ←ここを既存データに置き換え

    # ✅ ここで補正かける
    return apply_fixes(raw_events)


# =========================
# SPLIT（昨日 / 今日）
# =========================
def split_events_for_mail(events, now_jst):
    today = now_jst.date()
    yesterday = today - timedelta(days=1)

    y_list = []
    t_list = []

    for e in events or []:
        d = e.get("event_date_jst")

        date_obj = None

        if hasattr(d, "date"):
            try:
                date_obj = d.date()
            except:
                pass

        if date_obj is None:
            try:
                date_obj = datetime.strptime(_normalize_date(d), "%Y-%m-%d").date()
            except:
                pass

        if date_obj == yesterday:
            y_list.append(e)
        elif date_obj == today:
            t_list.append(e)

    return {
        "yesterday_events": y_list,
        "today_events": t_list,
    }
