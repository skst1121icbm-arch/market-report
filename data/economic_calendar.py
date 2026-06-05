import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup

from config.settings import JST


MINKABU_INDICATORS_URL = "https://fx.minkabu.jp/indicators"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://fx.minkabu.jp/",
}


COUNTRY_MAP = {
    "日本": "JP",
    "jp": "JP",
    "japan": "JP",
    "米国": "US",
    "アメリカ": "US",
    "us": "US",
    "usa": "US",
    "united states": "US",
}


DATE_PATTERNS = [
    re.compile(r"(?P<y>\d{4})[/-](?P<m>\d{1,2})[/-](?P<d>\d{1,2})"),
    re.compile(r"(?P<m>\d{1,2})/(?P<d>\d{1,2})\([月火水木金土日]\)"),
]

TIME_PATTERN = re.compile(r"^(?P<h>\d{1,2}):(?P<mi>\d{2})$")
STAR_PATTERN = re.compile(r"[★☆]+")


def _normalize_space(text: str) -> str:
    if text is None:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def _normalize_country(text: str) -> str:
    s = _normalize_space(text)
    key = s.lower()
    return COUNTRY_MAP.get(s, COUNTRY_MAP.get(key, s))


def _sanitize_value(v):
    if v is None:
        return None
    s = _normalize_space(v)
    if s in ["", "-", "--", "*", "＊", "未定", "N/A", "null", "None"]:
        return None
    return s


def _importance_to_label(raw: Optional[str]) -> str:
    if not raw:
        return "中"

    s = _normalize_space(raw)

    # ★の数が取れる場合
    stars = s.count("★")
    if stars >= 4:
        return "高"
    if stars >= 2:
        return "中"
    if stars >= 1:
        return "低"

    # 数値や語で来た場合の保険
    lower = s.lower()
    if "high" in lower or lower in ["5", "4", "3"]:
        return "高"
    if "low" in lower or lower == "1":
        return "低"
    return "中"


def _parse_date_from_text(text: str, fallback_year: int) -> Optional[datetime.date]:
    s = _normalize_space(text)

    # YYYY-MM-DD / YYYY/MM/DD
    m = DATE_PATTERNS[0].search(s)
    if m:
        y = int(m.group("y"))
        mo = int(m.group("m"))
        d = int(m.group("d"))
        return datetime(y, mo, d).date()

    # MM/DD(曜)
    m = DATE_PATTERNS[1].search(s)
    if m:
        mo = int(m.group("m"))
        d = int(m.group("d"))
        return datetime(fallback_year, mo, d).date()

    return None


def _parse_time_to_jst(base_date, time_text: Optional[str]) -> Optional[datetime]:
    """
    みんかぶ系の経済指標ページでは 24時超え（例: 27:00）が出る可能性を考慮。
    """
    if base_date is None or not time_text:
        return None

    s = _normalize_space(time_text)
    m = TIME_PATTERN.match(s)
    if not m:
        return None

    hour = int(m.group("h"))
    minute = int(m.group("mi"))

    add_days = 0
    if hour >= 24:
        hour -= 24
        add_days = 1

    dt = datetime(
        base_date.year,
        base_date.month,
        base_date.day,
        hour,
        minute,
        tzinfo=JST,
    ) + timedelta(days=add_days)

    return dt


def _extract_tables_with_pandas(html: str) -> List[pd.DataFrame]:
    try:
        return pd.read_html(html)
    except Exception:
        return []


def _normalize_df_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [_normalize_space(c) for c in df.columns]
    return df


def _extract_from_dataframe(df: pd.DataFrame, fallback_year: int) -> List[Dict]:
    """
    pandas.read_html で取れたテーブルから、できるだけ汎用的に抜く。
    完全一致でなく、列名候補をゆるく見る。
    """
    df = _normalize_df_columns(df)
    cols = list(df.columns)

    # 候補列
    time_col = next((c for c in cols if "時" in c or "時間" in c or c.lower() == "time"), None)
    country_col = next((c for c in cols if "国" in c or "地域" in c or "通貨" in c), None)
    name_col = next((c for c in cols if "指標" in c or "内容" in c or "イベント" in c), None)
    importance_col = next((c for c in cols if "重要" in c), None)
    previous_col = next((c for c in cols if "前回" in c), None)
    forecast_col = next((c for c in cols if "予想" in c), None)
    actual_col = next((c for c in cols if "結果" in c or "速報" in c), None)
    date_col = next((c for c in cols if "日付" in c or "日" == c), None)

    events = []
    current_date = None

    for _, row in df.iterrows():
        row_values = [_normalize_space(v) for v in row.tolist()]

        # 行全体から日付を検出
        joined = " ".join(row_values)
        maybe_date = _parse_date_from_text(joined, fallback_year)
        if maybe_date:
            current_date = maybe_date
            # 日付行だけなら次へ
            if all(v == "" for v in row_values[1:]):
                continue

        # 基本フィールド
        time_text = _normalize_space(row.get(time_col)) if time_col else ""
        country_text = _normalize_space(row.get(country_col)) if country_col else ""
        event_name = _normalize_space(row.get(name_col)) if name_col else ""
        importance = _normalize_space(row.get(importance_col)) if importance_col else ""
        previous = _sanitize_value(row.get(previous_col)) if previous_col else None
        forecast = _sanitize_value(row.get(forecast_col)) if forecast_col else None
        actual = _sanitize_value(row.get(actual_col)) if actual_col else None

        # date 列があれば優先
        if date_col:
            explicit_date = _parse_date_from_text(_normalize_space(row.get(date_col)), fallback_year)
            if explicit_date:
                current_date = explicit_date

        event_dt = _parse_time_to_jst(current_date, time_text)
        event_date = event_dt.date() if event_dt else current_date

        # 空行スキップ
        if not any([time_text, country_text, event_name, previous, forecast, actual]):
            continue

        events.append(
            {
                "event_dt_jst": event_dt,
                "event_date_jst": event_date,
                "country": _normalize_country(country_text),
                "event_name": event_name,
                "importance_label": _importance_to_label(importance),
                "forecast": forecast,
                "actual": actual,
                "previous": previous,
            }
        )

    return events


def _extract_rows_with_bs4(html: str, fallback_year: int) -> List[Dict]:
    """
    pandas.read_html でうまく取れない時の保険。
    表の tr/td をなめて、日付行 + データ行を雑に復元する。
    """
    soup = BeautifulSoup(html, "html.parser")
    events = []
    current_date = None

    for tr in soup.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
        cells = [_normalize_space(c) for c in cells if _normalize_space(c) != ""]

        if not cells:
            continue

        joined = " ".join(cells)

        maybe_date = _parse_date_from_text(joined, fallback_year)
        if maybe_date:
            current_date = maybe_date
            continue

        # 典型形を想定:
        # [時刻, 国, 重要度, 指標名, 前回, 予想, 結果]
        # or [時刻, 国, 指標名, 前回, 予想, 結果]
        time_text = ""
        country_text = ""
        importance_text = ""
        event_name = ""
        previous = None
        forecast = None
        actual = None

        if len(cells) >= 6:
            # 先頭に時刻があるか
            if TIME_PATTERN.match(cells[0]) or cells[0] in ["*", "＊"]:
                time_text = cells[0]

                # 重要度セルがあるか
                if len(cells) >= 7 and STAR_PATTERN.search(cells[2]):
                    country_text = cells[1]
                    importance_text = cells[2]
                    event_name = cells[3]
                    previous = _sanitize_value(cells[4]) if len(cells) > 4 else None
                    forecast = _sanitize_value(cells[5]) if len(cells) > 5 else None
                    actual = _sanitize_value(cells[6]) if len(cells) > 6 else None
                else:
                    country_text = cells[1] if len(cells) > 1 else ""
                    event_name = cells[2] if len(cells) > 2 else ""
                    previous = _sanitize_value(cells[3]) if len(cells) > 3 else None
                    forecast = _sanitize_value(cells[4]) if len(cells) > 4 else None
                    actual = _sanitize_value(cells[5]) if len(cells) > 5 else None

        event_dt = _parse_time_to_jst(current_date, time_text) if time_text not in ["*", "＊"] else None
        event_date = event_dt.date() if event_dt else current_date

        if not any([time_text, country_text, event_name, previous, forecast, actual]):
            continue

        events.append(
            {
                "event_dt_jst": event_dt,
                "event_date_jst": event_date,
                "country": _normalize_country(country_text),
                "event_name": _normalize_space(event_name),
                "importance_label": _importance_to_label(importance_text),
                "forecast": forecast,
                "actual": actual,
                "previous": previous,
            }
        )

    return events


def _deduplicate_events(events: List[Dict]) -> List[Dict]:
    seen = set()
    out = []

    for e in events:
        key = (
            e.get("event_date_jst"),
            e.get("event_dt_jst"),
            e.get("country"),
            e.get("event_name"),
            e.get("forecast"),
            e.get("actual"),
            e.get("previous"),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(e)

    return out


def fetch_minkabu_economic_events(
    start_date=None,
    end_date=None,
    countries=("JP", "US"),
    timeout=(10, 30),
):
    """
    みんかぶ FX 経済指標カレンダーからイベントを取得して標準化する提案実装。
    - まずページ全体を取得
    - pandas.read_html で表を抽出
    - 足りなければ BeautifulSoup でも補完
    - 最後に日付・国で絞る
    """
    if start_date is None:
        start_date = datetime.now(JST).date()

    if end_date is None:
        end_date = start_date + timedelta(days=7)

    resp = requests.get(
        MINKABU_INDICATORS_URL,
        headers=REQUEST_HEADERS,
        timeout=timeout,
    )
    resp.raise_for_status()

    html = resp.text
    fallback_year = start_date.year

    events = []

    # 1) pandas で表抽出
    tables = _extract_tables_with_pandas(html)
    for df in tables:
        events.extend(_extract_from_dataframe(df, fallback_year))

    # 2) 保険で BS4 も試す
    if not events:
        events.extend(_extract_rows_with_bs4(html, fallback_year))

    events = _deduplicate_events(events)

    # 国フィルタ
    countries_set = set(countries) if countries else None
    if countries_set:
        events = [
            e for e in events
            if e.get("country") in countries_set
        ]

    # 日付フィルタ
    events = [
        e for e in events
        if e.get("event_date_jst") and start_date <= e["event_date_jst"] <= end_date
    ]

    # event_name が空のものを最後に残すかどうかは要件次第。
    # 今回はレポート価値を優先して空名は落とす。
    events = [e for e in events if e.get("event_name")]

    events = sorted(
        events,
        key=lambda x: (
            x["event_date_jst"],
            x["event_dt_jst"] or datetime.max.replace(tzinfo=JST),
            x["country"],
            x["event_name"],
        ),
    )

    print(f"[DEBUG] minkabu events normalized = {len(events)}")
    for i, e in enumerate(events[:10], start=1):
        print(f"[DEBUG] MINKABU EVENT SAMPLE {i}: {e}")

    return events


def split_events_for_mail(events, now_jst):
    """
    月曜:
      - 今週の予定
    それ以外:
      - 昨日の結果
      - 今日の予定/結果
    JST基準
    """
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

    return {
        "mode": "daily",
        "weekly_upcoming": [],
        "yesterday_events": yesterday_events,
        "today_events": today_events,
    }
