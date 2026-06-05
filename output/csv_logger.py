import os
import csv
from config.settings import DAILY_LOG_FILE, EVENT_LOG_FILE
from utils.datetime_utils import now_jst


def ensure_csv_header(file_path, fieldnames):
    write_header = not os.path.exists(file_path) or os.path.getsize(file_path) == 0

    if write_header:
        with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()


def append_csv_row(file_path, fieldnames, row):
    ensure_csv_header(file_path, fieldnames)

    with open(file_path, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writerow(row)


def save_daily_log(score, regime, signal):
    fieldnames = ["timestamp", "score", "regime", "signal"]

    row = {
        "timestamp": now_jst().strftime("%Y-%m-%d %H:%M:%S"),
        "score": score,
        "regime": regime,
        "signal": signal,
    }

    append_csv_row(DAILY_LOG_FILE, fieldnames, row)


def save_event_log(events):
    fieldnames = ["timestamp", "event_name"]

    for e in events or []:
        row = {
            "timestamp": now_jst().strftime("%Y-%m-%d %H:%M:%S"),
            "event_name": e.get("event_name"),
        }
        append_csv_row(EVENT_LOG_FILE, fieldnames, row)