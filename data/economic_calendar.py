from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import re
import requests
from bs4 import BeautifulSoup

JST = ZoneInfo("Asia/Tokyo")

MINKABU_URL = "https://fx.minkabu.jp/indicators/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7",
}

TARGET_COUNTRIES = {"日本", "アメリカ"}


# =========================
# BASIC HELPERS
# =========================
def _safe(v):
    if v in [None, "", "None"]:
        return ""
    return str(v).strip()


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\u3000", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _jp_date_to_iso(text: str) -> str:
    """
    '2026年06月08日' -> '2026-06-08'
    """
    m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", text)
    if not m:
        return ""
    y, mo, d = m.groups()
    return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"


# =========================
# FETCH
# =========================
def _fetch_html():
    res = requests.get(MINKABU_URL, headers=HEADERS, timeout=30)
    res.raise_for_status()
    return res.text


def _parse_minkabu_calendar(html: str):
    """
    みんかぶ経済指標カレンダーから
    日本 / アメリカのイベントを抽出
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)

    lines = [_normalize_text(x) for x in text.splitlines()]
    lines = [x for x in lines if x]

    events = []
    current_date = ""

    i = 0
    while i < len(lines):
        line = lines[i]

        # 日付行
        if re.search(r"\d{4}年\d{2}月\d{2}日", line):
            current_date = _jp_date_to_iso(line)
            i += 1
            continue

        # 時刻行（例: 08:50 / 21:30 / 未定）
        if re.match(r"^\d{2}:\d{2}$", line) or line == "未定":
            if i + 6 < len(lines):
                event_time = line
                country = lines[i + 1]
                event_name = lines[i + 2]
                importance = lines[i + 3]
                # lines[i + 4] = 前回ドル円変動幅
                previous = lines[i + 5]
                forecast = lines[i + 6]
                actual = lines[i + 7] if i + 7 < len(lines) else ""

                if country in TARGET_COUNTRIES and current_date:
                    events.append({
                        "event_date_jst": current_date,
                        "event_time_jst": event_time,
                        "country": "JP" if country == "日本" else "US" if country == "アメリカ" else country,
                        "event_name": event_name,
                        "forecast": forecast,
                        "actual": actual,
                        "previous": previous,
                        "importance_label": importance,
                        "event_status": "結果" if actual not in ["", "---"] else "予定",
                    })

            i += 1
            continue

        i += 1

    return events


# =========================
# FALLBACK
# =========================
def fallback_events():
    """
    取得失敗時の最小フォールバック
    """
    return [
        {
            "event_date_jst": "2026-06-05",
            "event_time_jst": "21:30",
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
            "event_time_jst": "21:30",
            "country": "US",
            "event_name": "失業率",
            "forecast": "4.3%",
            "actual": "4.3%",
            "previous": "4.3%",
            "importance_label": "高",
            "event_status": "結果",
        },
    ]


# =========================
# PUBLIC FETCH FUNCTION
# =========================
def fetch_minkabu_economic_events():
    try:
        html = _fetch_html()
        events = _parse_minkabu_calendar(html)
        if not events:
            return fallback_events()
        return events
    except Exception as e:
        print("[WARN] minkabu economic calendar fallback:", e)
        return fallback_events()


# =========================
# DATETIME PARSER (JST)
# =========================
def _parse_event_datetime_jst(event):
    """
    event_date_jst + event_time_jst を JST の datetime に変換
    """
    date_str = _safe(event.get("event_date_jst"))
    time_str = _safe(event.get("event_time_jst"))

    if not date_str:
        return None

    try:
        if time_str and time_str != "未定":
            dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        else:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.replace(tzinfo=JST)
    except Exception:
        return None


# =========================
# SPLIT FOR MAIL
# =========================
def split_events_for_mail(events, now_dt):
    """
    日本時間基準で:
      - yesterday_events
      - today_events
      - week_events（今週・重要）
    に分割する
    """
    # 現在時刻を必ずJSTで判定
    now = now_dt.astimezone(JST)

    today = now.date()
    yesterday = today - timedelta(days=1)

    # 今週（月曜〜日曜）
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    yesterday_events = []
    today_events = []
    week_events = []

    for e in events or []:
        event_dt = _parse_event_datetime_jst(e)
        if not event_dt:
            continue

        event_date = event_dt.date()

        # ===== 昨日（JST基準）=====
        if event_date == yesterday:
            yesterday_events.append(e)

        # ===== 本日（JST基準）=====
        elif event_date == today:
            today_events.append(e)

        # ===== 今週（重要・未来のみ）=====
        if (
            today < event_date <= end_of_week
            and e.get("event_status") != "結果"
            and (
                "高" in str(e.get("importance_label"))
                or "中" in str(e.get("importance_label"))
            )
        ):
            week_events.append(e)

    def sort_key(e):
        dt = _parse_event_datetime_jst(e)
        if dt is None:
            return datetime.max.replace(tzinfo=JST)
        return dt

    yesterday_events = sorted(yesterday_events, key=sort_key)
    today_events = sorted(today_events, key=sort_key)
    week_events = sorted(week_events, key=sort_key)

    print("[DEBUG] yesterday:", len(yesterday_events))
    print("[DEBUG] today:", len(today_events))
    print("[DEBUG] week:", len(week_events))

    return {
        "yesterday_events": yesterday_events,
        "today_events": today_events,
        "week_events": week_events,
    }
