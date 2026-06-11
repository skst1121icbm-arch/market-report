from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import re
import requests
from bs4 import BeautifulSoup

JST = ZoneInfo("Asia/Tokyo")

FRB_SPEECHES_URL = "https://www.federalreserve.gov/newsevents/speeches-testimony.htm"
BOJ_PRESS_URL = "https://www.boj.or.jp/about/press/index.htm"
BOJ_SPEECHES_2026_URL = "https://www.boj.or.jp/en/about/press/koen_2026/index.htm"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0 Safari/537.36"
    ),
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

MONTHS = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}

# 高インパクト（SUPER相当）
HIGH_IMPACT_KEYWORDS = [
    "cpi", "core cpi",
    "ppi", "core ppi",
    "inflation", "prices",
    "interest rate", "rate decision",
    "monetary policy", "policy statement", "rate statement",
    "non-farm", "employment",
    "jobless claims", "initial jobless claims", "continuing jobless claims",
    "unemployment rate", "average hourly earnings",
]

# 中インパクト
MEDIUM_IMPACT_KEYWORDS = [
    "economy", "economic", "growth", "financial conditions",
    "yield", "wages", "labor", "demand",
    "retail sales", "trade balance", "current account",
    "industrial production", "manufacturing", "services",
    "consumer confidence", "bank lending", "gdp",
]

# ノイズ除外
LOW_SIGNAL_KEYWORDS = [
    "acceptance remarks",
    "opening remarks",
    "welcoming remarks",
    "introductory remarks",
    "award",
    "conference opening",
]

def _safe(v):
    return "" if v is None else str(v).strip()

def _normalize_text(text):
    if not text:
        return ""
    text = text.replace("\u3000", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def _fetch_html(url):
    session = requests.Session()
    session.headers.update(HEADERS)
    res = session.get(url, timeout=30)
    print(f"[DEBUG] policy fetch status {url}: {res.status_code}")
    res.raise_for_status()
    return res.text

def _parse_date_any(text: str):
    """
    対応:
    - 6/6/2026
    - June 3, 2026
    - 2026年 6月 8日
    - 2026年6月8日
    """
    s = _normalize_text(text)

    # US形式 6/6/2026
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        month, day, year = m.groups()
        return datetime(int(year), int(month), int(day), tzinfo=JST).date()

    # US形式 June 3, 2026
    m = re.search(r"([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})", s)
    if m:
        month_str, day, year = m.groups()
        month = MONTHS.get(month_str.lower())
        if month:
            return datetime(int(year), month, int(day), tzinfo=JST).date()

    # JP形式 2026年 6月 8日 / 2026年6月8日
    m = re.search(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日", s)
    if m:
        year, month, day = m.groups()
        return datetime(int(year), int(month), int(day), tzinfo=JST).date()

    return None

def _is_cpi_linked(title: str) -> bool:
    t = _safe(title).lower()
    return any(k in t for k in ["cpi", "core cpi", "ppi", "core ppi", "inflation", "prices"])

def _is_super_policy(title: str) -> bool:
    t = _safe(title).lower()
    super_keywords = [
        "cpi", "core cpi",
        "ppi", "core ppi",
        "inflation", "prices",
        "interest rate", "rate decision", "monetary policy", "policy statement", "rate statement",
        "non-farm", "employment", "jobless claims", "unemployment rate", "average hourly earnings",
    ]
    return any(k in t for k in super_keywords)

def _market_impact_score(title: str, speaker: str = "", source_type: str = "") -> int:
    """
    3 = 高 / 2 = 中 / 1 = 低
    """
    text = f"{_safe(title)} {_safe(speaker)} {_safe(source_type)}".lower()

    if any(k in text for k in LOW_SIGNAL_KEYWORDS):
        return 1
    if any(k in text for k in HIGH_IMPACT_KEYWORDS):
        return 3
    if any(k in text for k in MEDIUM_IMPACT_KEYWORDS):
        return 2
    return 1

def _market_impact_stars(score: int) -> str:
    if score >= 3:
        return "★★★"
    elif score == 2:
        return "★★"
    return "★"

def _title_is_market_relevant(title: str, speaker: str = "", source_type: str = "") -> bool:
    return _market_impact_score(title, speaker, source_type) >= 2

def _market_relevance_comment(title: str, speaker: str, source_type: str) -> str:
    text = f"{_safe(title)} {_safe(speaker)} {_safe(source_type)}".lower()

    if any(k in text for k in ["cpi", "core cpi", "ppi", "core ppi", "inflation", "prices"]):
        return "インフレ・金利観測に関連"
    if any(k in text for k in ["interest rate", "rate decision", "monetary policy", "policy statement"]):
        return "政策金利・金融政策に関連"
    if any(k in text for k in ["non-farm", "employment", "jobless claims", "unemployment rate", "average hourly earnings"]):
        return "雇用・景気見通しに関連"
    if any(k in text for k in ["economy", "economic", "growth", "financial conditions", "yield", "wages"]):
        return "景気・金利・金融環境に関連"

    if source_type == "FRB":
        return "米金融政策の文脈で注目"
    if source_type == "BOJ":
        return "日銀政策・円相場の文脈で注目"
    if source_type == "NEWS":
        return "市場材料として要確認"
    return "市場材料として要確認"

def _summarize_title(title: str, source_type: str) -> str:
    """
    記事本文要約はしない。タイトルから市場向け一言を返す。
    """
    t = _safe(title)

    if re.search(r"cpi|core cpi|ppi|core ppi|inflation|prices", t, re.IGNORECASE):
        return "物価・インフレ見通しの材料"
    if re.search(r"interest rate|rate decision|monetary policy|policy statement", t, re.IGNORECASE):
        return "政策金利・金融政策の材料"
    if re.search(r"non-farm|employment|jobless claims|unemployment rate|average hourly earnings", t, re.IGNORECASE):
        return "雇用・景気判断の材料"
    if re.search(r"economy|economic|growth|financial conditions|yield|wages", t, re.IGNORECASE):
        return "景気・金利環境の材料"

    if source_type == "FRB":
        return "FRB高官発言として確認対象"
    if source_type == "BOJ":
        return "日銀発言として確認対象"
    return "市場材料として確認"

def _make_item(source, date_obj, speaker, title, url):
    impact_score = _market_impact_score(title, speaker, source)
    return {
        "source": source,
        "date_jst": date_obj.strftime("%Y-%m-%d"),
        "speaker": speaker,
        "title": title,
        "summary": _summarize_title(title, source),
        "market_relevance": _market_relevance_comment(title, speaker, source),
        "market_impact_score": impact_score,
        "market_impact_stars": _market_impact_stars(impact_score),
        "is_super": _is_super_policy(title),
        "is_cpi_linked": _is_cpi_linked(title),
        "url": url,
    }

def _parse_frb_items(html: str, target_dates):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)
    lines = [_normalize_text(x) for x in text.splitlines() if _normalize_text(x)]

    items = []
    i = 0
    while i < len(lines):
        line = lines[i]
        dt = _parse_date_any(line)
        if dt and dt in target_dates:
            title = lines[i + 1] if i + 1 < len(lines) else ""
            speaker = lines[i + 2] if i + 2 < len(lines) else ""

            if title:
                item = _make_item("FRB", dt, speaker, title, FRB_SPEECHES_URL)
                if _title_is_market_relevant(title, speaker, "FRB"):
                    items.append(item)
            i += 3
            continue
        i += 1

    return items

def _parse_boj_items(html: str, target_dates):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)
    lines = [_normalize_text(x) for x in text.splitlines() if _normalize_text(x)]

    items = []
    i = 0
    while i < len(lines):
        line = lines[i]
        dt = _parse_date_any(line)
        if dt and dt in target_dates:
            speaker = lines[i + 1] if i + 1 < len(lines) else ""
            title = lines[i + 2] if i + 2 < len(lines) else ""

            if title:
                item = _make_item("BOJ", dt, speaker, title, BOJ_PRESS_URL)
                if _title_is_market_relevant(title, speaker, "BOJ"):
                    items.append(item)
            i += 3
            continue
        i += 1

    return items

def _parse_boj_speeches_2026(html: str, target_dates):
    """
    BOJの 2026 speeches 英文一覧からも補助取得
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)
    lines = [_normalize_text(x) for x in text.splitlines() if _normalize_text(x)]

    items = []
    i = 0
    while i < len(lines):
        line = lines[i]
        dt = _parse_date_any(line)
        if dt and dt in target_dates:
            speaker = lines[i + 1] if i + 1 < len(lines) else ""
            title = lines[i + 2] if i + 2 < len(lines) else ""
            if title:
                item = _make_item("BOJ", dt, speaker, title, BOJ_SPEECHES_2026_URL)
                if _title_is_market_relevant(title, speaker, "BOJ"):
                    items.append(item)
            i += 3
            continue
        i += 1

    return items

def _source_priority(source: str) -> int:
    if source == "FRB":
        return 0
    if source == "BOJ":
        return 1
    if source == "NEWS":
        return 2
    return 9

def fetch_policy_news(now_dt=None):
    """
    直近3日(JST)の FRB / BOJ 発言のうち
    “市場に効くものだけ” を抽出して返す
    """
    if now_dt is None:
        now_dt = datetime.now(JST)

    now = now_dt.astimezone(JST)

    target_dates = {
        now.date() - timedelta(days=1),
        now.date() - timedelta(days=2),
        now.date() - timedelta(days=3),
    }

    results = []

    # FRB
    try:
        frb_html = _fetch_html(FRB_SPEECHES_URL)
        results.extend(_parse_frb_items(frb_html, target_dates))
    except Exception as e:
        print("[WARN] FRB policy news fetch failed:", e)

    # BOJ press
    try:
        boj_html = _fetch_html(BOJ_PRESS_URL)
        results.extend(_parse_boj_items(boj_html, target_dates))
    except Exception as e:
        print("[WARN] BOJ press fetch failed:", e)

    # BOJ speeches 2026
    try:
        boj_speech_html = _fetch_html(BOJ_SPEECHES_2026_URL)
        results.extend(_parse_boj_speeches_2026(boj_speech_html, target_dates))
    except Exception as e:
        print("[WARN] BOJ speeches 2026 fetch failed:", e)

    # 重複排除
    dedup = {}
    for x in results:
        key = (
            x.get("source"),
            x.get("date_jst"),
            x.get("speaker"),
            x.get("title"),
        )
        dedup[key] = x

    results = list(dedup.values())

    # FRB優先 → 影響度高い順 → CPI連動優先 → 新しい日付順
    results.sort(
        key=lambda x: (
            _source_priority(x.get("source", "")),
            -int(x.get("market_impact_score", 1)),
            0 if x.get("is_cpi_linked") else 1,
            x.get("date_jst", ""),
            x.get("speaker", ""),
            x.get("title", ""),
        ),
        reverse=False,
    )

    print("[INFO] policy news count =", len(results))
    if results:
        print("[DEBUG] first policy news =", results[0])

    return results
