from config.settings import MAJOR_RELEASE_KEYWORDS, US_RELEASE_SERIES_MAP
from data.fred_api import fetch_fred_latest_result


def importance_to_stars(label):
    if label == "高":
        return 3
    if label == "中":
        return 2
    return 1


def is_major_release(release_name):
    s = str(release_name)
    return any(k.lower() in s.lower() for k in MAJOR_RELEASE_KEYWORDS)


def infer_importance_label(release_name):
    s = str(release_name).lower()

    if any(
        k.lower() in s
        for k in [
            "Consumer Price Index",
            "Gross Domestic Product",
            "Employment Situation",
            "Producer Price Index",
            "Personal Income and Outlays",
        ]
    ):
        return "高"

    if any(
        k.lower() in s
        for k in [
            "Retail Sales",
            "Industrial Production",
            "Job Openings and Labor Turnover",
            "Employment Cost Index",
            "Housing Starts",
            "Initial Claims",
        ]
    ):
        return "中"

    return "低"


def infer_importance_label_from_stars(stars):
    if stars >= 3:
        return "高"
    if stars >= 2:
        return "中"
    return "低"


def classify_country_from_name(name):
    """
    Excel上は日米混在している前提。
    最低限のキーワードで国を補完する。
    """
    if not name:
        return "US"

    s = str(name).lower()

    jp_keywords = [
        "日銀", "日本", "機械受注", "景気動向", "実質賃金", "家計調査",
        "鉱工業生産", "消費者物価", "企業物価", "毎月勤労統計",
    ]
    us_keywords = [
        "consumer price index",
        "gross domestic product",
        "employment situation",
        "producer price index",
        "retail sales",
        "industrial production",
        "personal income",
        "unemployment",
        "job openings",
        "initial claims",
        "fomc",
        "fed",
    ]

    if any(k in s for k in [x.lower() for x in jp_keywords]):
        return "JP"
    if any(k in s for k in us_keywords):
        return "US"

    return "US"


def build_event_result_text(actual, forecast, previous, note=None):
    parts = []

    if actual:
        parts.append(f"結果: {actual}")
    if forecast:
        parts.append(f"予想: {forecast}")
    if previous:
        parts.append(f"前回: {previous}")
    if note:
        parts.append(str(note))

    return " / ".join(parts) if parts else None


def calc_fred_event_impact_score(release_name, event_dt, status):
    """
    既存 main.py の全文が見えていないため、ここは安全な提案実装。
    必要に応じて既存のスコア式へ差し替えてください。
    """
    importance = infer_importance_label(release_name)
    base = {"高": 8.0, "中": 5.5, "低": 3.0}.get(importance, 3.0)

    s = str(status or "").lower()

    if "recent" in s or "past" in s:
        return round(base, 1)
    if "upcoming" in s or "next" in s:
        return round(base - 0.5, 1)

    return round(base, 1)


def enrich_fred_events_with_results(events):
    """
    Excel由来イベントの result が空のときのみ、
    release名に紐づく FRED series_id があれば補完する。
    """
    enriched = []

    for e in events:
        x = dict(e)

        if x.get("result"):
            enriched.append(x)
            continue

        name = x.get("event_name") or x.get("release_name") or ""
        matched = None

        for release_name, meta in US_RELEASE_SERIES_MAP.items():
            if release_name.lower() in str(name).lower():
                matched = meta
                break

        if not matched:
            enriched.append(x)
            continue

        latest_value = fetch_fred_latest_result(matched["series_id"])
        if latest_value is not None:
            x["result"] = f'{matched["result_label"]}: {latest_value}'
            x["series_id"] = matched["series_id"]

        enriched.append(x)

    return enriched