from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import re
import requests
from bs4 import BeautifulSoup

JST = ZoneInfo("Asia/Tokyo")

FRB_SPEECHES_URL = "https://www.federalreserve.gov/newsevents/speeches-testimony.htm"
BOJ_SPEECHES_URL = "https://www.boj.or.jp/en/announcements/press/index.htm/"

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

FRB_POLICY_KEYWORDS = [
    "inflation",
    "price",
    "rates",
    "rate",
    "monetary policy",
    "policy",
    "economy",
    "economic",
    "labor",
    "employment",
    "financial conditions",
    "regulation",
    "yield",
]

BOJ_POLICY_KEYWORDS = [
    "monetary policy",
    "economic activity and prices",
    "prices",
    "inflation",
    "wages",
    "economy",
    "payment",
    "policy",
    "financial system",
]

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


def _parse_us_date(text: str):
    """
    例:
    6/6/2026
    June 3, 2026
    """
    s = _normalize_text(text)

    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        month, day, year = m.groups()
        return datetime(int(year), int(month), int(day), tzinfo=JST).date()

    m = re.search(r"([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})", s)
    if m:
        month_str, day, year = m.groups()
        month = MONTHS.get(month_str.lower())
        if month:
            return datetime(int(year), month, int(day), tzinfo=JST).date()

    return None


def _event_market_relevance(title: str, speaker: str, source_type: str) -> str:
    text = f"{_safe(title)} {_safe(speaker)}".lower()

    if any(k in text for k in ["cpi", "ppi", "inflation", "prices"]):
        return "インフレ・金利観測に関連"
    if any(k in text for k in ["rate", "monetary policy", "policy"]):
        return "政策金利・金融政策に関連"
    if any(k in text for k in ["employment", "labor", "jobless"]):
        return "雇用・景気見通しに関連"
    if any(k in text for k in ["yield", "financial conditions", "regulation"]):
        return "金利・金融環境に関連"

    if source_type == "FRB":
        return "米金融政策の文脈で注目"
    if source_type == "BOJ":
        return "日銀政策・円相場の文脈で注目"
    return "市場材料として要確認"


def _title_is_policy_relevant(title: str, source_type: str) -> bool:
    t = _safe(title).lower()
    keywords = FRB_POLICY_KEYWORDS if source_type == "FRB" else BOJ_POLICY_KEYWORDS
    return any(k in t for k in keywords)


def _summarize_title(title: str, source_type: str) -> str:
    """
    記事本文を要約するのではなく、タイトルからメール掲載向けの一言を返す。
    """
    t = _safe(title)

    if source_type == "FRB":
        if re.search(r"inflation|price", t, re.IGNORECASE):
            return "インフレ・物価動向への示唆がある可能性"
        if re.search(r"rate|policy|economy|economic", t, re.IGNORECASE):
            return "米金融政策または景気判断の材料"
        if re.search(r"labor|employment|jobless", t, re.IGNORECASE):
            return "雇用や景気減速/過熱の判断材料"
        return "FRB高官発言として市場が確認しやすい材料"

    if source_type == "BOJ":
        if re.search(r"prices|inflation", t, re.IGNORECASE):
            return "物価・賃金・金融政策の判断材料"
        if re.search(r"policy|economic activity", t, re.IGNORECASE):
            return "日銀の政策運営や景気認識の判断材料"
        return "日銀発言として円相場・金利の観点で確認しやすい材料"

    return "市場材料として確認"


def _parse_frb_items(html: str, target_date):
    """
    FRB speeches-testimony の一覧ページから前日分を抽出する素朴なパーサ。
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)
    lines = [_normalize_text(x) for x in text.splitlines() if _normalize_text(x)]

    items = []
    i = 0
    while i < len(lines):
        line = lines[i]
        dt = _parse_us_date(line)
        if dt == target_date:
            title = lines[i + 1] if i + 1 < len(lines) else ""
            speaker = lines[i + 2] if i + 2 < len(lines) else ""

            if title:
                items.append({
                    "source": "FRB",
                    "date_jst": dt.strftime("%Y-%m-%d"),
                    "speaker": speaker,
                    "title": title,
                    "summary": _summarize_title(title, "FRB"),
                    "market_relevance": _event_market_relevance(title, speaker, "FRB"),
                    "url": FRB_SPEECHES_URL,
                })
            i += 3
            continue
        i += 1

    # タイトルで市場関連だけ残す
    filtered = [x for x in items if _title_is_policy_relevant(x["title"], "FRB")]
    return filtered


def _parse_boj_items(html: str, target_date):
    """
    BOJ speeches/statements の一覧ページから前日分を抽出する素朴なパーサ。
    構造変化に備えてテキストベースで抽出。
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)
    lines = [_normalize_text(x) for x in text.splitlines() if _normalize_text(x)]

    items = []
    i = 0
    while i < len(lines):
        line = lines[i]
        dt = _parse_us_date(line)
        if dt == target_date:
            speaker = lines[i + 1] if i + 1 < len(lines) else ""
            title = lines[i + 2] if i + 2 < len(lines) else ""

            if title:
                items.append({
                    "source": "BOJ",
                    "date_jst": dt.strftime("%Y-%m-%d"),
                    "speaker": speaker,
                    "title": title,
                    "summary": _summarize_title(title, "BOJ"),
                    "market_relevance": _event_market_relevance(title, speaker, "BOJ"),
                    "url": BOJ_SPEECHES_URL,
                })
            i += 3
            continue
        i += 1

    filtered = [x for x in items if _title_is_policy_relevant(x["title"], "BOJ")]
    return filtered


def fetch_policy_news(now_dt=None):
    """
    メール掲載用:
    前日(JST)の FRB / BOJ 発言一覧を取得して返す。
    """
    if now_dt is None:
        now_dt = datetime.now(JST)
    now = now_dt.astimezone(JST)
    target_date = (now.date() - timedelta(days=1))

    results = []

    # FRB
    try:
        frb_html = _fetch_html(FRB_SPEECHES_URL)
        frb_items = _parse_frb_items(frb_html, target_date)
        results.extend(frb_items)
    except Exception as e:
        print("[WARN] FRB policy news fetch failed:", e)

    # BOJ
    try:
        boj_html = _fetch_html(BOJ_SPEECHES_URL)
        boj_items = _parse_boj_items(boj_html, target_date)
        results.extend(boj_items)
    except Exception as e:
        print("[WARN] BOJ policy news fetch failed:", e)

    # ソート
    results.sort(key=lambda x: (x.get("source", ""), x.get("speaker", ""), x.get("title", "")))

    print("[INFO] policy news count =", len(results))
    if results:
        print("[DEBUG] first policy news =", results[0])

    return results
