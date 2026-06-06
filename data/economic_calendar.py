from datetime import datetime, timedelta

def _safe(v):
    if v in [None, "", "None"]:
        return ""
    return str(v).strip()


def split_events_for_mail(events, now_jst):
    today = now_jst.date()
    yesterday = today - timedelta(days=1)

    # 今週（月曜〜日曜）
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    yesterday_events = []
    today_events = []
    week_events = []

    for e in events or []:
        d = _safe(e.get("event_date_jst"))
        if not d:
            continue

        try:
            dt = datetime.strptime(d, "%Y-%m-%d").date()
        except Exception:
            continue

        # ===== 昨日 =====
        if dt == yesterday:
            yesterday_events.append(e)

        # ===== 本日 =====
        elif dt == today:
            today_events.append(e)

        # ===== 今週（重要・未来のみ）=====
        if (
            today < dt <= end_of_week
            and e.get("event_status") != "結果"
            and (
                "高" in str(e.get("importance_label"))
                or "中" in str(e.get("importance_label"))
            )
        ):
            week_events.append(e)

    return {
        "yesterday_events": yesterday_events,
        "today_events": today_events,
        "week_events": week_events,
    }
