from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")

# =========================
# NFPなど補正ルール
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
    },
    {
        "date": "2026-06-05",
        "country": "US",
        "keywords": ["失業率"],
        "forecast": "4.3%",
        "actual": "4.3%",
        "previous": "4.3%",
        "importance_label": "高",
        "event_status": "結果",
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

    # datetime対応
    try:
        if hasattr(v, "strftime"):
            return v.strftime("%Y-%m-%d")
    except:
        pass

    s = str(v).replace("/", "-").strip()
    return s[:10] if len(s) >= 10 else s


def _match(name, keywords):
    name = _safe(name)
    return any(k in name for k in keywords)


# =========================
# FIX
# =========================
def apply_fixes(events):
    result = []

    for e in events or []:
        item = dict(e)

        date = _normalize_date(item.get("event_date_jst"))
        country = _safe(item.get("country"))
        name = _safe(item.get("event_name"))

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
                break

        result.append(item)

    return result


# =========================
# メイン取得
# =========================
def fetch_minkabu_economic_events():
    """
    ✅ 重要：
    ここに既存のスクレイピング処理を入れる
    """

    # 🔽 例（あなたの既存コードに置き換える）
    raw_events = []

    # ✅ データが無いときはそのまま返す
    if not raw_events:
        return []

    return apply_fixes(raw_events)


# =========================
# 日付分割
# =========================
def split_events_for_mail(events, now_jst):
    today = now_jst.date()
    yesterday = today - timedelta(days=1)

    yesterday_events = []
    today_events = []

    for e in events or []:
        d = e.get("event_date_jst")

        date_obj = None

        # datetime型対応
        if hasattr(d, "date"):
            try:
                date_obj = d.date()
            except:
                pass

        # string型対応
        if date_obj is None:
            try:
                date_obj = datetime.strptime(
                    _normalize_date(d), "%Y-%m-%d"
                ).date()
            except:
                pass

        if date_obj == yesterday:
            yesterday_events.append(e)
        elif date_obj == today:
            today_events.append(e)

    return {
        "yesterday_events": yesterday_events,
        "today_events": today_events,
    }
