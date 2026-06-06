from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import re
import requests
from bs4 import BeautifulSoup

JST = ZoneInfo("Asia/Tokyo")

MINKABU_URL = "https://fx.minkabu.jp/indicators/"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "ja-JP,ja;q=0.9",
}

TARGET_COUNTRIES = {"日本", "アメリカ"}


# =========================
# 共通
# =========================
def _safe(v):
    if v in [None, "", "None"]:
        return ""
    return str(v).strip()


def _jp_date_to_iso(text: str) -> str:
    m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", text)
    if not m:
        return ""
    y, mo, d = m.groups()
    return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"


# =========================
# 取得
# =========================
def _fetch_html():
    res = requests.get(MINKABU_URL, headers=HEADERS, timeout=30)
    res.raise_for_status()
    return res.text


def _parse_minkabu_calendar(html: str):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)

    lines = [x.strip() for x in text.splitlines() if x.strip()]

    events = []
    current_date = ""

    i = 0
    while i < len(lines):
        line = lines[i]

        # 日付
        if re.search(r"\d{4}年\d{2}月\d{2}日", line):
            current_date = _jp_date_to_iso(line)
            i += 1
            continue

        # 時刻
        if re.match(r"^\d{2}:\d{2}$", line) or line == "未定":
            if i + 6 < len(lines):
                event_time = line
                country = lines[i + 1]
                name = lines[i + 2]
                importance = lines[i + 3]
                previous = lines[i + 5]
                forecast = lines[i + 6]
                actual = lines[i + 7] if i + 7 < len(lines) else ""

                if country in TARGET_COUNTRIES and current_date:
                    events.append({
                        "event_date_jst": current_date,
                        "event_time_jst": event_time,
                        "country": "JP" if country == "日本" else "US",
                        "event_name": name,
                        "forecast": forecast,
                        "actual": actual,
                        "previous": previous,
                        "importance_label": importance,
                        "event_status": "結果" if actual not in ["", "---"] else "予定",
                    })

        i += 1

    return events


# =========================
# メイン取得
# =========================
def fetch_minkabu_economic_events():
    try:
        html = _fetch_html()
        events = _parse_minkabu_calendar(html)
        return events
    except Exception as e:
        print("[WARN] fetch failed:", e)
        return []


# =========================
# メール表示用分割（最終版）
# =========================
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
            today < dt <= end_of_week                      # 未来のみ
            and e.get("event_status") != "結果"             # 未発表のみ
            and (
                "高" in str(e.get("importance_label"))     # ★★★
                or "中" in str(e.get("importance_label"))  # ★★
            )
        ):
            week_events.append(e)

    # ✅ 時系列ソート（重要）
    def sort_key(e):
        date = e.get("event_date_jst", "")
        time = e.get("event_time_jst", "99:99")
        return f"{date} {time}"

    week_events = sorted(week_events, key=sort_key)

    return {
        "yesterday_events": yesterday_events,
        "today_events": today_events,
        "week_events": week_events,
    }
