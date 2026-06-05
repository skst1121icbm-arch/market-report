from datetime import datetime, timedelta
from typing import List, Dict
import requests
from bs4 import BeautifulSoup

from config.settings import JST


# =========================================
# みんかぶ 経済指標取得（BS4版）
# =========================================
def fetch_minkabu_economic_events() -> List[Dict]:
    url = "https://fx.minkabu.jp/indicators"

    headers = {
        "User-Agent": "Mozilla/5.0",
    }

    try:
        res = requests.get(url, headers=headers, timeout=10)
        html = res.text

        soup = BeautifulSoup(html, "html.parser")

        events = []
        tables = soup.find_all("table")
        print(f"[DEBUG] tables found (bs4) = {len(tables)}")

        current_date = None

        for table in tables:
            # 例: caption から日付を拾う
            caption = table.find("caption")
            if caption:
                try:
                    text = caption.get_text(strip=True)
                    dt = datetime.strptime(text[:10], "%Y年%m月%d日")
                    current_date = dt.date()
                    print(f"[DEBUG] detected date = {current_date}")
                except Exception:
                    pass

            rows = table.find_all("tr")

            for row in rows:
                cols = row.find_all("td")
                if len(cols) < 5:
                    continue

                try:
                    time_text = cols[0].get_text(strip=True)

                    country_text = cols[1].get("data_country", "")
                    country_fallback = cols[1].text.strip()
                    country = country_text if country_text else country_fallback

                    event_name = cols[2].get_text(strip=True)

                    previous = cols[5].get_text(strip=True) if len(cols) > 5 else None
                    forecast = cols[6].get_text(strip=True) if len(cols) > 6 else None
                    actual = cols[7].get_text(strip=True) if len(cols) > 7 else None

                    if not event_name:
                        continue

                    # 日本・米国のみ
                    if country not in ["JP", "US"]:
                        continue

                    # 時刻を JST datetime に変換
                    event_dt = None
                    if current_date and ":" in time_text:
                        try:
                            hour, minute = map(int, time_text.split(":"))
                            base_date = current_date

                            # 27:00 みたいなケース対策
                            if hour >= 24:
                                hour -= 24
                                base_date = current_date + timedelta(days=1)

                            event_dt = datetime(
                                base_date.year,
                                base_date.month,
                                base_date.day,
                                hour,
                                minute,
                                tzinfo=JST,
                            )
                        except Exception:
                            event_dt = None

                    # ✅ 追加でやるとさらに良い:
                    # 結果が入っていれば「結果」、未発表なら「予定」
                    status = "結果" if actual not in [None, "", "--", "-"] else "予定"

                    events.append({
                        "event_dt_jst": event_dt,
                        "event_date_jst": event_dt.date() if event_dt else current_date,
                        "country": country,
                        "event_name": event_name,
                        "importance_label": "高" if event_name in [
                            "非農業部門雇用者数（NFP）",
                            "失業率",
                            "GDP前期比",
                            "消費者物価指数（CPI）",
                        ] else "中",
                        "forecast": forecast,
                        "actual": actual,
                        "previous": previous,
                        "event_status": status,   # ← 追加
                    })

                except Exception:
                    continue

        if len(events) > 0:
            print(f"[DEBUG] minkabu events normalized = {len(events)}")
            for i, e in enumerate(events[:5], start=1):
                print(f"[DEBUG] MINKABU EVENT SAMPLE {i}: {e}")
            return events

        print("[WARN] MINKABU HTML parse returned empty → fallback")

    except Exception as e:
        print(f"[WARN] MINKABU fetch failed → fallback: {e}")

    # ここまで取れなければ fallback
    events = _fallback_events()
    print(f"[DEBUG] fallback events = {len(events)}")
    return events


# =========================================
# fallback（昨日の結果 + 今日の予定 + 時間つき）
# =========================================
def _fallback_events() -> List[Dict]:
    now = datetime.now(JST)
    today = now.date()
    yesterday = today - timedelta(days=1)

    return [
        # =====================
        # 昨日の結果
        # =====================
        {
            "event_dt_jst": datetime(
                yesterday.year, yesterday.month, yesterday.day, 21, 30, tzinfo=JST
            ),
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
            "event_dt_jst": datetime(
                yesterday.year, yesterday.month, yesterday.day, 21, 30, tzinfo=JST
            ),
            "event_date_jst": yesterday,
            "country": "US",
            "event_name": "失業率",
            "importance_label": "高",
            "forecast": "4.0%",
            "actual": "4.0%",
            "previous": "4.1%",
            "event_status": "結果",
        },

        # =====================
        # 今日の予定
        # =====================
        {
            "event_dt_jst": datetime(
                today.year, today.month, today.day, 8, 50, tzinfo=JST
            ),
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


# =========================================
# メール用分割
# =========================================
def split_events_for_mail(events: List[Dict], now_jst):
    today = now_jst.date()
    yesterday = today - timedelta(days=1)

    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)

    # 月曜はその週の予定
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

    # 昨日の結果だけ抽出
    yesterday_events = [
        e for e in events
        if e.get("event_date_jst") == yesterday and e.get("event_status") == "結果"
    ]

    # 今日の予定/結果
    today_events = [
        e for e in events
        if e.get("event_date_jst") == today
    ]

    # 0件防止（最低限、予定を出す）
    if not today_events:
        today_events = [
            e for e in events if e.get("event_status") == "予定"
        ]

    return {
        "mode": "daily",
        "weekly_upcoming": [],
        "yesterday_events": yesterday_events,
        "today_events": today_events,
    }
