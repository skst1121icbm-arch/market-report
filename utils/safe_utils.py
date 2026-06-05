def safe_float(v):
    try:
        return float(v)
    except Exception:
        return None

def safe_execute(label, func, default=None):
    try:
        return func(), None
    except Exception as e:
        err = f"{label} エラー: {str(e)}"
        from utils.logging_utils import log_error
        log_error(err)
        return default, err