import pandas as pd

def normalize_excel_value(v):
    if v is None:
        return None
    if isinstance(v, float) and pd.isna(v):
        return None
    s = str(v).strip()
    if s in ["", "-", "nan", "NaN", "None"]:
        return None
    return s

def parse_excel_date_label(date_label):
    s = normalize_excel_value(date_label)
    if not s:
        return None
    try:
        return pd.to_datetime(s)
    except Exception:
        return None

def parse_excel_time_label(time_label):
    s = normalize_excel_value(time_label)
    if not s:
        return None
    try:
        return pd.to_datetime(s).time()
    except Exception:
        return None

def load_events_from_excel(file_path):
    try:
        df = pd.read_excel(file_path)

        events = []
        for _, row in df.iterrows():
            event = {
                "date": parse_excel_date_label(row.get("date")),
                "time": parse_excel_time_label(row.get("time")),
                "country": normalize_excel_value(row.get("country")),
                "event_name": normalize_excel_value(row.get("event_name")),
                "importance": normalize_excel_value(row.get("importance")),
                "actual": normalize_excel_value(row.get("actual")),
                "forecast": normalize_excel_value(row.get("forecast")),
                "previous": normalize_excel_value(row.get("previous")),
            }
            events.append(event)

        return events

    except Exception:
        return []