from datetime import datetime, timedeltafrom datetime import datetime-Type": "application/x-www-form-urlencoded",
    }

    res = requests.post(url, headers=headers, data=payload, timeout=30)
    res.raise_for_status()

    data = res.json()
    html = data.get("data", "")

    # ↓ importはここで分離（絶対壊れない）
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    rows = soup.find_all("tr")

    events = []
    today = datetime.now(JST).strftime("%Y-%m-%d")

    for r in rows:
        cols = r.find_all("td")

        # 必須列数チェック
        if len(cols) < 7:
            continue

        try:
            time = cols[0].get_text(strip=True)
            currency = cols[1].get_text(strip=True)
            event_name = cols[3].get_text(strip=True)
            actual = cols[4].get_text(strip=True)
            forecast = cols[5].get_text(strip=True)
            previous = cols[6].get_text(strip=True)

            events.append({
                "event_date_jst": today,
                "event_time_jst": time,
                "country": currency,
                "event_name": event_name,
                "forecast": forecast,
                "actual": actual,
                "previous": previous,
                "importance_label": "",
                "event_status": "結果" if actual not in ["", "-", "N/A"] else "予定",
            })

        except Exception:
            continue

    return events


def split_events_for_mail(events, now_jst):
    """
    ✅ 今回はAPIが当日中心なので
    今日のみ返す
    """
    return {
        "yesterday_events": [],
        "today_events": events,
    }

from zoneinfo import ZoneInfo
import requests

JST = ZoneInfo("Asia/Tokyo")


def fetch_minkabu_economic_events():
    """
    ✅ Investing API版（403回避）
    ✅ 崩れ防止構成
    """
    url = "https://www.investing.com/economic-calendar/Service/getCalendarFilteredData"

    payload = {
        "country[]": ["5", "35"],   # 5=US, 35=JP
        "importance[]": ["1", "2", "3"],
        "timeZone": "9",
        "timeFilter": "timeRemain",
        "currentTab": "custom",
    }

    headers = {
        "User-Agent": "Mozilla/5.0",
        "X-Requested-With": "XMLHttpRequest",
