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
        "Chrome/126.0 Safari/537.36"
    ),
    "Accept-Language": "ja,en-US;q=0.9",
}

COUNTRY_MAP = {
    "日本": "JP",
    "日": "JP",
    "アメリカ": "US",
    "米国": "US",
    "米": "US",
}

NO_RESULT_VALUES = {
    "",
    "-",
    "--",
    "---",
    "未定",
    "未発表",
    "N/A",
    "null",
}

SUPER_IMPORTANT_KEYWORDS = [
    "CPI",
    "消費者物価指数",
    "PCE",
    "FOMC",
    "政策金利",
    "雇用統計",
    "非農業部門雇用者数",
    "NFP",
    "失業率",
    "GDP",
]


def _safe(v):
    return "" if v is None else str(v).strip()


def _normalize_text(text):
    if not text:
        return ""

    text = text.replace("\u3000", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def _importance_rank(label: str) -> int:
    try:
        m = re.search(r"([0-9.]+)", label)
        if not m:
            return 1

        pips = float(m.group(1))

        if pips >= 10:
            return 5
        elif pips >= 7:
            return 4
        elif pips >= 4:
            return 3
        elif pips >= 2:
            return 2
        else:
            return 1

    except Exception:
        return 1

def _jp_date_to_iso(text):
    m = re.search(
        r"(\d{4})年(\d{1,2})月(\d{1,2})日",
        text,
    )

    if not m:
        return ""

    y, mth, d = m.groups()

    return f"{int(y):04d}-{int(mth):02d}-{int(d):02d}"


def _fetch_html():

    res = requests.get(
        MINKABU_URL,
        headers=HEADERS,
        timeout=30,
    )

    res.raise_for_status()

    html = res.text

    print(
        "[DEBUG] html length:",
        len(html),
    )

    return html


def _parse_minkabu_calendar(html):

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    tables = soup.find_all("table")

    print(
        "[DEBUG] tables:",
        len(tables),
    )

    events = []

    current_date = None

    date_pattern = re.compile(
        r"\d{4}年\d{1,2}月\d{1,2}日"
    )

    for table_idx, table in enumerate(tables):

        rows = table.find_all("tr")

        print(
            f"[DEBUG] table={table_idx} rows={len(rows)}"
        )

        for tag in table.find_all_previous():

            txt = _normalize_text(
                tag.get_text(" ", strip=True)
            )

            if date_pattern.search(txt):
                current_date = _jp_date_to_iso(txt)
                break

        for tr in rows:

            cols = [
                _normalize_text(
                    x.get_text(" ", strip=True)
                )
                for x in tr.find_all(["td", "th"])
            ]

            if len(cols) < 5:
                continue

            if len(events) < 5:
                print("[DEBUG] row:", cols)

            time_idx = None

            for i, v in enumerate(cols):

                if (
                    re.match(r"^\d{2}:\d{2}$", v)
                    or v == "未定"
                ):
                    time_idx = i
                    break

            if time_idx is None:
                continue

            try:
                event_name_raw = (
                    cols[time_idx + 2]
                    if len(cols) > time_idx + 2
                    else ""
                )

                country = None

                if event_name_raw.startswith("アメリカ・"):
                    country = "US"
                    event_name = event_name_raw.replace(
                        "アメリカ・",
                        "",
                        1
                    )

                elif event_name_raw.startswith("米国・"):
                    country = "US"
                    event_name = event_name_raw.replace(
                        "米国・",
                        "",
                        1
                    )

                elif event_name_raw.startswith("日本・"):
                    country = "JP"
                    event_name = event_name_raw.replace(
                        "日本・",
                        "",
                        1
                    )

                else:
                    continue
                    
                event_time = (
                    cols[time_idx]
                    if len(cols) > time_idx
                    else ""
                )

                importance = (
                    cols[4]
                    if len(cols) > 4
                    else ""
                )

                forecast = (
                    cols[-2]
                    if len(cols) >= 2
                    else ""
                )

                actual = (
                    cols[-1]
                    if len(cols) >= 1
                    else ""
                )

                if not current_date:
                    continue

                event_status = (
                    "予定"
                    if actual in NO_RESULT_VALUES
                    else "結果"
                )

                print(
                    "[EVENT]",
                    current_date,
                    event_time,
                    country,
                    event_name,
                    previous,
                    forecast,
                    actual,
                )
                events.append(
                    {
                        "event_date_jst": current_date,
                        "event_time_jst": event_time,
                        "country": country,
                        "event_name": event_name,
                        "forecast": forecast,
                        "actual": actual,
                        "previous": previous,
                        "importance_label": importance,
                        "importance_rank": _importance_rank(
                            importance
                        ),
                        "event_status": event_status,
                    }
                )

            except Exception as e:

                print(
                    "[WARN] parse row error:",
                    e,
                )

    dedup = {}

    for e in events:

        key = (
            e["event_date_jst"],
            e["event_time_jst"],
            e["country"],
            e["event_name"],
        )

        dedup[key] = e

    events = list(dedup.values())

    events.sort(
        key=lambda x: (
            x["event_date_jst"],
            x["event_time_jst"],
        )
    )

    print(
        "[INFO] economic events parsed:",
        len(events),
    )

    return events


def fetch_minkabu_economic_events():

    try:

        html = _fetch_html()

        return _parse_minkabu_calendar(
            html
        )

    except Exception as e:

        print(
            "[ERROR] economic calendar:",
            e,
        )

        return []


def _parse_event_datetime_jst(event):

    try:

        date_str = event.get(
            "event_date_jst",
            "",
        )

        time_str = event.get(
            "event_time_jst",
            "00:00",
        )

        if (
            not time_str
            or time_str == "未定"
        ):
            time_str = "00:00"

        return datetime.strptime(
            f"{date_str} {time_str}",
            "%Y-%m-%d %H:%M",
        ).replace(
            tzinfo=JST
        )

    except Exception:
        return None


def split_events_for_mail(
    events,
    now_dt,
):

    now = now_dt.astimezone(JST)

    today = now.date()
    yesterday = today - timedelta(days=1)

    start_of_week = (
        today - timedelta(days=today.weekday())
    )

    end_of_week = (
        start_of_week + timedelta(days=6)
    )

    yesterday_events = []
    today_events = []
    week_events = []
    super_important_events = []

    for e in events:

        dt = _parse_event_datetime_jst(e)

        if not dt:
            continue

        event_date = dt.date()

        if event_date == yesterday:
            yesterday_events.append(e)

        if event_date == today:
            today_events.append(e)

        if (
            today < event_date <= end_of_week
            and e.get("event_status") == "予定"
        ):
            week_events.append(e)

        event_name = str(
            e.get(
                "event_name",
                "",
            )
        )

        if any(
            keyword in event_name
            for keyword in SUPER_IMPORTANT_KEYWORDS
        ):
            super_important_events.append(e)

    print(
        "[INFO]",
        f"yesterday={len(yesterday_events)}",
        f"today={len(today_events)}",
        f"week={len(week_events)}",
        f"super={len(super_important_events)}",
    )

    return {
        "super_important_events":
            super_important_events,
        "yesterday_events":
            yesterday_events,
        "today_events":
            today_events,
        "week_events":
            week_events,
    }
