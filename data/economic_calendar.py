from datetime import datetime, timedelta
from typing import List, Dict

from config.settings import JST


def fetch_minkabu_economic_events():
    """
    現状は安定動作優先で fallback を返す。
    将来的に実ソースへ差し替える前提。
    """
    now = datetime.now(JST)
    today = now.date()
    yesterday = today - timedelta(days=1)

    return [
        # 昨日の結果
        {
            "event_dt_jst": datetime(yesterday.year, yesterday.month, yesterday.day, 21, 30, tzinfo=JST),
            "event_date_jst": yesterday,
            "country": "US",
            "event_name": "非農業部門雇用者数（NFP）",
            "importance_label": "高",
            "forecast": "180K",
            "actual": "185K",
            "previous": "175K",
            "event_status": "結果",
        },
        {
            "event_dt_jst": datetime(yesterday.year, yesterday.month, yesterday.day, 21, 30, tzinfo=JST),
            "event_date_jst": yesterday,
            "country": "US",
            "event_name": "失業率",
            "importance_label": "高",
            "forecast": "4.0%",
            "actual": "4.0%",
            "previous": "4.1%",
            "event_status": "結果",
        },
        # 今日の予定
        {
            "event_dt_jst": datetime(today.year, today.month, today.day, 8, 50, tzinfo=JST),
            "event_date_jst": today,
            "country": "JP",
            "event_name": "GDP前期比",
            "importance_label": "高",
            "forecast": "0.3%",
            "actual": None,
            "previous": "0.5%",
            "event_status": "予定",
        },
    ]


def split_events_for_mail(events: List[Dict], now_jst):
    today = now_jst.date()
    yesterday = today - timedelta(days=1)

    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)

    if now_jst.weekday() == 0:
        weekly_upcoming = [
            e for e in events
            if e.get("event_date_jst") and monday <= e["event_date_jst"] <= sunday
        ]
        return {
            "mode": "monday",
            "weekly_upcoming": weekly_upcoming,
            "yesterday_events": [],
            "today_events": [],
        }

    yesterday_events = [
        e for e in events
        if e.get("event_date_jst") == yesterday and e.get("event_status") == "結果"
    ]

    today_events = [
        e for e in events
        if e.get("event_date_jst") == today
    ]

    if not today_events:
        today_events = [e for e in events if e.get("event_status") == "予定"]

    return {
        "mode": "daily",
        "weekly_upcoming": [],
        "yesterday_events": yesterday_events,
        "today_events": today_events,
    }
