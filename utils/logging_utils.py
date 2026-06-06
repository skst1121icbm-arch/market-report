from config.settings import ERROR_LOG_FILEfrom config.settings.datetime_utils import now_jst


def log_error(msg, file_path=ERROR_LOG_FILE):
    try:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(f"{now_jst().strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")
    except Exception:
        pass
