from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests

JST = ZoneInfo("Asia/Tokyo")


def fetch_minkabu_economic_events():
    url = "https://www.investing.com/economic-calendar/Service/getCalendarFilteredData"

    payload = {
        "country[]": ["5", "35"],
        "importance[]": ["1", "2", "3"],
        "timeZone": "9",
        "timeFilter": "timeRemain",
        "currentTab": "custom",
    }

    headers = {
        "User-Agent": "Mozilla/5.0",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    res = requests.post(url, headers=headers, data=payload, timeout=30)
    res.raise_for_status()

    data = res.json()
    html = data.get("data", "")

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    rows = soup.find_all("tr")

    events = []
    today = datetime.now(JST).strftime("%Y-%m-%d")

    for r in rows:
        cols = r.find_all("td")

        if len(cols) < 7:
            continue

        try:
            events.append({
                "event_date_jst": today,
                "event_time_jst": cols[0].get_text(strip=True),
                "country": cols[1].get_text(strip=True),
                "event_name": cols[3].get_text(strip=True),
                "actual": cols[4].get_text(strip=True),
                "forecast": cols[5].get_text(strip=True),
                "previous": cols[6].get_text(strip=True),
                "importance_label": "",
                "event_status": "結果" if cols[4].get_text(strip=True) else "予定",
            })
        except:
            continue

    return events


def split_events_for_mail(events, now_jst):
    return {
        "yesterday_events": [],
        "today_events": events,
    }
