from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import calendar
import re
import requests
from bs4 import BeautifulSoup

JST = ZoneInfo("Asia/Tokyo")

FOREX_FACTORY_URL = "https://www.forexfactory.com/calendar"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0 Safari/537.36"
    ),
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Referer": "https://www.forexfactory.com/",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

NO_RESULT_VALUES = {
    "",
    "-",
    "--",
    "---",
    "N/A",
    "n/a",
    "null",
    "None",
}

# 表示対象通貨
TARGET_CURRENCIES = {"USD", "JPY"}

# today / yesterday / week で残す最低重要度（3段階正規化後）
MIN_VISIBLE_IMPORTANCE = 2

# SUPER 限定キーワード
# CPI / Core CPI / PPI / 金利 / 雇用統計 のみ
SUPER_IMPORTANT_KEYWORDS = [
    # CPI / Core CPI
    "CPI",
    "Core CPI",

    # PPI
    "PPI",
    "Core PPI",

    # 金利
    "Interest Rate",
    "Rate Decision",
    "Main Refinancing Rate",
    "Deposit Facility Rate",
    "Monetary Policy Statement",
    "Rate Statement",
    "Policy Statement",

    # 雇用統計
    "Non-Farm",
    "Employment Change",
    "ADP Non-Farm Employment Change",
    "Unemployment Rate",
    "Average Hourly Earnings",
    "Jobless Claims",
    "Initial Jobless Claims",
    "Continuing Jobless Claims",
]

CURRENCY_TO_COUNTRY_JP = {
    "USD": "米国",
    "JPY": "日本",
}

EVENT_NAME_MAP = {
    # 金利
    "Interest Rate Decision": "政策金利",
    "Main Refinancing Rate": "主要政策金利",
    "Deposit Facility Rate": "中銀預金金利",
    "Monetary Policy Statement": "金融政策声明",
    "Rate Statement": "政策声明",
    "Policy Statement": "政策声明",
    "Press Conference": "記者会見",

    # CPI / PPI
    "Core CPI y/y": "コアCPI前年比",
    "Core CPI m/m": "コアCPI前月比",
    "CPI y/y": "消費者物価指数前年比",
    "CPI m/m": "消費者物価指数前月比",
    "Core PPI y/y": "コアPPI前年比",
    "Core PPI m/m": "コアPPI前月比",
    "PPI y/y": "生産者物価指数前年比",
    "PPI m/m": "生産者物価指数前月比",
    "PPI": "生産者物価指数",
    "CPI": "消費者物価指数",

    # 雇用
    "ADP Non-Farm Employment Change": "ADP雇用統計",
    "Non-Farm Employment Change": "非農業部門雇用者数変化",
    "Non Farm Employment Change": "非農業部門雇用者数変化",
    "Employment Change": "雇用者数変化",
    "Unemployment Rate": "失業率",
    "Average Hourly Earnings y/y": "平均時給前年比",
    "Average Hourly Earnings m/m": "平均時給前月比",
    "Initial Jobless Claims": "新規失業保険申請件数",
    "Continuing Jobless Claims": "継続失業保険申請件数",
    "Unemployment Claims": "失業保険申請件数",
    "Jobless Claims": "失業保険申請件数",

    # その他（中重要度候補）
    "Final GDP q/q": "GDP前期比改定値",
    "GDP q/q": "GDP前期比",
    "GDP y/y": "GDP前年比",
    "Final GDP Price Index y/y": "GDPデフレーター前年比改定値",
    "Retail Sales m/m": "小売売上高前月比",
    "Retail Sales y/y": "小売売上高前年比",
    "Trade Balance": "貿易収支",
    "Current Account": "経常収支",
    "Industrial Production m/m": "鉱工業生産前月比",
    "Industrial Production y/y": "鉱工業生産前年比",
    "Manufacturing PMI": "製造業PMI",
    "Final Manufacturing PMI": "製造業PMI改定値",
    "Services PMI": "サービス業PMI",
    "Consumer Confidence": "消費者信頼感",
    "Business Confidence": "企業景況感",
    "Bank Lending y/y": "銀行貸出前年比",
    "BOJ": "日銀関連",
    "FOMC": "FOMC関連",
}

MONTH_MAP = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


def _safe(v):
    return "" if v is None else str(v).strip()


def _normalize_text(text):
    if not text:
        return ""
    text = text.replace("\u3000", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _translate_country(currency_code: str) -> str:
    return CURRENCY_TO_COUNTRY_JP.get(currency_code, currency_code)


def _translate_event_name(name: str) -> str:
    if not name:
        return ""
    # 長いキーを先に当てる
    for k in sorted(EVENT_NAME_MAP.keys(), key=len, reverse=True):
        if k.lower() in name.lower():
            return EVENT_NAME_MAP[k]
    return name


def _is_super_event(raw_name: str) -> bool:
    name = _safe(raw_name).lower()
    return any(k.lower() in name for k in SUPER_IMPORTANT_KEYWORDS)


def _normalize_importance(rank: int) -> int:
    """
    元の importance を 3段階に正規化
    3 = 高
    2 = 中
    1 = 低
    """
    try:
        r = int(rank)
    except Exception:
        r = 1

    if r >= 3:
        return 3
    elif r == 2:
        return 2
    else:
        return 1


def _fallback_importance_rank_from_event_name(raw_name: str, currency: str) -> int:
    """
    class から impact が拾えない場合のベース重要度（元スコア）
    ここでは 1〜3 を返す前提で、
    後段で _normalize_importance に通して最終 3段階にする。
    """
    name = _safe(raw_name).lower()

    # SUPER 対象は高
    if _is_super_event(raw_name):
        return 3

    # today/yesterday/week に残したい中重要度候補
    medium_keywords = [
        "claims",
        "consumer confidence",
        "retail sales",
        "trade balance",
        "current account",
        "industrial production",
        "manufacturing pmi",
        "services pmi",
        "bank lending",
        "gdp",
    ]

    if any(k in name for k in medium_keywords):
        return 2

    return 1


def _importance_rank_from_td(td) -> int:
    """
    Forex Factory の impact を class / title / aria / html から抽出
    戻り値は元スコア（1〜3想定）
    """
    if td is None:
        return 1

    class_text = " ".join(td.get("class", [])).lower()
    title_text = _safe(td.get("title", "")).lower()
    aria_text = _safe(td.get("aria-label", "")).lower()
    text = _normalize_text(td.get_text(" ", strip=True)).lower()
    html = str(td).lower()

    combined = " ".join([class_text, title_text, aria_text, text, html])

    if "holiday" in combined:
        return 0
    if "high" in combined or "impact--3" in combined:
        return 3
    if "medium" in combined or "med" in combined or "impact--2" in combined:
        return 2
    if "low" in combined or "impact--1" in combined:
        return 1

    return 1


def _parse_time_to_hhmm(time_text: str) -> str:
    t = _normalize_text(time_text)
    if not t or t.lower() == "all day":
        return "00:00"

    m = re.match(r"^(\d{1,2}):(\d{2})(am|pm)$", t.lower())
    if m:
        hh, mm, ampm = m.groups()
        hh = int(hh)
        mm = int(mm)

        if ampm == "am":
            if hh == 12:
                hh = 0
        else:
            if hh != 12:
                hh += 12

        return f"{hh:02d}:{mm:02d}"

    m2 = re.match(r"^(\d{1,2}):(\d{2})$", t)
    if m2:
        hh, mm = m2.groups()
        return f"{int(hh):02d}:{int(mm):02d}"

    return "00:00"


def _parse_header_date(text: str, base_year: int):
    s = _normalize_text(text)

    m = re.search(
        r"(Sun(?:day)?|Mon(?:day)?|Tue(?:sday)?|Wed(?:nesday)?|Thu(?:rsday)?|Fri(?:day)?|Sat(?:urday)?)"
        r",?\s+([A-Za-z]{3,9})\s+(\d{1,2})(?:,?\s+(\d{4}))?",
        s,
        re.IGNORECASE,
    )
    if not m:
        return None

    _, month_str, day_str, year_str = m.groups()
    month = MONTH_MAP.get(month_str.lower())
    if not month:
        return None

    year = int(year_str) if year_str else base_year
    day = int(day_str)

    return f"{year:04d}-{month:02d}-{day:02d}"


def _extract_row_data(tr):
    tds = tr.find_all("td")
    if not tds:
        return None

    row = {
        "time": "",
        "currency": "",
        "event": "",
        "actual": "",
        "forecast": "",
        "previous": "",
        "importance_rank": 1,
    }

    impact_td = None

    # classベースで優先抽出
    for td in tds:
        cls = " ".join(td.get("class", [])).lower()
        txt = _normalize_text(td.get_text(" ", strip=True))

        if not row["time"] and "time" in cls:
            row["time"] = txt
        elif not row["currency"] and ("currency" in cls or "curr" in cls):
            row["currency"] = txt
        elif impact_td is None and "impact" in cls:
            impact_td = td
        elif not row["event"] and ("event" in cls or "title" in cls):
            row["event"] = txt
        elif not row["actual"] and "actual" in cls:
            row["actual"] = txt
        elif not row["forecast"] and ("forecast" in cls or "consensus" in cls):
            row["forecast"] = txt
        elif not row["previous"] and "previous" in cls:
            row["previous"] = txt

    if impact_td is not None:
        row["importance_rank"] = _importance_rank_from_td(impact_td)

    # 位置ベース fallback
    texts = [_normalize_text(td.get_text(" ", strip=True)) for td in tds]

    if not row["time"]:
        for txt in texts:
            if re.match(r"^\d{1,2}:\d{2}(am|pm)$", txt.lower()) or txt.lower() == "all day":
                row["time"] = txt
                break

    if not row["currency"]:
        for txt in texts:
            if re.match(r"^[A-Z]{3}$", txt):
                row["currency"] = txt
                break

    if not row["event"] and row["currency"] in texts:
        start_idx = texts.index(row["currency"]) + 1
        for txt in texts[start_idx:]:
            if not txt:
                continue
            if re.match(r"^[A-Z]{3}$", txt):
                continue
            if txt.lower() in {"detail", "graph", "alerts", "actual"}:
                continue
            row["event"] = txt
            break

    # 末尾3列救済
    if not row["actual"] and len(texts) >= 3:
        row["actual"] = texts[-3]
        row["forecast"] = texts[-2]
        row["previous"] = texts[-1]

    # impact 補完
    if row["importance_rank"] <= 1 and row["event"] and row["currency"]:
        row["importance_rank"] = _fallback_importance_rank_from_event_name(
            row["event"], row["currency"]
        )

    return row


def _fetch_html():
    session = requests.Session()
    session.headers.update(HEADERS)

    # best effort で JST 表示寄せ
    session.cookies.set("fftimezone", "Asia/Tokyo")
    session.cookies.set("timezone", "Asia/Tokyo")

    res = session.get(FOREX_FACTORY_URL, timeout=30)
    print("[DEBUG] forex factory status:", res.status_code)
    res.raise_for_status()

    html = res.text
    print("[DEBUG] forex factory html length:", len(html))
    return html


def _parse_forex_factory_calendar(html: str):
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.find_all("tr")
    print("[DEBUG] forex factory rows:", len(rows))

    now_jst = datetime.now(JST)
    base_year = now_jst.year
    current_date_iso = None
    events = []

    for tr in rows:
        tr_text = _normalize_text(tr.get_text(" ", strip=True))
        if not tr_text:
            continue

        maybe_date = _parse_header_date(tr_text, base_year)
        if maybe_date:
            current_date_iso = maybe_date
            if len(tr.find_all("td")) <= 1:
                continue

        row = _extract_row_data(tr)
        if not row:
            continue

        currency = _safe(row["currency"])
        raw_name = _safe(row["event"])

        if not currency or not raw_name:
            continue

        if currency not in TARGET_CURRENCIES:
            continue

        if not current_date_iso:
            continue

        raw_rank = int(row.get("importance_rank", 1))

        # 取り切れない場合はイベント名から補完
        if raw_rank < 2:
            raw_rank = _fallback_importance_rank_from_event_name(raw_name, currency)

        # 3段階へ正規化
        importance_rank = _normalize_importance(raw_rank)

        # today / yesterday / week 用には 2以上のみ採用
        if importance_rank < MIN_VISIBLE_IMPORTANCE:
            continue

        actual = _safe(row.get("actual"))
        forecast = _safe(row.get("forecast"))
        previous = _safe(row.get("previous"))

        is_super = (_is_super_event(raw_name) and importance_rank == 3)

        event = {
            "event_date_jst": current_date_iso,
            "event_time_jst": _parse_time_to_hhmm(row.get("time", "")),
            "country": _translate_country(currency),
            "currency": currency,
            "event_name": _translate_event_name(raw_name),
            "event_name_raw": raw_name,
            "forecast": forecast,
            "actual": actual,
            "previous": previous,
            "importance_label": str(importance_rank),
            "importance_rank": importance_rank,  # ここは3段階後の値
            "event_status": "予定" if actual in NO_RESULT_VALUES else "結果",
            "is_super": is_super,
        }

        events.append(event)

    # 重複排除
    dedup = {}
    for e in events:
        key = (
            e["event_date_jst"],
            e["event_time_jst"],
            e["currency"],
            e["event_name_raw"],
        )
        dedup[key] = e

    events = list(dedup.values())
    events.sort(key=lambda x: (x["event_date_jst"], x["event_time_jst"], x["currency"]))

    print("[INFO] ForexFactory events parsed:", len(events))
    if events:
        print("[DEBUG] first 5 events:", events[:5])

    return events


def fetch_economic_events():
    try:
        html = _fetch_html()
        return _parse_forex_factory_calendar(html)
    except Exception as e:
        print("[ERROR] ForexFactory fetch:", e)
        return []


def _parse_event_datetime_jst(event):
    try:
        date_str = event.get("event_date_jst", "")
        time_str = event.get("event_time_jst", "00:00")
        if not time_str:
            time_str = "00:00"

        return datetime.strptime(
            f"{date_str} {time_str}",
            "%Y-%m-%d %H:%M",
        ).replace(tzinfo=JST)
    except Exception:
        return None


def _end_of_current_month(now_dt):
    year = now_dt.year
    month = now_dt.month
    last_day = calendar.monthrange(year, month)[1]
    return now_dt.replace(
        day=last_day,
        hour=23,
        minute=59,
        second=59,
        microsecond=0,
    )


def split_events_for_mail(events, now_dt):
    """
    出力:
    - super_important_events:
        当月の SUPER のみ。月末まで残す。
    - yesterday_events:
        昨日の重要指標（importance >= 2）。結果付きで当日中表示。
    - today_events:
        今日の重要指標（importance >= 2）。予定/結果どちらも表示。
    - week_events:
        今日より後〜今週末の upcoming 重要指標（importance >= 2）のみ。
        発表済みになったら消える。
    """
    now = now_dt.astimezone(JST)
    today = now.date()
    yesterday = today - timedelta(days=1)
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    month_end = _end_of_current_month(now).date()

    super_important_events = []
    yesterday_events = []
    today_events = []
    week_events = []

    for e in events:
        dt = _parse_event_datetime_jst(e)
        if not dt:
            continue

        event_date = dt.date()
        event_status = e.get("event_status", "予定")
        importance_rank = int(e.get("importance_rank", 0))
        is_super = bool(e.get("is_super", False))

        # safety filter
        if e.get("currency") not in TARGET_CURRENCIES:
            continue

        # ------------------------
        # ① SUPER（3のみ）
        # ------------------------
        if is_super and event_date.year == now.year and event_date.month == now.month and event_date <= month_end:
            super_important_events.append(e)

        # ------------------------
        # ② 昨日（2以上）
        # ------------------------
        if event_date == yesterday and importance_rank >= 2:
            yesterday_events.append(e)

        # ------------------------
        # ③ 本日（2以上）
        # ------------------------
        if event_date == today and importance_rank >= 2:
            today_events.append(e)

        # ------------------------
        # ④ 今週（2以上 + 未発表のみ）
        # ------------------------
        if (
            today < event_date <= end_of_week
            and event_status == "予定"
            and importance_rank >= 2
        ):
            week_events.append(e)

    super_important_events.sort(key=lambda x: (x["event_date_jst"], x["event_time_jst"], x["currency"]))
    yesterday_events.sort(key=lambda x: (x["event_time_jst"], x["currency"]))
    today_events.sort(key=lambda x: (x["event_time_jst"], x["currency"]))
    week_events.sort(key=lambda x: (x["event_date_jst"], x["event_time_jst"], x["currency"]))

    print(
        "[INFO]",
        f"yesterday={len(yesterday_events)}",
        f"today={len(today_events)}",
        f"week={len(week_events)}",
        f"super={len(super_important_events)}",
    )

    return {
        "super_important_events": super_important_events,
        "yesterday_events": yesterday_events,
        "today_events": today_events,
        "week_events": week_events,
    }


# =========================
# backward compatibility
# =========================
def fetch_minkabu_economic_events():
    return fetch_economic_events()
