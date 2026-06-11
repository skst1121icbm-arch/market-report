from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
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

# 通貨コード → 表示用
CURRENCY_TO_COUNTRY_JP = {
    "USD": "米国",
    "JPY": "日本",
    "EUR": "ユーロ圏",
    "GBP": "英国",
    "AUD": "豪州",
    "NZD": "NZ",
    "CAD": "カナダ",
    "CHF": "スイス",
    "CNY": "中国",
}

# 指標名をざっくり日本語化（部分一致）
EVENT_NAME_MAP = {
    "Interest Rate Decision": "政策金利",
    "Main Refinancing Rate": "主要政策金利",
    "Deposit Facility Rate": "中銀預金金利",
    "Monetary Policy Statement": "金融政策声明",
    "Press Conference": "記者会見",
    "CPI y/y": "消費者物価指数前年比",
    "CPI m/m": "消費者物価指数前月比",
    "Core CPI y/y": "コアCPI前年比",
    "Core CPI m/m": "コアCPI前月比",
    "PPI y/y": "生産者物価指数前年比",
    "PPI m/m": "生産者物価指数前月比",
    "Core PPI y/y": "コアPPI前年比",
    "Core PPI m/m": "コアPPI前月比",
    "Final GDP q/q": "GDP前期比改定値",
    "GDP q/q": "GDP前期比",
    "GDP y/y": "GDP前年比",
    "Final GDP Price Index y/y": "GDPデフレーター前年比改定値",
    "Unemployment Claims": "失業保険申請件数",
    "Initial Jobless Claims": "新規失業保険申請件数",
    "Continuing Jobless Claims": "継続失業保険申請件数",
    "Non-Farm Employment Change": "非農業部門雇用者数変化",
    "Non Farm Employment Change": "非農業部門雇用者数変化",
    "Average Hourly Earnings m/m": "平均時給前月比",
    "Average Hourly Earnings y/y": "平均時給前年比",
    "Unemployment Rate": "失業率",
    "Retail Sales m/m": "小売売上高前月比",
    "Retail Sales y/y": "小売売上高前年比",
    "Core Retail Sales m/m": "小売売上高コア前月比",
    "Trade Balance": "貿易収支",
    "Current Account": "経常収支",
    "Industrial Production m/m": "鉱工業生産前月比",
    "Industrial Production y/y": "鉱工業生産前年比",
    "Manufacturing PMI": "製造業PMI",
    "Services PMI": "サービス業PMI",
    "Final Manufacturing PMI": "製造業PMI改定値",
    "Final Services PMI": "サービス業PMI改定値",
    "Consumer Confidence": "消費者信頼感",
    "Business Confidence": "企業景況感",
    "Building Permits m/m": "建設許可件数前月比",
    "Bank Lending y/y": "銀行貸出前年比",
    "PPI": "生産者物価指数",
    "CPI": "消費者物価指数",
    "FOMC": "FOMC関連",
    "BOJ": "日銀関連",
    "ECB": "ECB関連",
    "RBA": "RBA関連",
    "BoC": "BOC関連",
}

SUPER_IMPORTANT_KEYWORDS = [
    "CPI",
    "消費者物価指数",
    "PPI",
    "政策金利",
    "主要政策金利",
    "FOMC",
    "非農業部門雇用者数",
    "失業率",
    "GDP",
    "金融政策声明",
    "記者会見",
]

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
    for k, v in EVENT_NAME_MAP.items():
        if k.lower() in name.lower():
            return v
    return name


def _importance_rank_from_text_or_html(cell_text: str, cell_html: str) -> int:
    text = (cell_text or "").lower()
    html = (cell_html or "").lower()

    # class やテキストから high / medium / low を拾う
    if "holiday" in text or "holiday" in html:
        return 0
    if "high" in text or "high" in html:
        return 3
    if "medium" in text or "medium" in html or "med" in text:
        return 2
    if "low" in text or "low" in html:
        return 1

    # アイコン数で表現されている場合のざっくり救済
    # impact class の数や span 数を見たいが、HTML構造変更に備えて簡易化
    return 1


def _parse_time_to_jst_hhmm(time_text: str) -> str:
    """
    '8:30am', '10:00pm', 'All Day' などを JST HH:MM にそのまま整形。
    ここでは page に表示されている時刻をそのまま使う前提。
    """
    t = _normalize_text(time_text)
    if not t or t.lower() == "all day":
        return "00:00"

    m = re.match(r"^(\d{1,2}):(\d{2})(am|pm)$", t.lower())
    if not m:
        # すでに 24h の可能性
        m2 = re.match(r"^(\d{1,2}):(\d{2})$", t)
        if m2:
            hh, mm = m2.groups()
            return f"{int(hh):02d}:{int(mm):02d}"
        return "00:00"

    hh, mm, ampm = m.groups()
    hh = int(hh)
    mm = int(mm)

    if ampm == "am":
        if hh == 12:
            hh = 0
    elif ampm == "pm":
        if hh != 12:
            hh += 12

    return f"{hh:02d}:{mm:02d}"


def _parse_header_date(text: str, base_year: int) -> str | None:
    """
    'Mon Jun 8' / 'Monday, Jun 8, 2026' / 'Sun Feb 1' などを ISO に。
    """
    s = _normalize_text(text)

    # Monday, Jun 8, 2026
    m = re.search(
        r"(Sun(?:day)?|Mon(?:day)?|Tue(?:sday)?|Wed(?:nesday)?|Thu(?:rsday)?|Fri(?:day)?|Sat(?:urday)?)"
        r",?\s+([A-Za-z]{3,9})\s+(\d{1,2})(?:,?\s+(\d{4}))?",
        s,
        re.IGNORECASE,
    )
    if m:
        _dow, month_str, day_str, year_str = m.groups()
        month = MONTH_MAP.get(month_str.lower())
        if month:
            year = int(year_str) if year_str else base_year
            day = int(day_str)
            return f"{year:04d}-{month:02d}-{day:02d}"

    return None


def _extract_cells_from_row(tr):
    """
    class ベースで拾いつつ、だめなら位置ベースで拾う。
    """
    tds = tr.find_all("td")
    if not tds:
        return None

    items = []
    for td in tds:
        classes = " ".join(td.get("class", []))
        text = _normalize_text(td.get_text(" ", strip=True))
        html = str(td)
        items.append({
            "classes": classes,
            "text": text,
            "html": html,
        })

    # まず class ベース
    by_class = {
        "time": "",
        "currency": "",
        "impact_text": "",
        "impact_html": "",
        "event": "",
        "actual": "",
        "forecast": "",
        "previous": "",
    }

    for item in items:
        cls = item["classes"].lower()
        txt = item["text"]

        if ("time" in cls) and not by_class["time"]:
            by_class["time"] = txt
        elif ("currency" in cls or "curr" in cls) and not by_class["currency"]:
            by_class["currency"] = txt
        elif ("impact" in cls) and not by_class["impact_html"]:
            by_class["impact_text"] = txt
            by_class["impact_html"] = item["html"]
        elif ("event" in cls or "title" in cls) and not by_class["event"]:
            by_class["event"] = txt
        elif ("actual" in cls) and not by_class["actual"]:
            by_class["actual"] = txt
        elif ("forecast" in cls or "consensus" in cls) and not by_class["forecast"]:
            by_class["forecast"] = txt
        elif ("previous" in cls) and not by_class["previous"]:
            by_class["previous"] = txt

    # 充分拾えていれば採用
    if by_class["currency"] and by_class["event"]:
        return by_class

    # fallback: 位置ベース
    texts = [x["text"] for x in items]

    # time
    time_idx = None
    for i, txt in enumerate(texts):
        if re.match(r"^\d{1,2}:\d{2}(am|pm)$", txt.lower()) or txt.lower() == "all day":
            time_idx = i
            break

    if time_idx is None:
        return None

    # currency = timeの次あたりに出る 3文字コード
    currency_idx = None
    for i in range(time_idx + 1, min(len(texts), time_idx + 5)):
        txt = texts[i]
        if re.match(r"^[A-Z]{3}$", txt):
            currency_idx = i
            break

    if currency_idx is None:
        return None

    # event = currency の後に来る、actual/forecast/previousっぽくない最初のテキスト
    event_idx = None
    for i in range(currency_idx + 1, len(texts)):
        txt = texts[i]
        if not txt:
            continue
        if re.match(r"^[A-Z]{3}$", txt):
            continue
        if txt.lower() in {"detail", "graph", "alerts", "actual"}:
            continue
        event_idx = i
        break

    if event_idx is None:
        return None

    # actual/forecast/previous は末尾3列想定で救済
    tail = texts[-3:] if len(texts) >= 3 else ["", "", ""]
    actual = tail[0] if len(tail) >= 1 else ""
    forecast = tail[1] if len(tail) >= 2 else ""
    previous = tail[2] if len(tail) >= 3 else ""

    # impact は event のひとつ前あたりを雑に見る
    impact_text = texts[currency_idx + 1] if currency_idx + 1 < len(texts) else ""
    impact_html = items[currency_idx + 1]["html"] if currency_idx + 1 < len(items) else ""

    return {
        "time": texts[time_idx],
        "currency": texts[currency_idx],
        "impact_text": impact_text,
        "impact_html": impact_html,
        "event": texts[event_idx],
        "actual": actual,
        "forecast": forecast,
        "previous": previous,
    }


def _fetch_html():
    session = requests.Session()
    session.headers.update(HEADERS)

    # JST 表示を狙う best-effort の cookie
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

    events = []
    now_jst = datetime.now(JST)
    base_year = now_jst.year
    current_date_iso = None

    rows = soup.find_all("tr")
    print("[DEBUG] forex factory rows:", len(rows))

    for tr in rows:
        tr_text = _normalize_text(tr.get_text(" ", strip=True))
        if not tr_text:
            continue

        # 日付ヘッダ判定
        maybe_date = _parse_header_date(tr_text, base_year)
        if maybe_date:
            current_date_iso = maybe_date
            # ヘッダ行の場合は次へ
            # 同じ tr に event が入っていないことが多い
            if len(tr.find_all("td")) <= 1:
                continue

        cells = _extract_cells_from_row(tr)
        if not cells:
            continue

        currency = _safe(cells["currency"])
        event_name_raw = _safe(cells["event"])
        if not currency or not event_name_raw:
            continue

        # currency が想定外なら除外
        if not re.match(r"^[A-Z]{3}$", currency):
            continue

        if not current_date_iso:
            # 日付ヘッダが先に見つからないケースの救済はしない
            continue

        event_time_jst = _parse_time_to_jst_hhmm(cells["time"])
        importance_rank = _importance_rank_from_text_or_html(
            cells.get("impact_text", ""),
            cells.get("impact_html", ""),
        )

        actual = _safe(cells["actual"])
        forecast = _safe(cells["forecast"])
        previous = _safe(cells["previous"])

        event_status = "予定" if actual in NO_RESULT_VALUES else "結果"

        event = {
            "event_date_jst": current_date_iso,
            "event_time_jst": event_time_jst,
            "country": _translate_country(currency),
            "currency": currency,
            "event_name": _translate_event_name(event_name_raw),
            "event_name_raw": event_name_raw,
            "forecast": forecast,
            "actual": actual,
            "previous": previous,
            "importance_label": str(importance_rank),
            "importance_rank": int(importance_rank),
            "event_status": event_status,
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


def split_events_for_mail(events, now_dt):
    now = now_dt.astimezone(JST)
    today = now.date()
    yesterday = today - timedelta(days=1)
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    yesterday_events = []
    today_events = []
    week_events = []
    super_important_events = []

    for e in events:
        dt = _parse_event_datetime_jst(e)
        if not dt:
            continue

        event_date = dt.date()

        # 昨日（中〜高重要度）
        if event_date == yesterday and e.get("importance_rank", 0) >= 2:
            yesterday_events.append(e)

        # 今日（中〜高重要度）
        if event_date == today and e.get("importance_rank", 0) >= 2:
            today_events.append(e)

        # 今週の残り（予定のみ）
        if today < event_date <= end_of_week and e.get("event_status") == "予定":
            if e.get("importance_rank", 0) >= 2:
                week_events.append(e)

        # 超重要イベント
        name = str(e.get("event_name", "")) + " " + str(e.get("event_name_raw", ""))
        if event_date >= today and any(k.lower() in name.lower() for k in SUPER_IMPORTANT_KEYWORDS):
            super_important_events.append(e)

    yesterday_events.sort(key=lambda x: (x["event_time_jst"], x["currency"]))
    today_events.sort(key=lambda x: (x["event_time_jst"], x["currency"]))
    week_events.sort(key=lambda x: (x["event_date_jst"], x["event_time_jst"], x["currency"]))
    super_important_events.sort(key=lambda x: (x["event_date_jst"], x["event_time_jst"], x["currency"]))

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
