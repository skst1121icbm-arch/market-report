import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timezone, timedelta

import yfinance as yf
import pandas as pd
from openai import OpenAI


SYMBOLS = {
    "日経平均": "^N225",
    "NASDAQ": "^IXIC",
    "S&P500": "^GSPC",
    "VIX": "^VIX",
    "GOLD (USD)": "GC=F",
    "BTC (USD)": "BTC-USD",
    "USD/JPY": "USDJPY=X",
}


def jst_now():
    jst = timezone(timedelta(hours=9))
    return datetime.now(jst)


def download_market_data():
    tickers = list(SYMBOLS.values())

    df = yf.download(
        tickers=tickers,
        period="5d",
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


def score_market(rows):
    """
    これは私の提案ロジックです（独自ヒューリスティック）。
    スコア:
      株上昇 → +1
      VIX低下 → +1
      GOLD低下 → +1
      BTC上昇 → +1
      USD/JPY上昇 → +1
    合計スコアでリスクオン/オフの目安を作る
    """
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

    # GOLD: 下がるほどリスクオン寄り（単純化した提案ロジック）
    gold = lookup.get("GOLD (USD)")
    if gold and gold["change_pct"] is not None:
        if gold["change_pct"] < 0:
            score += 1
            reasons.append("GOLDが下落")
        elif gold["change_pct"] > 0:
            score -= 1
            reasons.append("GOLDが上昇")

    # BTC: 上がるほどリスクオン寄り（提案ロジック）
    btc = lookup.get("BTC (USD)")
    if btc and btc["change_pct"] is not None:
        if btc["change_pct"] > 0:
            score += 1
            reasons.append("BTCが上昇")
        elif btc["change_pct"] < 0:
            score -= 1
            reasons.append("BTCが下落")

    # USD/JPY: 円安進行をリスクオン寄りの補助指標として使用（提案ロジック）
    usdjpy = lookup.get("USD/JPY")
    if usdjpy and usdjpy["change_pct"] is not None:
        if usdjpy["change_pct"] > 0:
            score += 1
            reasons.append("USD/JPYが上昇")
        elif usdjpy["change_pct"] < 0:
            score -= 1
            reasons.append("USD/JPYが低下")

    if score >= 3:
        stance = "強めのリスクオン"
    elif score >= 1:
        stance = "ややリスクオン"
    elif score == 0:
        stance = "中立"
    elif score <= -3:
        stance = "強めのリスクオフ"
    else:
        stance = "ややリスクオフ"

    return score, stance, reasons


def generate_ai_summary(rows, score, stance, reasons):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return "OPENAI_API_KEY が未設定のため、AI概況は生成していません。"

    client = OpenAI(api_key=api_key)

    lines = []
    for r in rows:
        lines.append(f"{r['label']}: 値={r['value']} / 前日比={r['change_text']}")

    reasons_text = "、".join(reasons) if reasons else "有意なシグナルは限定的"

    prompt = f"""
あなたは日本語で金融市場サマリーを書くアナリストです。
以下のデータをもとに、読みやすい日本語で概況を書いてください。

条件:
- 箇条書きは使わない
- 350〜550文字程度
- 市場全体の方向感を簡潔に説明
- VIX、GOLD、BTCの動きにも触れる
- 最後に本日の見方を短く入れる
- 断定しすぎず、市場コメントとして自然に書く

【市場データ】
{chr(10).join(lines)}

【独自スコア】
スコア: {score}
判定: {stance}
根拠: {reasons_text}
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


def colorize_change(change_text):
    if change_text == "N/A":
        return '<span style="color:#666;">N/A</span>'
    if change_text.startswith("+"):
        return f'<span style="color:green;font-weight:bold;">{change_text}</span>'
    if change_text.startswith("-"):
        return f'<span style="color:red;font-weight:bold;">{change_text}</span>'
    return f'<span style="color:#333;">{change_text}</span>'


def score_badge(score, stance):
    if score >= 3:
        color = "#dff6dd"
        border = "#2e7d32"
    elif score >= 1:
        color = "#eef8e8"
        border = "#558b2f"
    elif score == 0:
        color = "#f5f5f5"
        border = "#757575"
    elif score <= -3:
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
        <div style="font-weight:bold;">📈 独自スコア</div>
        <div>スコア: <b>{score}</b> / 判定: <b>{stance}</b></div>
    </div>
    """


def build_html(rows, score, stance, reasons, ai_summary):
    table_rows = []

    for r in rows:
        table_rows.append(f"""
        <tr>
            <td style="padding:8px 10px;border-bottom:1px solid #ddd;">{r['label']}</td>
            <td style="padding:8px 10px;border-bottom:1px solid #ddd;text-align:right;">{r['value']}</td>
            <td style="padding:8px 10px;border-bottom:1px solid #ddd;text-align:right;">{colorize_change(r['change_text'])}</td>
        </tr>
        """)

    reasons_html = "・" + "<br>・".join(reasons) if reasons else "・有意な変化は限定的"

    today_jst = jst_now().strftime("%Y-%m-%d")

    html = f"""
    <html>
    <body style="font-family:Arial, Helvetica, sans-serif; color:#222; line-height:1.7;">

        <h2 style="margin-bottom:8px;">🌏 市場サマリー</h2>
        <p>{today_jst} 時点 / Yahoo Financeベース</p>

        <table style="border-collapse:collapse;width:100%;max-width:760px;font-size:14px;">
            <tr style="background:#f4f6f8;">
                <th style="padding:10px;text-align:left;border-bottom:2px solid #ccc;">項目</th>
                <th style="padding:10px;text-align:right;border-bottom:2px solid #ccc;">値</th>
                <th style="padding:10px;text-align:right;border-bottom:2px solid #ccc;">前日比</th>
            </tr>
            {''.join(table_rows)}
        </table>

        {score_badge(score, stance)}

        <h2 style="margin-top:24px;margin-bottom:8px;">🔎 スコアの根拠</h2>
        <p>{reasons_html}</p>

        <h2 style="margin-top:24px;margin-bottom:8px;">📝 AI概況</h2>
        <p>{ai_summary}</p>

        <p style="margin-top:18px;color:#666;font-size:12px;">
            Data source: Yahoo Finance / yfinance
        </p>
    </body>
    </html>
    """
    return html, today_jst


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
    df = download_market_data()
    rows = build_market_rows(df)
    score, stance, reasons = score_market(rows)
    ai_summary = generate_ai_summary(rows, score, stance, reasons)
    html, today_jst = build_html(rows, score, stance, reasons, ai_summary)

    subject = f"{today_jst} 市場サマリー（日経・NASDAQ・S&P500・VIX・GOLD・BTC）"
    send_mail(subject, html)

    print("Market report email sent successfully.")


if __name__ == "__main__":
    main()
