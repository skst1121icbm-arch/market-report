from datetime import datetime, timedelta
from typing import List, Dict
import requests
from bs4 import BeautifulSoup

from config.settings import JST


# =========================================
# みんかぶ 経済指標取得（BS4版・安定）
# =========================================
def fetch_minkabu_economic_events() -> List[Dict]:
    url = "https://fx.minkabu.jp/indicators"

    headers = {
        "User-Agent": "Mozilla/5.0",
    }

    res = requests.get(url, headers=headers, timeout=10)
    html = res.text

    soup = BeautifulSoup(html, "html.parser")

    events = []

    tables = soup.find_all("table")
    print(f"[DEBUG] tables found (bs4) = {len(tables)}")

    current_date = None

    for table in tables:
        # 日付（caption）
        caption = table.find("caption")
        if caption:
            try:
                # 例: 2026年06月08日(月)
                text = caption.get_text(strip=True)
                dt = datetime.strptime(text[:10], "%Y年%m月%d日")
                current_date = dt.date()
                print(f"[DEBUG] detected date = {current_date}")
            except Exception:
                continue

        rows = table.find_all("tr")

        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 5:
                continue

            try:
                time_text = cols[0].get_text(strip=True)
                country_text = cols[1].get("data_country", "")
                country_fallback = cols[1].text.strip()

                # 国コード優先
                country = country_text if country_text else country_fallback

                event_name = cols[2].get_text(strip=True)
                previous = cols[5].get_text(strip=True)
                forecast = cols[6].get_text(strip=True) if len(cols) > 6 else None
                actual = cols[7].get_text(strip=True) if len(cols) > 7 else None

                if not event_name:
                    continue

                # 日本・米国のみ
                if country not in ["JP", "US"]:
                    continue

                events.append({
                    "event_dt_jst": None,
                    "event_date_jst": current_date,
                    "country": country,
                    "event_name": event_name,
                    "importance_label": "中",
                    "forecast": forecast,
                    "actual": actual,
                    "previous": previous,
                })

            except Exception:
                continue

    print(f"[DEBUG] minkabu events normalized = {len(events)}")

    for i, e in enumerate(events[:5], start=1):
        print(f"[DEBUG] MINKABU EVENT SAMPLE {i}: {e}")

    return events


# =========================================
# メール用分割（そのまま）
# =========================================
def split_events_for_mail(events, now_jst):
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
        if e.get("event_date_jst") == yesterday
    ]

    today_events = [
        e for e in events
        if e.get("event_date_jst") == today
    ]

    # fallback（0件回避）
    if not yesterday_events and not today_events:
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        fallback_events = [
            e for e in events
            if e.get("event_date_jst") and week_start <= e["event_date_jst"] <= week_end
        ]
        today_events = fallback_events[:10]

    return {
        "mode": "daily",
        "weekly_upcoming": [],
        "yesterday_events": yesterday_events,
        "today_events": today_events,
    }
