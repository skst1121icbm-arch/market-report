from datetime import datetime, timedeltafrom datetime import========
# 既知の重要指標の補正値（NFPなど）
# =========================================
KNOWN_EVENT_FIXES = [
    {
        "event_date_jst": "2026-06-05",
        "country": "US",
        "name_keywords": ["非農業部門雇用者数", "NFP"],
        "forecast": "85K",
        "actual": "172K",
        "previous": "179K",
        "importance_label": "高",
        "event_status": "結果",
    },
    {
        "event_date_jst": "2026-06-05",
        "country": "US",
        "name_keywords": ["失業率"],
        "forecast": "4.3%",
        "actual": "4.3%",
        "previous": "4.3%",
        "importance_label": "高",
        "event_status": "結果",
    },
]


# =========================================
# 文字正規化
# =========================================
def _safe(v):
    if v in [None, "", "None"]:
        return ""
    return str(v).strip()


def _norm_date_str(v):
    if v is None:
        return ""

    # datetime / date
    if hasattr(v, "strftime"):
        try:
            return v.strftime("%Y-%m-%d")
        except:
            pass

    s = str(v).strip().replace("/", "-")

    if len(s) >= 10:
        return s[:10]

    return s


def _name_matches(name, keywords):
    name = _safe(name)
    return any(k in name for k in keywords)


# =========================================
# 補正処理
# =========================================
def apply_known_event_fixes(events):
    fixed = []

    for e in events or []:
        item = dict(e)

        event_date = _norm_date_str(item.get("event_date_jst"))
        country = _safe(item.get("country"))
        name = _safe(item.get("event_name"))

        for rule in KNOWN_EVENT_FIXES:
            if (
                event_date == rule["event_date_jst"]
                and country == rule["country"]
                and _name_matches(name, rule["name_keywords"])
            ):
                item["forecast"] = rule["forecast"]
                item["actual"] = rule["actual"]
                item["previous"] = rule["previous"]
                item["importance_label"] = rule["importance_label"]
                item["event_status"] = rule["event_status"]
                break

        fixed.append(item)

    return fixed


# =========================================
# メイン：イベント取得（既存と繋ぐ）
# =========================================
def fetch_minkabu_economic_events():
    """
    ここにあなたの既存スクレイピングコードを入れる
    最後に補正をかけるだけ
    """

    # ✅ あなたの既存処理に置き換える
    raw_events = []

    # ✅ NFP補正適用
    return apply_known_event_fixes(raw_events)


# =========================================
# 昨日 / 本日に分割
# =========================================
def split_events_for_mail(events, now_jst):
    today = now_jst.date()
    yesterday = today - timedelta(days=1)

    y_events = []
    t_events = []

    for e in events or []:
        d = e.get("event_date_jst")

        date_obj = None

        # datetime系
        if hasattr(d, "date"):
            try:
                date_obj = d.date()
            except:
                pass

        # string
        if date_obj is None:
            try:
                date_obj = datetime.strptime(_norm_date_str(d), "%Y-%m-%d").date()
            except:
                pass

        if date_obj == yesterday:
            y_events.append(e)
        elif date_obj == today:
            t_events.append(e)

    return {
        "yesterday_events": y_events,
        "today_events": t_events,
    }
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")


