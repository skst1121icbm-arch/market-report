from datetime import datetime, timedeltafrom datetime import datetime, timedeltainfo 
import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")


def fetch_minkabu_economic_events():
    return [
        {
            "event_date_jst": "2026-06-05",
            "country": "US",
            "event_name": "非農業部門雇用者数（NFP）",
            "forecast": "85K",
            "actual": "172K",
            "previous": "179K",
            "importance_label": "高",
            "event_status": "結果",
        },
        {
            "event_date_jst": "2026-06-05",
            "country": "US",
            "event_name": "失業率",
            "forecast": "4.3%",
            "actual": "4.3%",
            "previous": "4.3%",
            "importance_label": "高",
            "event_status": "結果",
        }
    ]


def split_events_for_mail(events, now_jst):
    today = now_jst.date()
    yesterday = today - timedelta(days=1)

    y = []
    t = []

    for e in events:
        try:
            dt = datetime.strptime(e["event_date_jst"], "%Y-%m-%d").date()
        except:
            continue

        if dt == yesterday:
            y.append(e)
        elif dt == today:
            t.append(e)

    return {
        "yesterday_events": y,
        "today_events": t,
    }
