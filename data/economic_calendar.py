import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

from config.settings import JST


def _pick_value(row, candidates, default=None):
    for c in candidates:
        if c in row and pd.notna(row[c]):
            return row[c]
    return default


def _to_jst_datetime(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None

    try:
        dt = pd.to_datetime(v, utc=True, errors="coerce")
        if pd.isna(dt):
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
    if importance_raw is None:
        return "中"

    s = str(importance_raw).strip().lower()

    if "high" in s or s in ["3"]:
        return "高"
    if "low" in s or s in ["1"]:
        return "低"

    return "中"


def _sanitize(v):
    if v is None:
        return None
    s = str(v).strip()
    if s == "" or s.lower() == "nan":
        return None
    return v


# =========================
# ✅ Yahoo経済指標取得（修正版）
# =========================
def fetch_yahoo_economic_events(start_date=None, end_date=None, limit=200):

    if start_date is None:
        start_date = datetime.now(JST).date()

    # ✅ ① 日付範囲を14日に拡張
    if end_date is None:
        end_date = start_date + timedelta(days=14)

    print(f"[DEBUG] fetch range: {start_date} → {end_date}")

    cal = yf.Calendars(start=start_date, end=end_date)

    # ✅ ② limit拡張
    df = cal.get_economic_events_calendar(
        start=start_date,
        end=end_date,
        limit=limit,
        offset=0,
        force=True,
    )

    if df is None or len(df) == 0:
        print("[WARN] Yahoo returned empty DataFrame")
        return []

    if isinstance(df, pd.Series):
        df = df.to_frame().T

    print(f"[DEBUG] RAW rows = {len(df)}")

    events = []

    for _, row in df.iterrows():
        event_dt = _to_jst_datetime(
            _pick_value(
                row,
                ["eventTime", "startdatetime", "startDate", "date", "eventDate", "time"],
            )
        )

        # ✅ ③ countryフィルタ OFF（重要）
        country = _pick_value(row, ["country", "region", "currency", "locale"])

        event_name = _pick_value(row, ["event", "name", "title", "eventName"], "")

        actual = _sanitize(_pick_value(row, ["actual", "actualValue"]))
        forecast = _sanitize(_pick_value(row, ["forecast", "consensus", "expected"]))
        previous = _sanitize(_pick_value(row, ["previous", "prior"]))

        importance_label = _importance_to_label(
            _pick_value(row, ["importance", "impact", "priority"])
        )

        events.append({
            "event_dt_jst": event_dt,
            "event_date_jst": event_dt.date() if event_dt else None,
            "country": str(country),
            "event_name": str(event_name) if event_name else "",
            "importance_label": importance_label,
            "actual": actual,
            "forecast": forecast,
            "previous": previous,
        })

    events_sorted = sorted(
        events,
        key=lambda x: x["event_dt_jst"] or datetime.max.replace(tzinfo=JST),
    )

    print(f"[DEBUG] normalized events = {len(events_sorted)}")

    return events_sorted


# =========================
# ✅ メール用分割
# =========================
def split_events_for_mail(events, now_jst):

    today = now_jst.date()
    yesterday = today - timedelta(days=1)

    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)

    # 月曜モード
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

    # 通常日
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
