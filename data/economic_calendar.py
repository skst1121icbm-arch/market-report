from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import re
import requests
from bs4 import BeautifulSoup

JST = ZoneInfo("Asia/Tokyo")
MINKABU_URL = "https://fx.minkabu.jp/indicators/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7",
}

TARGET_COUNTRIES = {"日本", "アメリカ"}

COUNTRY_ALIASES = {
    "日本": "日本",
    "jp": "日本",
    "japan": "日本",
    "アメリカ": "アメリカ",
    "米国": "アメリカ",
    "米": "アメリカ",
    "us": "アメリカ",
    "usa": "アメリカ",
    "united states": "アメリカ",
}

SUPER_IMPORTANT_KEYWORDS = [
    "cpi",
    "消費者物価",
    "fomc",
    "政策金利",
    "雇用統計",
    "非農業部門雇用者数",
    "失業率",
    "pce",
    "ism",
    "小売売上高",
    "gdp",
    "日銀",
    "boj",
    "パウエル",
]


# =========================
# BASIC HELPERS
# =========================
def _safe(v):
    if v in [None, "", "None"]:
        return ""
    return str(v).strip()


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\u3000", " ")
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _jp_date_to_iso(text: str) -> str:
    """
    '2026年06月08日' -> '2026-06-08'
    """
    m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", _normalize_text(text))
    if not m:
        return ""
    y, mo, d = m.groups()
    return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"


def _normalize_country(text: str) -> str:
    s = _normalize_text(text).lower()
    for k, v in COUNTRY_ALIASES.items():
        if s == k.lower():
            return v
    return ""


def _extract_time(text: str) -> str:
    """
    例:
      '21:30' -> '21:30'
      '未定' / '--:--' -> ''
    """
    s = _normalize_text(text)
    m = re.search(r"(\d{1,2}):(\d{2})", s)
    if not m:
        return ""
    hh, mm = m.groups()
    return f"{int(hh):02d}:{mm}"


def _looks_like_numberish(text: str) -> bool:
    s = _normalize_text(text)
    if not s:
        return False
    if s in {"-", "—", "N/A", "n/a"}:
        return True
    return bool(re.search(r"[0-9]", s))


def _extract_importance(cells) -> str:
    """
    High / Medium / Low を緩めに判定
    """
    joined = " ".join([_normalize_text(c) for c in cells])

    if re.search(r"(高|重要|★★★)", joined):
        return "高"
    if re.search(r"(中|★★)", joined):
        return "中"
    if re.search(r"(低|★)", joined):
        return "低"

    if "importance-high" in joined.lower():
        return "高"
    if "importance-middle" in joined.lower():
        return "中"
    if "importance-low" in joined.lower():
        return "低"

    return ""


def _extract_status(cells) -> str:
    """
    '結果' / '予定' / '発表前' / '未定' などを緩めに判定
    """
    joined = " ".join([_normalize_text(c) for c in cells])

    if "結果" in joined:
        return "結果"
    if "予定" in joined:
        return "予定"
    if "未定" in joined:
        return "未定"
    if "発表前" in joined:
        return "予定"

    return ""


def _is_super_important(event) -> bool:
    name = _normalize_text(event.get("event_name", "")).lower()
    if event.get("importance_label") == "高":
        return True
    for kw in SUPER_IMPORTANT_KEYWORDS:
        if kw in name:
            return True
    return False


# =========================
# FETCH
# =========================
def _fetch_html():
    res = requests.get(MINKABU_URL, headers=HEADERS, timeout=30)
    res.raise_for_status()
    return res.text


# =========================
# PARSE MINKABU
# =========================
def _find_nearest_date_text(tr):
    """
    tr より前方にある 'YYYY年MM月DD日' を探す
    """
    cur = tr
    for _ in range(20):
        cur = cur.find_previous()
        if cur is None:
            break
        txt = _normalize_text(cur.get_text(" ", strip=True))
        iso = _jp_date_to_iso(txt)
        if iso:
            return iso
    return ""


def _parse_row_cells(cells, event_date_jst):
    """
    1行セルからイベント生成
    想定:
      時刻 / 国 / 指標 / 予想 / 結果 / 前回 / 重要度...
    HTML変化に備えてゆるく判定する
    """
    if len(cells) < 3:
        return None

    norm_cells = [_normalize_text(c) for c in cells]

    # 国候補
    country_idx = None
    country_val = ""
    for i, c in enumerate(norm_cells):
        nc = _normalize_country(c)
        if nc in TARGET_COUNTRIES:
            country_idx = i
            country_val = nc
            break

    if country_idx is None:
        return None

    # 時刻候補
    time_val = ""
    for i in range(0, min(country_idx + 1, len(norm_cells))):
        t = _extract_time(norm_cells[i])
        if t:
            time_val = t
            break

    # 指標名候補
    event_name = ""
    event_name_idx = None
    for i in range(country_idx + 1, len(norm_cells)):
        c = norm_cells[i]
        if not c:
            continue
        if _looks_like_numberish(c):
            continue
        if c in {"結果", "予定", "高", "中", "低"}:
            continue
        if len(c) >= 2:
            event_name = c
            event_name_idx = i
            break

    if not event_name:
        return None

    # 残り数値っぽいセル
    numberish = []
    for i in range(event_name_idx + 1, len(norm_cells)):
        c = norm_cells[i]
        if _looks_like_numberish(c):
            numberish.append(c)

    forecast = numberish[0] if len(numberish) >= 1 else ""
    actual = numberish[1] if len(numberish) >= 2 else ""
    previous = numberish[2] if len(numberish) >= 3 else ""

    importance = _extract_importance(norm_cells)
    status = _extract_status(norm_cells)

    if not status:
        status = "結果" if actual else "予定"

    return {
        "event_date_jst": event_date_jst,
        "event_time_jst": time_val,
        "country": country_val,
        "event_name": event_name,
        "forecast": forecast,
        "actual": actual,
        "previous": previous,
        "importance_label": importance,
        "event_status": status,
    }


def _parse_minkabu_calendar(html: str):

    soup = BeautifulSoup(html, "html.parser")

    text = soup.get_text("\n", strip=True)
    lines = [_normalize_text(x) for x in text.split("\n") if _normalize_text(x)]

    events = []
    current_date = ""

    for line in lines:

        # ======================
        # 日付更新
        # ======================
        iso = _jp_date_to_iso(line)
        if iso:
            current_date = iso
            continue

        # ======================
        # 条件フィルタ
        # ======================
        if not re.search(r"\d{1,2}:\d{2}", line):
            continue

        if not ("日本" in line or "米" in line or "アメリカ" in line):
            continue

        # ======================
        # 国
        # ======================
        if "日本" in line:
            country = "日本"
        else:
            country = "アメリカ"

        # ======================
        # 時刻
        # ======================
        m = re.search(r"\d{1,2}:\d{2}", line)
        time_val = m.group(0) if m else ""

        # ======================
        # 指標名
        # ======================
        event_name = line.split(time_val, 1)[-1].strip()
        if not event_name:
            continue

        events.append({
            "event_date_jst": current_date,
            "event_time_jst": time_val,
            "country": country,
            "event_name": event_name,
            "forecast": "",
            "actual": "",
            "previous": "",
            "importance_label": "",
            "event_status": "予定",
        })

    return events


# =========================
# FALLBACK
# =========================
def fallback_events():
    """
    取得失敗時の最小フォールバック
    """
    return [
        {
            "event_date_jst": "2026-06-05",
            "event_time_jst": "21:30",
            "country": "アメリカ",
            "event_name": "非農業部門雇用者数（NFP）",
            "forecast": "85K",
            "actual": "172K",
            "previous": "179K",
            "importance_label": "高",
            "event_status": "結果",
        },
        {
            "event_date_jst": "2026-06-05",
            "event_time_jst": "21:30",
            "country": "アメリカ",
            "event_name": "失業率",
            "forecast": "4.3%",
            "actual": "4.3%",
            "previous": "4.3%",
            "importance_label": "高",
            "event_status": "結果",
        },
    ]


# =========================
# PUBLIC FETCH FUNCTION
# =========================
def fetch_minkabu_economic_events():
    try:
        html = _fetch_html()
        events = _parse_minkabu_calendar(html)
        if not events:
            return fallback_events()
        return events
    except Exception as e:
        print("[WARN] minkabu economic calendar fallback:", e)
        return fallback_events()


# =========================
# DATETIME PARSER (JST)
# =========================
def _parse_event_datetime_jst(event):
    """
    event_date_jst + event_time_jst を JST の datetime に変換
    """
    date_str = _safe(event.get("event_date_jst"))
    time_str = _safe(event.get("event_time_jst"))

    if not date_str:
        return None

    if not time_str:
        time_str = "00:00"

    try:
        dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        return dt.replace(tzinfo=JST)
    except Exception:
        return None


# =========================
# SPLIT FOR MAIL
# =========================
def split_events_for_mail(events, now_dt):
    """
    日本時間基準で:
    - yesterday_events
    - today_events
    - week_events（今週・重要）
    - super_important_events
    に分割する
    """
    now = now_dt.astimezone(JST)
    today = now.date()
    end_of_week_window = today + timedelta(days=7)

    # 古すぎるイベントを事前除外
    cleaned_events = []
    for e in events or []:
        dt = _parse_event_datetime_jst(e)
        if not dt:
            continue

        d = dt.date()

        # 7日より前は完全除外
        if d < (today - timedelta(days=7)):
            continue

        cleaned_events.append(e)

    yesterday_events = []
    today_events = []
    week_events = []
    super_important_events = []

    for e in cleaned_events:
        dt = _parse_event_datetime_jst(e)
        if not dt:
            continue

        d = dt.date()

        # 昨日
        if d == (today - timedelta(days=1)):
            yesterday_events.append(e)

        # 今日
        if d == today:
            today_events.append(e)

        # 今週（未来7日以内 / 今日は含む）
        if today <= d <= end_of_week_window:
            if e.get("importance_label") in {"高", "中"} or _is_super_important(e):
                week_events.append(e)

        # 超重要
        if _is_super_important(e):
            super_important_events.append(e)

    def _sort_key(x):
        return (_safe(x.get("event_date_jst")), _safe(x.get("event_time_jst")))

    yesterday_events = sorted(yesterday_events, key=_sort_key)
    today_events = sorted(today_events, key=_sort_key)
    week_events = sorted(week_events, key=_sort_key)
    super_important_events = sorted(super_important_events, key=_sort_key)

    return {
        "yesterday_events": yesterday_events,
        "today_events": today_events,
        "week_events": week_events,
        "super_important_events": super_important_events[:10],
    }
