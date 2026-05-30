import os
import csv
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
from datetime import datetime, timedelta, timezone

import requests
import yfinance as yf
from openai import OpenAI


# =========================================================
# 設定
# =========================================================
JST = timezone(timedelta(hours=9))

MARKET_SYMBOLS = {
    "日経平均": "^N225",
    "NYダウ": "^DJI",
    "NASDAQ": "^IXIC",
    "S&P500": "^GSPC",
    "VIX": "^VIX",
    "米10年金利": "^TNX",
    "GOLD (USD)": "GC=F",
    "BTC (USD)": "BTC-USD",
    "USD/JPY": "USDJPY=X",
}

SECTOR_ETFS = {
    "テクノロジー": "XLK",
    "金融": "XLF",
    "素材": "XLB",
    "ヘルスケア": "XLV",
    "公益": "XLU",
}

# FRED
FRED_BASE_URL = "https://api.stlouisfed.org/fred"
# 重要イベントとして注目する release 名（提案実装）
MAJOR_RELEASE_KEYWORDS = [
    "Consumer Price Index",
    "Gross Domestic Product",
    "Employment Situation",
    "Producer Price Index",
    "Retail Sales",
    "Industrial Production",
    "Personal Income and Outlays",
    "Advance Monthly Sales for Retail and Food Services",
    "Employment Cost Index",
    "Unemployment",
    "Job Openings and Labor Turnover",
    "Housing Starts",
    "New Residential Sales",
    "Existing Home Sales",
    "Initial Claims",
    "Selected Interest Rates",
]

# CSV保存先
DAILY_LOG_FILE = "market_ai_daily_log.csv"
EVENT_LOG_FILE = "market_ai_event_log.csv"


# =========================================================
# 共通
# =========================================================
def now_jst():
    return datetime.now(JST)


def format_change(change):
    if change is None:
        return "N/A"
    sign = "+" if change > 0 else ""
    return f"{sign}{change:.2f}%"


def colorize_change(change_text):
    if change_text == "N/A":
        return '<span style="color:#666;">N/A</span>'
    if str(change_text).startswith("+"):
        return f'<span style="color:green;font-weight:bold;">{change_text}</span>'
    if str(change_text).startswith("-"):
        return f'<span style="color:red;font-weight:bold;">{change_text}</span>'
    return f'<span style="color:#333;">{change_text}</span>'


def safe_float(v):
    try:
        return float(v)
    except Exception:
        return None


# =========================================================
# 市場データ（Yahoo Finance）
# =========================================================
def download_ohlc(symbols, period="5d", interval="1d"):
    return yf.download(
        tickers=symbols,
        period=period,
        interval=interval,
        auto_adjust=False,
        progress=False,
        threads=False,
        group_by="ticker",
    )


def get_close_pair(df, symbol):
    try:
        sub = df[symbol].copy()
        closes = sub["Close"].dropna()
        if len(closes) < 2:
            return None, None
        return float(closes.iloc[-1]), float(closes.iloc[-2])
    except Exception:
        return None, None


def calc_change_pct(curr, prev):
    if curr is None or prev is None or prev == 0:
        return None
    return round((curr - prev) / prev * 100, 2)


def build_rows(df, symbol_map):
    rows = []
    for label, symbol in symbol_map.items():
        curr, prev = get_close_pair(df, symbol)
        change = calc_change_pct(curr, prev)

        if curr is None:
            rows.append({
                "label": label,
                "value": "N/A",
                "change_pct": None,
                "change_text": "N/A",
            })
            continue

        rows.append({
            "label": label,
            "value": f"{curr:.2f}",
            "change_pct": change,
            "change_text": format_change(change),
        })

    return rows


def summarize_sector_attention(sector_rows):
    valid = [r for r in sector_rows if r["change_pct"] is not None]
    if not valid:
        return {"leaders": [], "laggards": []}

    leaders = sorted(valid, key=lambda x: x["change_pct"], reverse=True)[:3]
    laggards = sorted(valid, key=lambda x: x["change_pct"])[:2]
    return {"leaders": leaders, "laggards": laggards}


# =========================================================
# FRED 経済カレンダー（release datesベース）
# =========================================================
def fred_get(path, params=None):
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        raise ValueError("FRED_API_KEY が未設定です。")

    if params is None:
        params = {}

    params = dict(params)
    params["api_key"] = api_key
    params["file_type"] = "json"

    url = f"{FRED_BASE_URL}/{path}"
    res = requests.get(url, params=params, timeout=30)
    res.raise_for_status()
    return res.json()


def fetch_fred_release_dates():
    """
    FRED の fred/releases/dates を取得し、注目release名で絞る提案実装。
    """
    try:
        data = fred_get(
            "releases/dates",
            {
                "sort_order": "asc",
                "limit": 1000,
            }
        )
    except Exception as e:
        return [], f"FRED releases/dates 取得エラー: {e}"

    raw_dates = data.get("release_dates", [])
    events = []

    for item in raw_dates:
        release_name = item.get("release_name", "")
        release_id = item.get("release_id", "")
        date_str = item.get("date", "")

        # 重要リリース名だけ通す（提案実装）
        if not is_major_release(release_name):
            continue

        event_dt = parse_date_only(date_str)
        if event_dt is None:
            continue

        status = "upcoming" if event_dt.date() >= now_jst().date() else "recent"
        impact_score = calc_fred_event_impact_score(release_name, event_dt, status)

        events.append({
            "release_id": release_id,
            "name": release_name,
            "event_dt": event_dt,
            "event_dt_text": event_dt.strftime("%Y-%m-%d"),
            "status": status,
            "importance_label": infer_importance_label(release_name),
            "impact_score": impact_score,
            "country": "US",
        })

    # 直近2日〜先7日だけ使う
    today = now_jst().date()
    min_date = today - timedelta(days=2)
    max_date = today + timedelta(days=7)

    filtered = []
    for e in events:
        if min_date <= e["event_dt"].date() <= max_date:
            filtered.append(e)

    return filtered, None


def is_major_release(release_name):
    s = str(release_name)
    return any(k.lower() in s.lower() for k in MAJOR_RELEASE_KEYWORDS)


def parse_date_only(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=JST)
    except Exception:
        return None


def infer_importance_label(release_name):
    """
    release名ベースの提案実装
    """
    s = release_name.lower()
    if any(k.lower() in s for k in [
        "Consumer Price Index",
        "Gross Domestic Product",
        "Employment Situation",
        "Producer Price Index",
        "Personal Income and Outlays",
    ]):
        return "高"
    if any(k.lower() in s for k in [
        "Retail Sales",
        "Industrial Production",
        "Job Openings and Labor Turnover",
        "Employment Cost Index",
        "Housing Starts",
    ]):
        return "中"
    return "低"


def calc_fred_event_impact_score(release_name, event_dt, status):
    """
    FRED向けイベント影響度スコア（提案ロジック）
    - release_name で基礎点
    - 近い日付ほど加点
    """
    importance = infer_importance_label(release_name)
    base = {"高": 8.0, "中": 5.5, "低": 3.0}.get(importance, 3.0)

    days_diff = abs((event_dt.date() - now_jst().date()).days)

    if days_diff == 0:
        proximity_bonus = 2.0
    elif days_diff == 1:
        proximity_bonus = 1.2
    elif days_diff == 2:
        proximity_bonus = 0.7
    else:
        proximity_bonus = 0.2

    score = min(10.0, round(base + proximity_bonus, 2))
    return score


def split_fred_events(events):
    recent = []
    upcoming = []

    today = now_jst().date()

    for e in events:
        if e["event_dt"].date() >= today:
            upcoming.append(e)
        else:
            recent.append(e)

    recent = sorted(recent, key=lambda x: x["impact_score"], reverse=True)[:8]
    upcoming = sorted(upcoming, key=lambda x: x["impact_score"], reverse=True)[:8]

    return recent, upcoming


# =========================================================
# レジーム / 研究用シグナル
# =========================================================
def score_market(market_rows, sector_rows, recent_events, upcoming_events):
    score = 0
    reasons = []

    lookup = {r["label"]: r for r in market_rows}

    # 株価指数
    for key in ["日経平均", "NYダウ", "NASDAQ", "S&P500"]:
        item = lookup.get(key)
        if item and item["change_pct"] is not None:
            if item["change_pct"] > 0:
                score += 1
                reasons.append(f"{key}が上昇")
            elif item["change_pct"] < 0:
                score -= 1
                reasons.append(f"{key}が下落")

    # VIX
    vix = lookup.get("VIX")
    if vix and vix["change_pct"] is not None:
        if vix["change_pct"] < 0:
            score += 1
            reasons.append("VIXが低下")
        elif vix["change_pct"] > 0:
            score -= 1
            reasons.append("VIXが上昇")

    # 米10年金利
    tnx = lookup.get("米10年金利")
    if tnx and tnx["change_pct"] is not None:
        if tnx["change_pct"] < 0:
            score += 1
            reasons.append("米10年金利が低下")
        elif tnx["change_pct"] > 0:
            score -= 1
            reasons.append("米10年金利が上昇")

    # GOLD
    gold = lookup.get("GOLD (USD)")
    if gold and gold["change_pct"] is not None:
        if gold["change_pct"] < 0:
            score += 1
            reasons.append("GOLDが下落")
        elif gold["change_pct"] > 0:
            score -= 1
            reasons.append("GOLDが上昇")

    # BTC
    btc = lookup.get("BTC (USD)")
    if btc and btc["change_pct"] is not None:
        if btc["change_pct"] > 0:
            score += 1
            reasons.append("BTCが上昇")
        elif btc["change_pct"] < 0:
            score -= 1
            reasons.append("BTCが下落")

    # USD/JPY
    usdjpy = lookup.get("USD/JPY")
    if usdjpy and usdjpy["change_pct"] is not None:
        if usdjpy["change_pct"] > 0:
            score += 1
            reasons.append("USD/JPYが上昇")
        elif usdjpy["change_pct"] < 0:
            score -= 1
            reasons.append("USD/JPYが低下")

    # セクター
    sector_attention = summarize_sector_attention(sector_rows)
    if sector_attention["leaders"]:
        reasons.append(
            "上位セクター: " + "、".join(
                [f"{x['label']}({x['change_text']})" for x in sector_attention["leaders"]]
            )
        )
    if sector_attention["laggards"]:
        reasons.append(
            "下位セクター: " + "、".join(
                [f"{x['label']}({x['change_text']})" for x in sector_attention["laggards"]]
            )
        )

    # FREDイベントは「予定リスク」として反映（提案実装）
    risky_upcoming = [e for e in upcoming_events if e["impact_score"] >= 8.5]
    if len(risky_upcoming) >= 2:
        score -= 1
        reasons.append("高影響度の予定イベントが複数控えている")
    elif len(risky_upcoming) == 1:
        reasons.append(f"高影響イベント候補: {risky_upcoming[0]['name']}")

    return score, reasons, sector_attention


def classify_regime(score):
    if score >= 5:
        return "強めのリスクオン"
    elif score >= 2:
        return "ややリスクオン"
    elif score >= -1:
        return "中立"
    elif score >= -4:
        return "ややリスクオフ"
    else:
        return "強めのリスクオフ"


def generate_research_signal(score, market_rows, sector_attention, recent_events, upcoming_events):
    lookup = {r["label"]: r for r in market_rows}
    nasdaq = lookup.get("NASDAQ", {})
    dow = lookup.get("NYダウ", {})
    vix = lookup.get("VIX", {})
    tnx = lookup.get("米10年金利", {})

    signal = "観察継続"
    details = []

    if score >= 5:
        signal = "研究用シグナル: Growth優位"
        details.append("指数・ボラ・金利の並びが相対的に強気寄り")
    elif score >= 2:
        signal = "研究用シグナル: やや強気"
        details.append("地合いは改善傾向だが一方向までは未確認")
    elif score >= -1:
        signal = "研究用シグナル: 様子見"
        details.append("方向感が弱く、優位性は限定的")
    elif score >= -4:
        signal = "研究用シグナル: Defensive優位"
        details.append("防御的な解釈が優位になりやすい局面")
    else:
        signal = "研究用シグナル: リスク縮小優位"
        details.append("指数・ボラ・安全資産の並びが警戒寄り")

    if vix.get("change_pct") is not None and vix["change_pct"] > 0:
        details.append("VIX上昇は短期ボラ拡大のサイン")
    if tnx.get("change_pct") is not None and tnx["change_pct"] > 0:
        details.append("米10年金利上昇は株式バリュエーション逆風になりやすい")

    if nasdaq.get("change_pct") is not None and dow.get("change_pct") is not None:
        if nasdaq["change_pct"] > dow["change_pct"]:
            details.append("NASDAQ優位でグロース色がやや強い")
        elif dow["change_pct"] > nasdaq["change_pct"]:
            details.append("NYダウ優位で大型バリュー色がやや強い")

    if sector_attention["leaders"]:
        details.append("主導セクター: " + "、".join([x["label"] for x in sector_attention["leaders"]]))

    if recent_events:
        details.append(f"直近リリース候補: {recent_events[0]['name']} (影響度 {recent_events[0]['impact_score']})")
    if upcoming_events:
        details.append(f"次の高影響イベント候補: {upcoming_events[0]['name']} (影響度 {upcoming_events[0]['impact_score']})")

    return signal, details


# =========================================================
# AI要約
# =========================================================
def generate_ai_summary(market_rows, sector_rows, recent_events, upcoming_events, score, regime, signal, signal_details, reasons):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return "OPENAI_API_KEY が未設定のため、AI概況は生成していません。"

    client = OpenAI(api_key=api_key)

    market_lines = [f"{r['label']}: 値={r['value']} / 前日比={r['change_text']}" for r in market_rows]
    sector_lines = [f"{r['label']}: 値={r['value']} / 前日比={r['change_text']}" for r in sector_rows]
    recent_lines = [f"{e['event_dt_text']} / {e['name']} / 影響度={e['impact_score']}" for e in recent_events[:5]]
    upcoming_lines = [f"{e['event_dt_text']} / {e['name']} / 重要度={e['importance_label']} / 影響度={e['impact_score']}" for e in upcoming_events[:5]]

    prompt = f"""
あなたは日本語で金融市場サマリーを書くアナリストです。
以下のデータをもとに、自然な日本語で概況を書いてください。

条件:
- 箇条書きは使わない
- 500〜800文字程度
- 日経平均、NYダウ、NASDAQ、S&P500に触れる
- VIX、米10年金利、GOLD、BTC、USD/JPYに触れる
- セクターの強弱に触れる
- FREDベースの直近 / 今後の重要イベント候補にも触れる
- 最後に研究用シグナルの意味を短く書く
- 断定しすぎず、市場コメントとして自然に書く

【市場データ】
{chr(10).join(market_lines)}

【セクターETF】
{chr(10).join(sector_lines)}

【直近リリース候補】
{chr(10).join(recent_lines) if recent_lines else "なし"}

【今後の主要リリース候補】
{chr(10).join(upcoming_lines) if upcoming_lines else "なし"}

【総合スコア】
スコア: {score}
レジーム: {regime}

【研究用シグナル】
{signal}
{"; ".join(signal_details)}

【補足理由】
{"; ".join(reasons)}
"""
    try:
        res = client.responses.create(model="gpt-4o-mini", input=prompt)
        text = res.output[0].content[0].text.strip()
        return text.replace("。", "。<br><br>")
    except Exception as e:
        return f"AI概況の生成中にエラーが発生しました: {e}"


# =========================================================
# CSVログ保存
# =========================================================
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


def save_daily_log(market_rows, sector_rows, recent_events, upcoming_events, score, regime, signal, reasons):
    market_lookup = {r["label"]: r for r in market_rows}
    sector_attention = summarize_sector_attention(sector_rows)

    fieldnames = [
        "run_timestamp_jst",
        "score",
        "regime",
        "signal",
        "nikkei_change_pct",
        "dow_change_pct",
        "nasdaq_change_pct",
        "sp500_change_pct",
        "vix_change_pct",
        "tnx_change_pct",
        "gold_change_pct",
        "btc_change_pct",
        "usdjpy_change_pct",
        "top_sector_1",
        "top_sector_2",
        "top_sector_3",
        "laggard_sector_1",
        "laggard_sector_2",
        "top_recent_event",
        "top_recent_event_impact",
        "top_upcoming_event",
        "top_upcoming_event_impact",
        "reason_1",
        "reason_2",
        "reason_3",
        "reason_4",
        "reason_5",
    ]

    leaders = sector_attention["leaders"][:3]
    laggards = sector_attention["laggards"][:2]
    top_recent = recent_events[0] if recent_events else None
    top_upcoming = upcoming_events[0] if upcoming_events else None

    row = {
        "run_timestamp_jst": now_jst().strftime("%Y-%m-%d %H:%M:%S"),
        "score": score,
        "regime": regime,
        "signal": signal,
        "nikkei_change_pct": market_lookup.get("日経平均", {}).get("change_pct"),
        "dow_change_pct": market_lookup.get("NYダウ", {}).get("change_pct"),
        "nasdaq_change_pct": market_lookup.get("NASDAQ", {}).get("change_pct"),
        "sp500_change_pct": market_lookup.get("S&P500", {}).get("change_pct"),
        "vix_change_pct": market_lookup.get("VIX", {}).get("change_pct"),
        "tnx_change_pct": market_lookup.get("米10年金利", {}).get("change_pct"),
        "gold_change_pct": market_lookup.get("GOLD (USD)", {}).get("change_pct"),
        "btc_change_pct": market_lookup.get("BTC (USD)", {}).get("change_pct"),
        "usdjpy_change_pct": market_lookup.get("USD/JPY", {}).get("change_pct"),
        "top_sector_1": leaders[0]["label"] if len(leaders) > 0 else "",
        "top_sector_2": leaders[1]["label"] if len(leaders) > 1 else "",
        "top_sector_3": leaders[2]["label"] if len(leaders) > 2 else "",
        "laggard_sector_1": laggards[0]["label"] if len(laggards) > 0 else "",
        "laggard_sector_2": laggards[1]["label"] if len(laggards) > 1 else "",
        "top_recent_event": top_recent["name"] if top_recent else "",
        "top_recent_event_impact": top_recent["impact_score"] if top_recent else "",
        "top_upcoming_event": top_upcoming["name"] if top_upcoming else "",
        "top_upcoming_event_impact": top_upcoming["impact_score"] if top_upcoming else "",
        "reason_1": reasons[0] if len(reasons) > 0 else "",
        "reason_2": reasons[1] if len(reasons) > 1 else "",
        "reason_3": reasons[2] if len(reasons) > 2 else "",
        "reason_4": reasons[3] if len(reasons) > 3 else "",
        "reason_5": reasons[4] if len(reasons) > 4 else "",
    }

    append_csv_row(DAILY_LOG_FILE, fieldnames, row)


def save_event_log(recent_events, upcoming_events):
    fieldnames = [
        "run_timestamp_jst",
        "bucket",
        "event_date_jst",
        "country",
        "event_name",
        "importance_label",
        "impact_score",
        "release_id",
    ]

    run_ts = now_jst().strftime("%Y-%m-%d %H:%M:%S")

    for bucket_name, events in [("recent", recent_events), ("upcoming", upcoming_events)]:
        for e in events:
            row = {
                "run_timestamp_jst": run_ts,
                "bucket": bucket_name,
                "event_date_jst": e["event_dt_text"],
                "country": e["country"],
                "event_name": e["name"],
                "importance_label": e["importance_label"],
                "impact_score": e["impact_score"],
                "release_id": e["release_id"],
            }
            append_csv_row(EVENT_LOG_FILE, fieldnames, row)


# =========================================================
# HTML
# =========================================================
def regime_badge(regime):
    if regime == "強めのリスクオン":
        bg = "#dff6dd"
        border = "#2e7d32"
    elif regime == "ややリスクオン":
        bg = "#eef8e8"
        border = "#558b2f"
    elif regime == "中立":
        bg = "#f5f5f5"
        border = "#757575"
    elif regime == "ややリスクオフ":
        bg = "#fff3e0"
        border = "#ef6c00"
    else:
        bg = "#fdecea"
        border = "#c62828"

    return f"""
    <div style="
        background:{bg};
        border-left:6px solid {border};
        padding:12px 14px;
        margin:14px 0 18px 0;
        max-width:820px;
    ">
        <div style="font-weight:bold;">📈 市場レジーム</div>
        <div><b>{regime}</b></div>
    </div>
    """


def signal_badge(signal, details):
    detail_html = "・" + "<br>・".join(details) if details else "・特記事項なし"
    return f"""
    <div style="
        background:#eef3ff;
        border-left:6px solid #3f51b5;
        padding:12px 14px;
        margin:14px 0 18px 0;
        max-width:820px;
    ">
        <div style="font-weight:bold;">🤖 研究用トレードシグナル</div>
        <div style="margin:6px 0 8px 0;"><b>{signal}</b></div>
        <div>{detail_html}</div>
        <div style="margin-top:8px;color:#666;font-size:12px;">
            ※ 研究・観察用のシグナルであり、自動売買や投資助言ではありません。
        </div>
    </div>
    """


def build_market_table(rows):
    html_rows = []
    for r in rows:
        html_rows.append(f"""
        <tr>
            <td style="padding:8px 10px;border-bottom:1px solid #ddd;">{r['label']}</td>
            <td style="padding:8px 10px;border-bottom:1px solid #ddd;text-align:right;">{r['value']}</td>
            <td style="padding:8px 10px;border-bottom:1px solid #ddd;text-align:right;">{colorize_change(r['change_text'])}</td>
        </tr>
        """)

    return f"""
    <table style="border-collapse:collapse;width:100%;max-width:880px;font-size:14px;">
        <tr style="background:#f4f6f8;">
            <th style="padding:10px;text-align:left;border-bottom:2px solid #ccc;">項目</th>
            <th style="padding:10px;text-align:right;border-bottom:2px solid #ccc;">値</th>
            <th style="padding:10px;text-align:right;border-bottom:2px solid #ccc;">前日比</th>
        </tr>
        {''.join(html_rows)}
    </table>
    """


def build_fred_event_table(events, title):
    if not events:
        return f"<h3>{title}</h3><p>該当なし</p>"

    rows = []
    for e in events:
        rows.append(f"""
        <tr>
            <td style="padding:8px 10px;border-bottom:1px solid #ddd;">{e['event_dt_text']}</td>
            <td style="padding:8px 10px;border-bottom:1px solid #ddd;">{e['country']}</td>
            <td style="padding:8px 10px;border-bottom:1px solid #ddd;">{e['name']}</td>
            <td style="padding:8px 10px;border-bottom:1px solid #ddd;text-align:center;">{e['importance_label']}</td>
            <td style="padding:8px 10px;border-bottom:1px solid #ddd;text-align:right;"><b>{e['impact_score']}</b></td>
        </tr>
        """)

    return f"""
    <h3 style="margin-top:16px;margin-bottom:8px;">{title}</h3>
    <table style="border-collapse:collapse;width:100%;max-width:980px;font-size:13px;">
        <tr style="background:#f4f6f8;">
            <th style="padding:10px;text-align:left;border-bottom:2px solid #ccc;">日付</th>
            <th style="padding:10px;text-align:left;border-bottom:2px solid #ccc;">国</th>
            <th style="padding:10px;text-align:left;border-bottom:2px solid #ccc;">リリース</th>
            <th style="padding:10px;text-align:center;border-bottom:2px solid #ccc;">重要度</th>
            <th style="padding:10px;text-align:right;border-bottom:2px solid #ccc;">影響度</th>
        </tr>
        {''.join(rows)}
    </table>
    """


def build_html(market_rows, sector_rows, recent_events, upcoming_events, score, regime, signal, signal_details, reasons, ai_summary):
    today = now_jst().strftime("%Y-%m-%d")
    sector_attention = summarize_sector_attention(sector_rows)

    leaders_html = "・" + "<br>・".join([f"{x['label']} {x['change_text']}" for x in sector_attention["leaders"]]) if sector_attention["leaders"] else "・データなし"
    laggards_html = "・" + "<br>・".join([f"{x['label']} {x['change_text']}" for x in sector_attention["laggards"]]) if sector_attention["laggards"] else "・データなし"
    reasons_html = "・" + "<br>・".join(reasons) if reasons else "・特記事項なし"

    return f"""
    <html>
    <body style="font-family:Arial, Helvetica, sans-serif; color:#222; line-height:1.7;">
        <h2 style="margin-bottom:8px;">🌏 市場サマリー</h2>
        <p>{today} 時点 / Yahoo Finance + FRED API</p>

        <h3 style="margin-top:18px;margin-bottom:8px;">📊 マーケット</h3>
        {build_market_table(market_rows)}

        {regime_badge(regime)}
        {signal_badge(signal, signal_details)}

        <h3 style="margin-top:24px;margin-bottom:8px;">🏭 セクター</h3>
        {build_market_table(sector_rows)}

        <h4 style="margin-top:16px;margin-bottom:6px;">📌 上位セクター</h4>
        <p>{leaders_html}</p>

        <h4 style="margin-top:16px;margin-bottom:6px;">📌 下位セクター</h4>
        <p>{laggards_html}</p>

        <h3 style="margin-top:24px;margin-bottom:8px;">🗓️ FREDベースの主要リリース候補</h3>
        {build_fred_event_table(recent_events, "直近の主要リリース候補")}
        {build_fred_event_table(upcoming_events, "今後の主要リリース候補")}

        <h3 style="margin-top:24px;margin-bottom:8px;">🔎 判定の根拠</h3>
        <p>{reasons_html}</p>

        <h3 style="margin-top:24px;margin-bottom:8px;">📝 AI概況</h3>
        <p>{ai_summary}</p>

        <h3 style="margin-top:24px;margin-bottom:8px;">💾 CSVログ保存</h3>
        <p>daily: {DAILY_LOG_FILE}<br>events: {EVENT_LOG_FILE}</p>

        <p style="margin-top:18px;color:#666;font-size:12px;">
            ※ FRED版では release dates ベースでイベントを扱っています。
        </p>
    </body>
    </html>
    """


# =========================================================
# メール送信
# =========================================================
def send_mail(subject, html):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    to_email = os.getenv("TO_EMAIL")

    msg = MIMEText(html, "html", "utf-8")
    msg["Subject"] = subject
    msg["From"] = formataddr(("Market AI", smtp_user))
    msg["To"] = to_email

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)


# =========================================================
# 実行
# =========================================================
def main():
    # 1) 市場
    market_df = download_ohlc(list(MARKET_SYMBOLS.values()))
    sector_df = download_ohlc(list(SECTOR_ETFS.values()))
    market_rows = build_rows(market_df, MARKET_SYMBOLS)
    sector_rows = build_rows(sector_df, SECTOR_ETFS)

    # 2) FRED release dates
    fred_events, fred_error = fetch_fred_release_dates()
    recent_events, upcoming_events = split_fred_events(fred_events)

    # 3) スコア
    score, reasons, sector_attention = score_market(
        market_rows=market_rows,
        sector_rows=sector_rows,
        recent_events=recent_events,
        upcoming_events=upcoming_events
    )
    regime = classify_regime(score)
    signal, signal_details = generate_research_signal(
        score=score,
        market_rows=market_rows,
        sector_attention=sector_attention,
        recent_events=recent_events,
        upcoming_events=upcoming_events
    )

    if fred_error:
        reasons.append(fred_error)

    # 4) AI要約
    ai_summary = generate_ai_summary(
        market_rows=market_rows,
        sector_rows=sector_rows,
        recent_events=recent_events,
        upcoming_events=upcoming_events,
        score=score,
        regime=regime,
        signal=signal,
        signal_details=signal_details,
        reasons=reasons
    )

    # 5) CSVログ
    save_daily_log(
        market_rows=market_rows,
        sector_rows=sector_rows,
        recent_events=recent_events,
        upcoming_events=upcoming_events,
        score=score,
        regime=regime,
        signal=signal,
        reasons=reasons
    )
    save_event_log(recent_events, upcoming_events)

    # 6) HTMLメール
    html = build_html(
        market_rows=market_rows,
        sector_rows=sector_rows,
        recent_events=recent_events,
        upcoming_events=upcoming_events,
        score=score,
        regime=regime,
        signal=signal,
        signal_details=signal_details,
        reasons=reasons,
        ai_summary=ai_summary
    )

    today = now_jst().strftime("%Y-%m-%d")
    subject = f"{today} 市場レジーム＋FRED主要リリース候補"
    send_mail(subject, html)

    print("Market report email sent successfully.")
    print(f"CSV saved: {DAILY_LOG_FILE}, {EVENT_LOG_FILE}")


if __name__ == "__main__":
    main()
