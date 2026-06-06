from datetime import datetime
from config.settings import JST


def now_jst():
    return datetime.now(JST)
