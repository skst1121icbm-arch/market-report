import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

from config.settings import JST


def _normalize_colname(name):
    """
    列名を正規化:
    - 小文字化
    - 空白/ハイフン/スラッシュ/括弧を除去
    """
    if name is None:
        return ""
    s = str(name).strip().lower()
    for ch in [" ", "_", "-", "/", "(", ")", "[", "]", ":", "."]:
        s = s.replace(ch, "")
    return s


def _build_normalized_row_map(row):
    """
    row(Series) -> 正規化列名 => 値 の dict
    """
    out = {}
    for k, v in row.items():
        out[_normalize_colname(k)] = v
    return out


def _pick_value_norm(norm_row, candidates, default=None):
    """
    正規化後の列名 dict から候補を探す
    """
    for c in candidates:
        key = _normalize_colname(c)
        if key in norm_row:
            v = norm_row[key]
            if pd.notna(v):
                return v
    return default


def _to_jst_datetime(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None

    try:
        # まず UTC 前提で解釈
        dt = pd.to_datetime(v, utc=True, errors="coerce")
        if pd.isna(dt):
            # だめなら普通に解釈
            dt = pd.to_datetime(v, errors="coerce")
            if pd.isna(dt):
                return None

            if getattr(dt, "tzinfo", None) is None:
                return dt.to_pydatetime().replace(tzinfo=JST)
            return dt.tz_convert(JST).to_pydatetime()

        return dt.tz_convert(JST).to_pydatetime()
    except Exception:
        return None


def _importance_to_label(v):
    if v is None:
        return "中"

    s = str(v).strip().lower()

    # よくあるパターンに広く対応
    if "high" in s or s in ["3", "3.0", "強", "高"]:
        return "高"
    if "low" in s or s in ["1", "1.0", "弱", "低"]:
        return "低"

    return "中"


def _sanitize(v):
    if v is None:
        return None
    s = str(v).strip()
    if s == "" or s.lower() in ["nan", "none", "null"]:
        return None
    return v


def fetch_yahoo_economic_events(start_date=None, end_date=None, limit=200):
    """
    Yahoo Finance / yfinance の economic events calendar を取得し、
    できるだけ頑健に標準化して返す。

    重要:
    - まずは country フィルタをかけない
    - 列名の揺れに耐える
    - 生データ構造をログに出す
    """
    if start_date is None:
        start_date = datetime.now(JST).date()

    if end_date is None:
        end_date = start_date + timedelta(days=14)

    print(f"[DEBUG] fetch range: {start_date} → {end_date}")

    cal = yf.Calendars(start=start_date, end=end_date)
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
    print(f"[DEBUG] RAW columns = {list(df.columns)}")

    # 最初の数行をそのまま確認
    try:
        print("[DEBUG] RAW head(3):")
        print(df.head(3).to_dict(orient="records"))
    except Exception as e:
        print(f"[WARN] failed to print RAW head: {e}")

    events = []

    for idx, row in df.iterrows():
        norm_row = _build_normalized_row_map(row)

        # どんなキーがあるか最初だけ見る
        if idx < 3:
            print(f"[DEBUG] normalized keys row {idx}: {list(norm_row.keys())}")

        event_dt_raw = _pick_value_norm(
            norm_row,
            [
                "eventTime",
                "eventDateTime",
                "startdatetime",
                "startDate",
                "date",
                "eventDate",
                "time",
                "releaseDate",
                "datetime",
            ],
        )

        country_raw = _pick_value_norm(
            norm_row,
            [
                "country",
                "countryName",
                "region",
                "locale",
                "currency",
                "nation",
            ]
        )

        event_name_raw = _pick_value_norm(
            norm_row,
            [
                "event",
                "eventName",
                "name",
                "title",
                "indicator",
                "indicatorName",
                "report",
            ],
            "",
        )

        forecast_raw = _pick_value_norm(
            norm_row,
            [
                "forecast",
                "consensus",
                "expected",
                "survey",
                "medianforecast",
            ]
        )

        actual_raw = _pick_value_norm(
            norm_row,
            [
                "actual",
                "actualValue",
                "released",
                "result",
            ]
        )

        previous_raw = _pick_value_norm(
            norm_row,
            [
                "previous",
                "prior",
                "previousValue",
                "last",
            ]
        )

        importance_raw = _pick_value_norm(
            norm_row,
            [
                "importance",
                "impact",
                "priority",
                "volatility",
                "level",
            ]
        )

        event_dt = _to_jst_datetime(event_dt_raw)
        country = _sanitize(country_raw)
        event_name = _sanitize(event_name_raw)
        forecast = _sanitize(forecast_raw)
        actual = _sanitize(actual_raw)
        previous = _sanitize(previous_raw)
        importance_label = _importance_to_label(importance_raw)

        # 完全空行は捨てる
        if not any([event_dt, country, event_name, forecast, actual, previous]):
            continue

        event = {
            "event_dt_jst": event_dt,
            "event_date_jst": event_dt.date() if event_dt else None,
            "country": str(country) if country is not None else "",
            "event_name": str(event_name) if event_name is not None else "",
            "importance_label": importance_label,
            "forecast": forecast,
            "actual": actual,
            "previous": previous,
        }

        events.append(event)

    print(f"[DEBUG] normalized events = {len(events)}")

    # 正規化後のサンプル
    for i, e in enumerate(events[:5], start=1):
        print(f"[DEBUG] NORMALIZED EVENT SAMPLE {i}: {e}")

    # event_dt_jst がないものは後ろへ
    events = sorted(
        events,
        key=lambda x: x["event_dt_jst"] or datetime.max.replace(tzinfo=JST),
    )

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
