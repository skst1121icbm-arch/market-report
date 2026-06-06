from datetime import datetime, timedelta
from zone# =========================================from zoneinfo import ZoneInfo
# 既知の重要指標の補正値
# =========================================
# 2026-06-05 発表（5月分）
# NFP: Actual 172K / Forecast 85K / Previous 179K
# Unemployment Rate: Actual 4.3% / Previous 4.3%
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
# 文字列正規化
# =========================================
def _norm_text(v):
    if v is None:
        return ""
    return str(v).strip()


def _norm_date_str(v):
    """
    date / datetime / 文字列 を YYYY-MM-DD に寄せる
    """
    if v is None:
        return ""

    # datetime/date
    try:
        if hasattr(v, "strftime"):
            return v.strftime("%Y-%m-%d")
    except Exception:
        pass

    s = str(v).strip()

    # 2026-06-05 / 2026/06/05
    s = s.replace("/", "-")
    if len(s) >= 10:
        return s[:10]

    return s


def _name_matches(event_name, keywords):
    name = _norm_text(event_name)
    return any(k in name for k in keywords)


# =========================================
# 補正
# =========================================
def apply_known_event_fixes(events):
    """
    スクレイピング済みイベントに対して既知の補正を適用
    """
    fixed = []

    for e in events or []:
        item = dict(e)

        event_date_str = _norm_date_str(item.get("event_date_jst"))
        country = _norm_text(item.get("country"))
        event_name = _norm_text(item.get("event_name"))

        for rule in KNOWN_EVENT_FIXES:
            if (
                event_date_str == rule["event_date_jst"]
                and country == rule["country"]
                and _name_matches(event_name, rule["name_keywords"])
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
# あなたの既存スクレイピング結果をここに通す想定
# =========================================
def fetch_minkabu_economic_events():
    """
    既存のスクレイパーが返す events を最後に補正する。
    ここでは既存実装を残したいので、raw_events を返す部分だけ
    あなたの今のコードに置き換えてください。
    """

    # -------------------------------------
    # ここはあなたの既存取得処理に置き換え
    # 例:
    # raw_events = existing_scrape_minkabu()
    # -------------------------------------
    raw_events = []

    # 最後に補正をかける
    return apply_known_event_fixes(raw_events)


# =========================================
# メール表示用に昨日 / 本日へ分ける
# =========================================
def split_events_for_mail(events, now_jst):
    """
    events の event_date_jst を元に
    昨日 / 本日へ分割する
    """
    today = now_jst.date()
    yesterday = today - timedelta(days=1)

    yesterday_events = []
    today_events = []

    for e in events or []:
        d = e.get("event_date_jst")

        # datetime/date/string を安全に date 化
        date_obj = None

        if hasattr(d, "date"):
            try:
                date_obj = d.date()
            except Exception:
                date_obj = None
        elif hasattr(d, "year") and hasattr(d, "month") and hasattr(d, "day"):
            date_obj = d
        else:
            ds = _norm_date_str(d)
            try:
                date_obj = datetime.strptime(ds, "%Y-%m-%d").date()
            except Exception:
                date_obj = None

        if date_obj == yesterday:
            yesterday_events.append(e)
        elif date_obj == today:
            today_events.append(e)

    return {
        "yesterday_events": yesterday_events,
        "today_events": today_events,
    }

JST = ZoneInfo("Asia/Tokyo")


