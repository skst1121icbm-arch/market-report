import os
import csv

from config.settings import DAILY_LOG_FILE, EVENT_LOG_FILE
from utils.datetime_utils import now_jst


# =========================
# CSVヘッダー作成
# =========================
def ensure_csv_header(file_path, fieldnames):
    write_header = not os.path.exists(file_path) or os.path.getsize(file_path) == 0

    if write_header:
        with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()


# =========================
# 1行追記
# =========================
def append_csv_row(file_path, fieldnames, row):
    ensure_csv_header(file_path, fieldnames)

    with open(file_path, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writerow(row)


# =========================
# 日次ログ保存
# =========================
def save_daily_log(score, regime, signal):
    fieldnames = [
        "timestamp_jst",
        "score",
        "regime",
        "signal",
    ]

    row = {
        "timestamp_jst": now_jst().strftime("%Y-%m-%d %H:%M:%S"),
        "score": score,
        "regime": regime,
        "signal": signal,
    }

    append_csv_row(DAILY_LOG_FILE, fieldnames, row)


# =========================
# 経済指標ログ保存
# =========================
def save_event_log(events):
    fieldnames = [
        "timestamp_jst",
        "event_dt_jst",
        "event_date_jst",
        "country",
        "event_name",
        "importance_label",
        "forecast",
        "actual",
        "previous",
    ]

    for e in events or []:
        event_dt = e.get("event_dt_jst")
        event_date = e.get("event_date_jst")

        row = {
            "timestamp_jst": now_jst().strftime("%Y-%m-%d %H:%M:%S"),
            "event_dt_jst": event_dt.strftime("%Y-%m-%d %H:%M:%S") if event_dt else "",
            "event_date_jst": event_date.strftime("%Y-%m-%d") if event_date else "",
            "country": e.get("country"),
            "event_name": e.get("event_name"),
            "importance_label": e.get("importance_label"),
            "forecast": e.get("forecast"),
            "actual": e.get("actual"),
            "previous": e.get("previous"),
        }

        append_csv_row(EVENT_LOG_FILE, fieldnames, row)
