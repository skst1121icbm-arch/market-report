import os
import re
import math
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone

import yfinance as yf
import pandas as pd
import investpy
from openai import OpenAI


# =========================================
# 設定
# =========================================
SYMBOLS = {
    "日経平均": "^N225",
    "NASDAQ": "^IXIC",
    "S&P500": "^GSPC",
    "VIX": "^VIX",
    "GOLD (USD)": "GC=F",
    "BTC (USD)": "BTC-USD",
    "USD/JPY": "USDJPY=X",
}

# 経済指標で特に見たい通貨（必要に応じて変更）
TARGET_CURRENCIES = {"USD", "JPY", "EUR"}

# JST
JST = timezone(timedelta(hours=9))


# =========================================
# 時刻
# =========================================
def now_jst():
    return datetime.now(JST)


# =========================================
# 数値変換
# 例:
# "220K" -> 220000
# "2.5%" -> 2.5
# "1.2M" -> 1200000
# "-12K" -> -12000
# "" / None -> None
# =========================================
def parse_numeric(value):
    if value is None:
        return None

    s = str(value).strip()
    if s == "" or s.lower() in {"nan", "none"}:
        return None

    # よくある不要文字を除去
    s = s.replace(",", "").replace(" ", "")

    # 単位
    multiplier = 1.0
    if s.endswith("%"):
        s = s[:-1]
        multiplier = 1.0
    elif s.endswith("K"):
        s = s[:-1]
        multiplier = 1_000.0
    elif s.endswith("M"):
        s = s[:-1]
        multiplier = 1_000_000.0
    elif s.endswith("B"):
        s = s[:-1]
        multiplier = 1_000_000_000.0
    elif s.endswith("T"):
        s = s[:-1]
        multiplier = 1_000_000_000_000.0

    try:
        return float(s) * multiplier
    except Exception:
        return None


# =========================================
# Yahoo Finance 市場データ取得
# =========================================
def download_market_data():
    tickers = list(SYMBOLS.values())

    df = yf.download(
        tickers=tickers,
        period="5d",          # 週末またぎ対策
        interval="1d",
        auto_adjust=False,
        progress=False,
        threads=False,
        group_by="ticker",
    )
    return df


def get_close_pair(df, symbol):
    """
    直近2営業日のCloseを返す
    """
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


def build_market_rows(df):
    rows = []

    for label, symbol in SYMBOLS.items():
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

        sign = "+" if change is not None and change > 0 else ""
        change_text = f"{sign}{change:.2f}%" if change is not None else "N/A"

        rows.append({
            "label": label,
            "value": f"{curr:.2f}",
            "change_pct": change,
            "change_text": change_text,
        })

    return rows


# =========================================
# Investing.com 由来の経済カレンダー取得（investpy）
# ドキュメント上、time_zone / importances / from_date / to_date
# を指定でき、actual / forecast / previous 等が取得可能
# =========================================
def get_recent_economic_events():
    """
    過去24時間の高重要度イベントを取得（JST基準）
    """
    now = now_jst()
    start_dt = now - timedelta(hours=24)

    from_date = start_dt.strftime("%d/%m/%Y")
    to_date = now.strftime("%d/%m/%Y")

    try:
        df = investpy.economic_calendar(
            time_zone="GMT +09:00",
            time_filter="time_only",
            importances=["high"],
            countries=None,
            categories=None,
            from_date=from_date,
            to_date=to_date,
        )
    except Exception as e:
        return [], f"経済カレンダー取得エラー: {e}"

    if df is None or len(df) == 0:
        return [], None

    # 返却列の存在を前提に安全に処理
    events = []

    for _, row in df.iterrows():
        try:
            zone = str(row.get("zone", "")).strip()
            event = str(row.get("event", "")).strip()
            time_str = str(row.get("time", "")).strip()
            date_str = str(row.get("date", "")).strip()
            actual = row.get("actual", None)
            forecast = row.get("forecast", None)
            previous = row.get("previous", None)
            importance = str(row.get("importance", "")).strip()

            # 通貨/国フィルタ（必要に応じて調整）
            # investpyの zone は "united states" のような国名になることがあります。
            # currency 列がある環境ではそちらを優先してもOK。
            currency = str(row.get("currency", "")).strip().upper()
            if currency and currency not in TARGET_CURRENCIES:
                continue

            # "All Day" などは時刻が明確でないため除外
            if not time_str or time_str.lower() == "all day":
                continue

            event_dt = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M").replace(tzinfo=JST)

            if not (start_dt <= event_dt <= now):
                continue

            # surprise
            actual_num = parse_numeric(actual)
            forecast_num = parse_numeric(forecast)
            surprise = None
            if actual_num is not None and forecast_num is not None:
                surprise = round(actual_num - forecast_num, 4)

            events.append({
                "datetime": event_dt,
                "date": date_str,
                "time": time_str,
                "zone": zone,
                "currency": currency,
                "importance": importance,
                "event": event,
                "actual": actual if actual not in [None, ""] else "N/A",
                "forecast": forecast if forecast not in [None, ""] else "N/A",
                "previous": previous if previous not in [None, ""] else "N/A",
                "surprise": surprise,
            })
        except Exception:
            continue

    events.sort(key=lambda x: x["datetime"])
    return events, None


# =========================================
# サプライズ判定
# これは提案ロジックです
# surprise > 0   → 上振れ
# surprise < 0   → 下振れ
# 数値が取れない → 判定保留
# =========================================
def classify_surprise(surprise):
    if surprise is None:
        return "判定保留"
    if surprise > 0:
        return "上振れ"
    elif surprise < 0:
        return "下振れ"
    else:
        return "一致"


def build_surprise_summary(events):
    """
    サプライズをイベント単位で集約
    """
    summaries = []

    for ev in events:
        surprise_label = classify_surprise(ev["surprise"])

        # 表示用 surprise
        if ev["surprise"] is None:
            surprise_text = "N/A"
        else:
            sign = "+" if ev["surprise"] > 0 else ""
            surprise_text = f"{sign}{ev['surprise']}"

        summaries.append({
            "time": ev["time"],
            "zone": ev["zone"],
            "currency": ev["currency"],
            "event": ev["event"],
            "actual": ev["actual"],
            "forecast": ev["forecast"],
            "previous": ev["previous"],
            "surprise_text": surprise_text,
            "surprise_label": surprise_label,
        })

    return summaries


# =========================================
# 総合スコア
# これは提案ロジックです
# 市場スコア + サプライズスコアを合算
# =========================================
def score_market(rows):
    score = 0
    reasons = []

    lookup = {r["label"]: r for r in rows}

    # 株式指数
    for key in ["日経平均", "NASDAQ", "S&P500"]:
        item = lookup.get(key)
        if item and item["change_pct"] is not None:
            if item["change_pct"] > 0:
                score += 1
                reasons.append(f"{key}が上昇")
            elif item["change_pct"] < 0:
                score -= 1
                reasons.append(f"{key}が下落")

    # VIX: 下がるほどリスクオン寄り
    vix = lookup.get("VIX")
    if vix and vix["change_pct"] is not None:
        if vix["change_pct"] < 0:
            score += 1
            reasons.append("VIXが低下")
        elif vix["change_pct"] > 0:
            score -= 1
            reasons.append("VIXが上昇")

    # GOLD: 下がるほどリスクオン寄り
    gold = lookup.get("GOLD (USD)")
    if gold and gold["change_pct"] is not None:
        if gold["change_pct"] < 0:
            score += 1
            reasons.append("GOLDが下落")
        elif gold["change_pct"] > 0:
            score -= 1
            reasons.append("GOLDが上昇")

    # BTC: 上がるほどリスクオン寄り
    btc = lookup.get("BTC (USD)")
    if btc and btc["change_pct"] is not None:
        if btc["change_pct"] > 0:
            score += 1
            reasons.append("BTCが上昇")
        elif btc["change_pct"] < 0:
            score -= 1
            reasons.append("BTCが下落")

    # USD/JPY: 円安進行を補助的にリスクオン寄りとして扱う
    usdjpy = lookup.get("USD/JPY")
    if usdjpy and usdjpy["change_pct"] is not None:
        if usdjpy["change_pct"] > 0:
            score += 1
            reasons.append("USD/JPYが上昇")
        elif usdjpy["change_pct"] < 0:
            score -= 1
            reasons.append("USD/JPYが低下")

    return score, reasons


def score_surprises(surprise_items):
    """
    サプライズの単純スコア化（提案ロジック）
    上振れ +1 / 下振れ -1 / 一致 0 / 判定保留 0
    """
    score = 0
    reasons = []

    for item in surprise_items:
        if item["surprise_label"] == "上振れ":
            score += 1
            reasons.append(f"{item['event']} が上振れ")
        elif item["surprise_label"] == "下振れ":
            score -= 1
            reasons.append(f"{item['event']} が下振れ")

    return score, reasons


def final_market_stance(total_score):
    if total_score >= 4:
        return "強めのリスクオン"
    elif total_score >= 1:
        return "ややリスクオン"
    elif total_score == 0:
        return "中立"
    elif total_score <= -4:
        return "強めのリスクオフ"
    else:
        return "ややリスクオフ"


# =========================================
# AI概況
# =========================================
def generate_ai_summary(rows, surprise_items, total_score, stance, market_reasons, surprise_reasons):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return "OPENAI_API_KEY が未設定のため、AI概況は生成していません。"

    client = OpenAI(api_key=api_key)

    market_lines = []
    for r in rows:
        market_lines.append(f"{r['label']}: 値={r['value']} / 前日比={r['change_text']}")

    if surprise_items:
        surprise_lines = []
        for s in surprise_items[:10]:
            surprise_lines.append(
                f"{s['time']} {s['event']} / 実績={s['actual']} / 予想={s['forecast']} / 前回={s['previous']} / 判定={s['surprise_label']}"
            )
        surprise_text = "\n".join(surprise_lines)
    else:
        surprise_text = "過去24時間で対象イベントなし"

    prompt = f"""
あなたは日本語で金融市場サマリーを書くアナリストです。
以下のデータをもとに、自然な日本語でマーケット概況を書いてください。

条件:
- 箇条書きは使わない
- 400〜650文字程度
- 市場の方向感を簡潔に説明
- VIX、GOLD、BTC、USD/JPYに触れる
- 過去24時間の重要経済指標とサプライズ判定も触れる
- 最後に本日の見方を短く入れる
- 断定しすぎず市場コメントとして自然に書く

【市場データ】
{chr(10).join(market_lines)}

【過去24時間の重要イベント】
{surprise_text}

【総合スコア】
スコア: {total_score}
判定: {stance}

【市場要因】
{", ".join(market_reasons) if market_reasons else "特記事項なし"}

【経済指標要因】
{", ".join(surprise_reasons) if surprise_reasons else "特記事項なし"}
"""

    try:
        res = client.responses.create(
            model="gpt-4o-mini",
            input=prompt
        )
        text = res.output[0].content[0].text.strip()
        text = text.replace("。", "。<br><br>")
        return text
    except Exception as e:
        return f"AI概況の生成中にエラーが発生しました: {e}"


# =========================================
# HTML
# =========================================
def colorize_change(change_text):
    if change_text == "N/A":
        return '<span style="color:#666;">N/A</span>'
    if str(change_text).startswith("+"):
        return f'<span style="color:green;font-weight:bold;">{change_text}</span>'
    if str(change_text).startswith("-"):
        return f'<span style="color:red;font-weight:bold;">{change_text}</span>'
    return f'<span style="color:#333;">{change_text}</span>'


def colorize_surprise(label, text):
    if label == "上振れ":
        return f'<span style="color:green;font-weight:bold;">{text}</span>'
    elif label == "下振れ":
        return f'<span style="color:red;font-weight:bold;">{text}</span>'
    elif label == "一致":
        return f'<span style="color:#333;">{text}</span>'
    return f'<span style="color:#666;">{text}</span>'


def score_badge(score, stance):
    if score >= 4:
        color = "#dff6dd"
        border = "#2e7d32"
    elif score >= 1:
        color = "#eef8e8"
        border = "#558b2f"
    elif score == 0:
        color = "#f5f5f5"
        border = "#757575"
    elif score <= -4:
        color = "#fdecea"
        border = "#c62828"
    else:
        color = "#fff3e0"
        border = "#ef6c00"

    return f"""
    <div style="
        background:{color};
        border-left:6px solid {border};
        padding:12px 14px;
        margin:14px 0 18px 0;
        max-width:760px;
    ">
        <div style="font-weight:bold;">📈 総合スコア</div>
        <div>スコア: <b>{score}</b> / 判定: <b>{stance}</b></div>
    </div>
    """


def build_html(rows, surprise_items, total_score, stance, market_reasons, surprise_reasons, ai_summary):
    # 市場テーブル
    market_rows = []
    for r in rows:
        market_rows.append(f"""
        <tr>
            <td style="padding:8px 10px;border-bottom:1px solid #ddd;">{r['label']}</td>
            <td style="padding:8px 10px;border-bottom:1px solid #ddd;text-align:right;">{r['value']}</td>
            <td style="padding:8px 10px;border-bottom:1px solid #ddd;text-align:right;">{colorize_change(r['change_text'])}</td>
        </tr>
        """)

    # 経済指標テーブル
    if surprise_items:
        event_rows = []
        for s in surprise_items[:12]:
            event_rows.append(f"""
            <tr>
                <td style="padding:8px 10px;border-bottom:1px solid #ddd;">{s['time']}</td>
                <td style="padding:8px 10px;border-bottom:1px solid #ddd;">{s['event']}</td>
                <td style="padding:8px 10px;border-bottom:1px solid #ddd;text-align:right;">{s['actual']}</td>
                <td style="padding:8px 10px;border-bottom:1px solid #ddd;text-align:right;">{s['forecast']}</td>
                <td style="padding:8px 10px;border-bottom:1px solid #ddd;text-align:right;">{s['previous']}</td>
                <td style="padding:8px 10px;border-bottom:1px solid #ddd;text-align:right;">{colorize_surprise(s['surprise_label'], s['surprise_label'])}</td>
            </tr>
            """)
        events_html = f"""
        <table style="border-collapse:collapse;width:100%;max-width:900px;font-size:13px;">
            <tr style="background:#f4f6f8;">
                <th style="padding:10px;text-align:left;border-bottom:2px solid #ccc;">時刻</th>
                <th style="padding:10px;text-align:left;border-bottom:2px solid #ccc;">イベント</th>
                <th style="padding:10px;text-align:right;border-bottom:2px solid #ccc;">実績</th>
                <th style="padding:10px;text-align:right;border-bottom:2px solid #ccc;">予想</th>
                <th style="padding:10px;text-align:right;border-bottom:2px solid #ccc;">前回</th>
                <th style="padding:10px;text-align:right;border-bottom:2px solid #ccc;">判定</th>
            </tr>
            {''.join(event_rows)}
        </table>
        """
    else:
        events_html = "<p>該当なし</p>"

    market_reason_html = "・" + "<br>・".join(market_reasons) if market_reasons else "・特記事項なし"
    surprise_reason_html = "・" + "<br>・".join(surprise_reasons) if surprise_reasons else "・特記事項なし"

    today = now_jst().strftime("%Y-%m-%d")

    html = f"""
    <html>
    <body style="font-family:Arial, Helvetica, sans-serif; color:#222; line-height:1.7;">

        <h2 style="margin-bottom:8px;">🌏 市場サマリー</h2>
        <p>{today} 時点 / Yahoo Finance + Investing.com由来データ（investpy経由）</p>

        <table style="border-collapse:collapse;width:100%;max-width:760px;font-size:14px;">
            <tr style="background:#f4f6f8;">
                <th style="padding:10px;text-align:left;border-bottom:2px solid #ccc;">項目</th>
                <th style="padding:10px;text-align:right;border-bottom:2px solid #ccc;">値</th>
                <th style="padding:10px;text-align:right;border-bottom:2px solid #ccc;">前日比</th>
            </tr>
            {''.join(market_rows)}
        </table>

        {score_badge(total_score, stance)}

        <h2 style="margin-top:24px;margin-bottom:8px;">📉 過去24時間の重要経済指標</h2>
        {events_html}

        <h2 style="margin-top:24px;margin-bottom:8px;">🔎 市場スコアの根拠</h2>
        <p>{market_reason_html}</p>

        <h2 style="margin-top:24px;margin-bottom:8px;">📊 サプライズ判定の根拠</h2>
        <p>{surprise_reason_html}</p>

        <h2 style="margin-top:24px;margin-bottom:8px;">📝 AI概況</h2>
        <p>{ai_summary}</p>

        <p style="margin-top:18px;color:#666;font-size:12px;">
            Market data: Yahoo Finance / yfinance<br>
            Economic calendar: Investing.com derived data via investpy
        </p>
    </body>
    </html>
    """
    return html, today


# =========================================
# メール送信
# =========================================
def send_mail(subject, html):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    to_email = os.getenv("TO_EMAIL")

    msg = MIMEText(html, "html", "utf-8")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to_email

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)


# =========================================
# メイン
# =========================================
def main():
    # 1. 市場データ
    market_df = download_market_data()
    market_rows = build_market_rows(market_df)

    # 2. 経済指標（過去24h）
    events, event_error = get_recent_economic_events()
    surprise_items = build_surprise_summary(events)

    # 3. スコア
    market_score, market_reasons = score_market(market_rows)
    surprise_score, surprise_reasons = score_surprises(surprise_items)
    total_score = market_score + surprise_score
    stance = final_market_stance(total_score)

    # 4. AI概況
    if event_error:
        surprise_reasons = surprise_reasons + [event_error]
    ai_summary = generate_ai_summary(
        rows=market_rows,
        surprise_items=surprise_items,
        total_score=total_score,
        stance=stance,
        market_reasons=market_reasons,
        surprise_reasons=surprise_reasons
    )

    # 5. HTML & メール
    html, today = build_html(
        rows=market_rows,
        surprise_items=surprise_items,
        total_score=total_score,
        stance=stance,
        market_reasons=market_reasons,
        surprise_reasons=surprise_reasons,
        ai_summary=ai_summary
    )

    subject = f"{today} 市場サマリー＋重要経済指標＋サプライズ判定"
    send_mail(subject, html)

    print("Market report email sent successfully.")


if __name__ == "__main__":
    main()
