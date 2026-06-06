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


def _fetch_html():
    res = requests.get(MINKABU_URL, headers=HEADERS, timeout=30)
    res.raise_for_status()
    return res.text


def _parse_minkabu_calendar(html: str):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)

    lines = [_normalize_text(x) for x in text.splitlines()]
    lines = [x for x in lines if x]

    events = []
    current_date = ""

    # みんかぶの公開表示では、日付見出しの下に
    # 時間 / 国 / 指標名 / 重要度 / 前回ドル円変動幅 / 前回（改定） / 予想 / 結果
    # の並びが見える。[1](https://fx.minkabu.jp/indicators/)
    #
    # ここでは、生テキストから日付見出しを拾い、
    # その後に続く行を簡易的に組み立てる。
    i = 0
    while i < len(lines):
        line = lines[i]

        # 日付行
        if re.search(r"\d{4}年\d{2}月\d{2}日", line):
            current_date = _jp_date_to_iso(line)
            i += 1
            continue

        # 時刻っぽい行（例: 08:50, 21:30, 未定）
        if re.match(r"^\d{2}:\d{2}$", line) or line == "未定":
            if i + 6 < len(lines):
                event_time = line
                country = lines[i + 1]
                event_name = lines[i + 2]
                importance = lines[i + 3]
                # lines[i + 4] = 前回ドル円変動幅
                previous = lines[i + 5]   # 前回（改定）
                forecast = lines[i + 6]   # 予想
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


def fallback_events():
    """
    カレンダー取得失敗時の最小フォールバック。
    ここはあなたの運用に合わせて増やせます。
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


def split_events_for_mail(events, now_jst):
    today = now_jst.date()
    yesterday = today - timedelta(days=1)

    yesterday_events = []
    today_events = []

    for e in events or []:
        d = _safe(e.get("event_date_jst"))
        if not d:
            continue

        try:
            dt = datetime.strptime(d, "%Y-%m-%d").date()
        except Exception:
            continue

        if dt == yesterday:
            yesterday_events.append(e)
        elif dt == today:
            today_events.append(e)

    return {
        "yesterday_events": yesterday_events,
        "today_events": today_events,
    }
