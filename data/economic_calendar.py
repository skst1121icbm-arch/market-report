import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional

import pandas as pd
import requests

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
    "アメリカ合衆国": "US",
    "us": "US",
    "usa": "US",
    "united states": "US",
}


DATE_HEADER_PATTERN = re.compile(r"(?P<m>\d{2})/(?P<d>\d{2})\([月火水木金土日]\)")
TIME_PATTERN = re.compile(r"^(?P<h>\d{1,2}):(?P<mi>\d{2})$")


def _norm(text) -> str:
    if text is None:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def _sanitize(v):
    s = _norm(v)
    if s in ["", "-", "--", "*", "＊", "未定", "N/A", "None", "none", "null"]:
        return None
    return s


def _country_to_code(text: str) -> str:
    s = _norm(text)
    return COUNTRY_MAP.get(s, COUNTRY_MAP.get(s.lower(), s))


def _importance_to_label(v: Optional[str]) -> str:
    s = _norm(v)
    if not s:
        return "中"

    # 数字/記号/文字のゆるい対応
    if s.count("★") >= 3 or s in ["5", "4", "3", "高"]:
        return "高"
    if s.count("★") == 2 or s in ["2", "中"]:
        return "中"
    if s.count("★") == 1 or s in ["1", "低"]:
        return "低"

    return "中"


def _parse_mmdd(text: str, year: int):
    s = _norm(text)
    m = DATE_HEADER_PATTERN.search(s)
    if not m:
        return None
    return datetime(year, int(m.group("m")), int(m.group("d"))).date()


def _parse_time(date_obj, time_text: str):
    if not date_obj:
        return None

    s = _norm(time_text)
    m = TIME_PATTERN.match(s)
    if not m:
        return None

    h = int(m.group("h"))
    mi = int(m.group("mi"))

    add_days = 0
    if h >= 24:
        h -= 24
        add_days = 1

    return datetime(
        date_obj.year,
        date_obj.month,
        date_obj.day,
        h,
        mi,
        tzinfo=JST,
    ) + timedelta(days=add_days)


def _extract_events_from_df(df: pd.DataFrame, year: int) -> List[Dict]:
    """
    みんかぶの表っぽい DataFrame からできるだけ頑健に抽出する。
    想定列:
      時間 / 国 / 重要度 / 指標名 / 前回 / 予想 / 結果
    ただし完全一致に頼らず位置でも吸う。
    """
    events: List[Dict] = []

    # 列名正規化
    df = df.copy()
    df.columns = [_norm(c) for c in df.columns]

    current_date = None

    for _, row in df.iterrows():
        vals = [_norm(v) for v in row.tolist()]

        # 日付ヘッダ行検出
        joined = " ".join(vals)
        maybe_date = _parse_mmdd(joined, year)
        if maybe_date:
            current_date = maybe_date
            continue

        # 空行スキップ
        if not any(vals):
            continue

        # 典型ケース:
        # [時刻, 国, 重要度, 指標名, 前回, 予想, 結果]
        # [時刻, 国, 指標名, 前回, 予想, 結果]
        time_text = vals[0] if len(vals) > 0 else ""
        event_dt = _parse_time(current_date, time_text)

        # 時刻っぽくない行は飛ばす
        if not (TIME_PATTERN.match(_norm(time_text)) or time_text in ["*", "＊"]):
            continue

        country = ""
        importance = ""
        event_name = ""
        previous = None
        forecast = None
        actual = None

        if len(vals) >= 7:
            # 重要度列が入っているパターンを優先
            country = vals[1]
            importance = vals[2]
            event_name = vals[3]
            previous = _sanitize(vals[4])
            forecast = _sanitize(vals[5])
            actual = _sanitize(vals[6])
        elif len(vals) >= 6:
            country = vals[1]
            event_name = vals[2]
            previous = _sanitize(vals[3])
            forecast = _sanitize(vals[4])
            actual = _sanitize(vals[5])
        else:
            continue

        # 日本・米国だけ残す
        country_code = _country_to_code(country)
        if country_code not in ["JP", "US"]:
            continue

        # event_name が空なら捨てる
        event_name = _norm(event_name)
        if not event_name:
            continue

        events.append(
            {
                "event_dt_jst": event_dt,
                "event_date_jst": event_dt.date() if event_dt else current_date,
                "country": country_code,
                "event_name": event_name,
                "importance_label": _importance_to_label(importance),
                "forecast": forecast,
                "actual": actual,
                "previous": previous,
            }
        )

    return events


def _dedup(events: List[Dict]) -> List[Dict]:
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


def fetch_minkabu_economic_events(start_date=None, end_date=None, timeout=(10, 30)):
    """
    みんかぶ経済指標カレンダーから日本・米国のイベントを取得する。
    まずページを取得し、pandas.read_html() で表を抽出する。
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
    year = start_date.year

    try:
        tables = pd.read_html(html)
    except Exception as e:
        print(f"[WARN] pd.read_html failed: {e}")
        tables = []

    print(f"[DEBUG] minkabu tables found = {len(tables)}")

    all_events: List[Dict] = []
    for i, df in enumerate(tables):
        try:
            evs = _extract_events_from_df(df, year)
            if evs:
                print(f"[DEBUG] table {i} extracted events = {len(evs)}")
            all_events.extend(evs)
        except Exception as e:
            print(f"[WARN] failed parsing table {i}: {e}")

    all_events = _dedup(all_events)

    # 指定期間フィルタ
    all_events = [
        e for e in all_events
        if e.get("event_date_jst") and start_date <= e["event_date_jst"] <= end_date
    ]

    # 日時順ソート
    all_events = sorted(
        all_events,
        key=lambda x: (
            x["event_date_jst"],
            x["event_dt_jst"] or datetime.max.replace(tzinfo=JST),
            x["country"],
            x["event_name"],
        ),
    )

    print(f"[DEBUG] minkabu events normalized = {len(all_events)}")
    for i, e in enumerate(all_events[:10], start=1):
        print(f"[DEBUG] MINKABU EVENT SAMPLE {i}: {e}")

    return all_events


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

    # 保険:
    # 今日/昨日が0件のとき、今週内の近いイベントを today_events に入れて
    # 「完全に空」になるのを避ける
    if not yesterday_events and not today_events:
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        fallback_events = [
            e for e in events
            if e.get("event_date_jst") and week_start <= e["event_date_jst"] <= week_end
        ]
        today_events = fallback_events[:10]

    return {
        "mode": "daily",
        "weekly_upcoming": [],
        "yesterday_events": yesterday_events,
        "today_events": today_events,
    }
