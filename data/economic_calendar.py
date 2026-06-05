import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

from config.settings import JST


COUNTRY_MAP = {
    "US": "US",
    "United States": "US",
    "USA": "US",
    "JP": "JP",
    "Japan": "JP",
    "日本": "JP",
}


def _normalize_country(v):
    if v is None:
        return None
    s = str(v).strip()
    return COUNTRY_MAP.get(s, s)


def _pick_value(row, candidates, default=None):
    """
    row から candidate column を順番に探して、最初の有効値を返す
    """
    for c in candidates:
        if c in row and pd.notna(row[c]):
            return row[c]
    return default


def _to_jst_datetime(v):
    """
    Yahoo / yfinance 側の日時が UTC / naive / string で来ても、
    できるだけ JST datetime にそろえる
    """
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None

    try:
        # まず UTC として解釈を試す
        dt = pd.to_datetime(v, utc=True, errors="coerce")
        if pd.isna(dt):
            # UTC前提で解釈できない場合は通常 parse
            dt = pd.to_datetime(v, errors="coerce")
            if pd.isna(dt):
                return None

            if getattr(dt, "tzinfo", None) is None:
                return dt.to_pydatetime().replace(tzinfo=JST)
            return dt.tz_convert(JST).to_pydatetime()

        return dt.tz_convert(JST).to_pydatetime()
    except Exception:
        return None


def _importance_to_label(importance_raw):
    """
    importance / impact / priority 的な値を 高・中・低 に寄せる
    """
    if importance_raw is None:
        return "中"

    s = str(importance_raw).strip().lower()

    if s in ["3", "high", "high impact"] or "high" in s:
        return "高"
    if s in ["1", "low", "low impact"] or "low" in s:
        return "低"

    return "中"


def _sanitize_metric_value(v):
    """
    nan / 空文字は None にそろえる
    """
    if v is None:
        return None

    s = str(v).strip()
    if s == "" or s.lower() == "nan":
        return None

    return v


def fetch_yahoo_economic_events(start_date=None, end_date=None, limit=100):
    """
    Yahoo Finance / yfinance の economic events calendar を取得し、
    日本（JP）・米国（US）だけに絞って標準化した list[dict] を返す。

    戻り値の各 event 例:
    {
        "event_dt_jst": datetime | None,
        "event_date_jst": date | None,
        "country": "JP" | "US",
        "event_name": str,
        "importance_label": "高" | "中" | "低",
        "actual": Any,
        "forecast": Any,
        "previous": Any,
    }
    """

    if start_date is None:
        start_date = datetime.now(JST).date()

    if end_date is None:
        end_date = start_date + timedelta(days=7)

    cal = yf.Calendars(start=start_date, end=end_date)
    df = cal.get_economic_events_calendar(
        start=start_date,
        end=end_date,
        limit=limit,
        offset=0,
        force=True,
    )

    if df is None or len(df) == 0:
        return []

    if isinstance(df, pd.Series):
        df = df.to_frame().T

    events = []

    for _, row in df.iterrows():
        event_dt = _to_jst_datetime(
            _pick_value(
                row,
                ["eventTime", "startdatetime", "startDate", "date", "eventDate", "time"],
            )
        )

        country = _normalize_country(
            _pick_value(row, ["country", "region", "currency", "locale"])
        )

        # 日本・米国のみに限定
        if country not in ["US", "JP"]:
            continue

        event_name = _pick_value(row, ["event", "name", "title", "eventName"], "")

        actual = _sanitize_metric_value(
            _pick_value(row, ["actual", "actualValue"])
        )
        forecast = _sanitize_metric_value(
            _pick_value(row, ["forecast", "consensus", "expected"])
        )
        previous = _sanitize_metric_value(
            _pick_value(row, ["previous", "prior"])
        )

        importance_label = _importance_to_label(
            _pick_value(row, ["importance", "impact", "priority"])
        )

        events.append(
            {
                "event_dt_jst": event_dt,
                "event_date_jst": event_dt.date() if event_dt else None,
                "country": country,
                "event_name": str(event_name) if event_name is not None else "",
                "importance_label": importance_label,
                "actual": actual,
                "forecast": forecast,
                "previous": previous,
            }
        )

    return sorted(
        events,
        key=lambda x: x["event_dt_jst"] or datetime.max.replace(tzinfo=JST),
    )


def split_events_for_mail(events, now_jst):
    """
    メール用に分割する。

    月曜:
        mode='monday'
        weekly_upcoming に JST基準の今週イベントを入れる

    月曜以外:
        mode='daily'
        yesterday_events に JST基準の昨日イベント
        today_events に JST基準の今日イベント
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
