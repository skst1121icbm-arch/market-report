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

```
text = text.replace("\u3000", " ")
text = re.sub(r"\s+", " ", text)
return text.strip()
```

def _jp_date_to_iso(text):
m = re.search(
r"(\d{4})年(\d{1,2})月(\d{1,2})日",
text
)

```
if not m:
    return ""

y, mth, d = m.groups()

return f"{int(y):04d}-{int(mth):02d}-{int(d):02d}"
```

def _fetch_html():

```
res = requests.get(
    MINKABU_URL,
    headers=HEADERS,
    timeout=30
)

res.raise_for_status()

html = res.text

print(
    "[DEBUG] html length:",
    len(html)
)

return html
```

def _parse_minkabu_calendar(html):

```
soup = BeautifulSoup(
    html,
    "html.parser"
)

tables = soup.find_all("table")

print(
    "[DEBUG] tables:",
    len(tables)
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

    #
    # 日付探索
    #
    for tag in table.find_all_previous():

        txt = _normalize_text(
            tag.get_text(" ", strip=True)
        )

        if date_pattern.search(txt):
            current_date = _jp_date_to_iso(txt)
            break

    for row_idx, tr in enumerate(rows):

        cols = [
            _normalize_text(
                x.get_text(" ", strip=True)
            )
            for x in tr.find_all(["td", "th"])
        ]

        if len(cols) < 5:
            continue

        #
        # 最初の20行だけログ
        #
        if len(events) < 5:
            print(
                "[DEBUG] row:",
                cols
            )

        time_idx = None

        for i, v in enumerate(cols):

            if (
                re.match(
                    r"^\d{2}:\d{2}$",
                    v
                )
                or v == "未定"
            ):
                time_idx = i
                break

        if time_idx is None:
            continue

        try:

            event_time = (
                cols[time_idx]
                if len(cols) > time_idx
                else ""
            )

            country_raw = (
                cols[time_idx + 1]
                if len(cols) > time_idx + 1
                else ""
            )

            event_name = (
                cols[time_idx + 2]
                if len(cols) > time_idx + 2
                else ""
            )

            importance = (
                cols[time_idx + 3]
                if len(cols) > time_idx + 3
                else ""
            )

            previous = (
                cols[time_idx + 4]
                if len(cols) > time_idx + 4
                else ""
            )

            forecast = (
                cols[time_idx + 5]
                if len(cols) > time_idx + 5
                else ""
            )

            actual = (
                cols[time_idx + 6]
                if len(cols) > time_idx + 6
                else ""
            )

            if country_raw not in COUNTRY_MAP:
                continue

            if not current_date:
                continue

            event_status = (
                "予定"
                if actual in NO_RESULT_VALUES
                else "結果"
            )

            events.append({
                "event_date_jst": current_date,
                "event_time_jst": event_time,
                "country": COUNTRY_MAP[country_raw],
                "event_name": event_name,
                "forecast": forecast,
                "actual": actual,
                "previous": previous,
                "importance_label": importance,
                "event_status": event_status,
            })

        except Exception as e:

            print(
                "[WARN] parse row error:",
                e
            )

#
# 重複除去
#
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
        x["event_time_jst"]
    )
)

print(
    "[INFO] economic events parsed:",
    len(events)
)

return events
```

def fetch_minkabu_economic_events():

```
try:

    html = _fetch_html()

    return _parse_minkabu_calendar(
        html
    )

except Exception as e:

    print(
        "[ERROR] economic calendar:",
        e
    )

    return []
