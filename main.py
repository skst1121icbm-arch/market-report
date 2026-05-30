import os
import math
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone

import pandas as pd
import yfinance as yf
from openai import OpenAI

# =========================================================
# 設定
# =========================================================
SYMBOLS = {
    "日経平均": "^N225",
    "NYダウ": "^DJI",
    "NASDAQ": "^IXIC",
    "S&P500": "^GSPC",
    "VIX": "^VIX",
    "GOLD (USD)": "GC=F",
    "BTC (USD)": "BTC-USD",
    "USD/JPY": "USDJPY=X",
}

# 注目セクター（Yahoo Finance/State Streetの当日セクター騰落を見て、
# 表示しやすいように代表ETFで追う実装）
SECTOR_ETFS = {
    "テクノロジー": "XLK",
    "金融": "XLF",
    "素材": "XLB",
    "ヘルスケア": "XLV",
    "公益": "XLU",
}

JST = timezone(timedelta(hours=9))


def now_jst():
    return datetime.now(JST)


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


def build_sector_rows(df):
    rows = []
    for label, symbol in SECTOR_ETFS.items():
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


def summarize_sector_attention(sector_rows):
    valid = [r for r in sector_rows if r["change_pct"] is not None]
    if not valid:
        return {
            "leaders": [],
            "laggards": []
        }
    leaders = sorted(valid, key=lambda x: x["change_pct"], reverse=True)[:3]
    laggards = sorted(valid, key=lambda x: x["change_pct"])[:2]
    return {
        "leaders": leaders,
        "laggards": laggards,
    }


def score_market(rows, sector_rows=None):
    score = 0
    reasons = []
    lookup = {r["label"]: r for r in rows}

    for key in ["日経平均", "NYダウ", "NASDAQ", "S&P500"]:
        item = lookup.get(key)
        if item and item["change_pct"] is not None:
            if item["change_pct"] > 0:
                score += 1
                reasons.append(f"{key}が上昇")
            elif item["change_pct"] < 0:
                score -= 1
                reasons.append(f"{key}が下落")

    vix = lookup.get("VIX")
    if vix and vix["change_pct"] is not None:
        if vix["change_pct"] < 0:
            score += 1
            reasons.append("VIXが低下")
        elif vix["change_pct"] > 0:
            score -= 1
            reasons.append("VIXが上昇")

    gold = lookup.get("GOLD (USD)")
    if gold and gold["change_pct"] is not None:
        if gold["change_pct"] < 0:
            score += 1
            reasons.append("GOLDが下落")
        elif gold["change_pct"] > 0:
            score -= 1
            reasons.append("GOLDが上昇")

    btc = lookup.get("BTC (USD)")
    if btc and btc["change_pct"] is not None:
        if btc["change_pct"] > 0:
            score += 1
            reasons.append("BTCが上昇")
        elif btc["change_pct"] < 0:
            score -= 1
            reasons.append("BTCが下落")

    usdjpy = lookup.get("USD/JPY")
    if usdjpy and usdjpy["change_pct"] is not None:
        if usdjpy["change_pct"] > 0:
            score += 1
            reasons.append("USD/JPYが上昇")
        elif usdjpy["change_pct"] < 0:
            score -= 1
            reasons.append("USD/JPYが低下")

    if sector_rows:
        attention = summarize_sector_attention(sector_rows)
        if attention["leaders"]:
            reasons.append(
                "注目セクター上位: " + "、".join([f"{x['label']}({x['change_text']})" for x in attention["leaders"]])
            )

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


def generate_ai_summary(rows, sector_rows, total_score, stance, reasons):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return "OPENAI_API_KEY が未設定のため、AI概況は生成していません。"

    client = OpenAI(api_key=api_key)

    market_lines = []
    for r in rows:
        market_lines.append(f"{r['label']}: 値={r['value']} / 前日比={r['change_text']}")

    sector_lines = []
    for s in sector_rows:
        sector_lines.append(f"{s['label']}: 値={s['value']} / 前日比={s['change_text']}")

    prompt = f"""
あなたは日本語で金融市場サマリーを書くアナリストです。
以下のデータをもとに、自然な日本語でマーケット概況を書いてください。

条件:
- 箇条書きは使わない
- 400〜650文字程度
- 日経平均、NYダウ、NASDAQ、S&P500の動きに触れる
- VIX、GOLD、BTC、USD/JPYに触れる
- 注目セクターの動きに触れる
- 最後に本日の見方を短く入れる
- 断定しすぎず市場コメントとして自然に書く

【市場データ】
{chr(10).join(market_lines)}

【セクターETF】
{chr(10).join(sector_lines)}

【総合スコア】
スコア: {total_score}
判定: {stance}

【補足要因】
{", ".join(reasons) if reasons else "特記事項なし"}
"""
    try:
        res = client.responses.create(
            model="gpt-4o-mini",
            input=prompt,
        )
        text = res.output[0].content[0].text.strip()
        text = text.replace("。", "。<br><br>")
        return text
    except Exception as e:
        return f"AI概況の生成中にエラーが発生しました: {e}"


def colorize_change(change_text):
    if change_text == "N/A":
        return '<span style="color:#666;">N/A</span>'
    if str(change_text).startswith("+"):
        return f'<span style="color:green;font-weight:bold;">{change_text}</span>'
    if str(change_text).startswith("-"):
        return f'<span style="color:red;font-weight:bold;">{change_text}</span>'
    return f'<span style="color:#333;">{change_text}</span>'


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


def build_html(rows, sector_rows, sector_attention, total_score, stance, reasons, ai_summary):
    market_rows = []
    for r in rows:
        market_rows.append(f"""
        <tr>
            <td style="padding:8px 10px;border-bottom:1px solid #ddd;">{r['label']}</td>
            <td style="padding:8px 10px;border-bottom:1px solid #ddd;text-align:right;">{r['value']}</td>
            <td style="padding:8px 10px;border-bottom:1px solid #ddd;text-align:right;">{colorize_change(r['change_text'])}</td>
        </tr>
        """)

    sector_rows_html = []
    for s in sector_rows:
        sector_rows_html.append(f"""
        <tr>
            <td style="padding:8px 10px;border-bottom:1px solid #ddd;">{s['label']}</td>
            <td style="padding:8px 10px;border-bottom:1px solid #ddd;text-align:right;">{s['value']}</td>
            <td style="padding:8px 10px;border-bottom:1px solid #ddd;text-align:right;">{colorize_change(s['change_text'])}</td>
        </tr>
        """)

    if sector_attention["leaders"]:
        leaders_html = "・" + "<br>・".join([f"{x['label']} {x['change_text']}" for x in sector_attention["leaders"]])
    else:
        leaders_html = "・データなし"

    if sector_attention["laggards"]:
        laggards_html = "・" + "<br>・".join([f"{x['label']} {x['change_text']}" for x in sector_attention["laggards"]])
    else:
        laggards_html = "・データなし"

    reasons_html = "・" + "<br>・".join(reasons) if reasons else "・特記事項なし"

    today = now_jst().strftime("%Y-%m-%d")

    html = f"""
    <html>
    <body style="font-family:Arial, Helvetica, sans-serif; color:#222; line-height:1.7;">

        <h2 style="margin-bottom:8px;">🌏 市場サマリー</h2>
        <p>{today} 時点 / Yahoo Financeベース</p>

        <table style="border-collapse:collapse;width:100%;max-width:760px;font-size:14px;">
            <tr style="background:#f4f6f8;">
                <th style="padding:10px;text-align:left;border-bottom:2px solid #ccc;">項目</th>
                <th style="padding:10px;text-align:right;border-bottom:2px solid #ccc;">値</th>
                <th style="padding:10px;text-align:right;border-bottom:2px solid #ccc;">前日比</th>
            </tr>
            {''.join(market_rows)}
        </table>

        {score_badge(total_score, stance)}

        <h2 style="margin-top:24px;margin-bottom:8px;">🏭 注目セクター</h2>
        <table style="border-collapse:collapse;width:100%;max-width:760px;font-size:14px;">
            <tr style="background:#f4f6f8;">
                <th style="padding:10px;text-align:left;border-bottom:2px solid #ccc;">セクター</th>
                <th style="padding:10px;text-align:right;border-bottom:2px solid #ccc;">ETF価格</th>
                <th style="padding:10px;text-align:right;border-bottom:2px solid #ccc;">前日比</th>
            </tr>
            {''.join(sector_rows_html)}
        </table>

        <h3 style="margin-top:16px;margin-bottom:6px;">📌 上位セクター</h3>
        <p>{leaders_html}</p>

        <h3 style="margin-top:16px;margin-bottom:6px;">📌 下位セクター</h3>
        <p>{laggards_html}</p>

        <h2 style="margin-top:24px;margin-bottom:8px;">🔎 判定の根拠</h2>
        <p>{reasons_html}</p>

        <h2 style="margin-top:24px;margin-bottom:8px;">📝 AI概況</h2>
        <p>{ai_summary}</p>

        <p style="margin-top:18px;color:#666;font-size:12px;">
            Market data: Yahoo Finance / yfinance
        </p>
    </body>
    </html>
    """
    return html, today


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


def main():
    market_df = download_ohlc(list(SYMBOLS.values()))
    sector_df = download_ohlc(list(SECTOR_ETFS.values()))

    market_rows = build_market_rows(market_df)
    sector_rows = build_sector_rows(sector_df)
    sector_attention = summarize_sector_attention(sector_rows)

    total_score, reasons = score_market(market_rows, sector_rows)
    stance = final_market_stance(total_score)
    ai_summary = generate_ai_summary(market_rows, sector_rows, total_score, stance, reasons)

    html, today = build_html(
        rows=market_rows,
        sector_rows=sector_rows,
        sector_attention=sector_attention,
        total_score=total_score,
        stance=stance,
        reasons=reasons,
        ai_summary=ai_summary,
    )

    subject = f"{today} 市場サマリー＋NYダウ＋注目セクター"
    send_mail(subject, html)
    print("Market report email sent successfully.")


if __name__ == "__main__":
    main()
