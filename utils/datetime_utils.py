from datetime import datetime, timedelta
from config.settings import JST

def now_jst():
    return datetime.now(JST)

def is_monday():
    return now_jst().weekday() == 0

def within_last_24h(dt):
    now = now_jst()
    return (now - timedelta(hours=24)) <= dt <= now

def within_next_24h(dt):
    now = now_jst()
    return now < dt <= (now + timedelta(hours=24))

def within_this_week(dt):
    now = now_jst()
    start = now - timedelta(days=now.weekday())
    end = start + timedelta(days=6)
    return start.date() <= dt.date() <= end.date()