from datetime import datetime, timedelta
import requests

JST = ZoneInfo("Asia/Tokyo")


def fetch_investing_economic_events():
    url = "https://www.investing.com/economic-calendar/Service/getCalendarFilteredData"

    payload = {
        "country[]": ["5", "35"],  # 5=US, 35=JP
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

    res = requests.post(url, headers=headers, data=payload)
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
        if len(cols) < 6:
            continue

        try:
            time = cols[0].text.strip()
            currency = cols[1].text.strip()
            event_name = cols[3].text.strip()
            actual = cols[4].text.strip()
            forecast = cols[5].text.strip()
            previous = cols[6].text.strip()

            item = {
                "event_date_jst": today,
                "event_time_jst": time,
                "country": currency,
                "event_name": event_name,
                "forecast": forecast,
                "actual": actual,
                "previous": previous,
                "importance_label": "",
                "event_status": "結果" if actual else "予定",
            }

            events.append(item)

        except Exception:
            continue

    return events


def fetch_minkabu_economic_events():
    return fetch_investing_economic_events()


def split_events_for_mail(events, now_jst):
    today = now_jst.date()
    yesterday = today - timedelta(days=1)

    return {
        "yesterday_events": [],  # APIは当日中心
        "today_events": events
    }
from zoneinfo import ZoneInfo
