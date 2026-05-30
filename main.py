import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timezone, timedelta

import yfinance as yf
import pandas as pd


SYMBOLS = {
    "日経平均": "^N225",
    "NASDAQ": "^IXIC",
    "S&P500": "^GSPC",
    "VIX": "^VIX",
    "GOLD": "GC=F",
    "BTC": "BTC-USD",
    "USD/JPY": "USDJPY=X",
}


def get_market_data():
    tickers = list(SYMBOLS.values())

    # 5日分あれば、週末や祝日をまたいでも直近2営業日を取りやすい
    df = yf.download(
        tickers=tickers,
        period="5d",
        interval="1d",
        auto_adjust=False,
        progress=False,
        group_by="ticker",
        threads=False,
    )

    rows = []

    for label, symbol in SYMBOLS.items():
        try:
            s = df[symbol].dropna()
            if len(s) < 2:
                rows.append((label, "N/A", "N/A"))
                continue

            latest_close = float(s["Close"].iloc[-1])
            prev_close = float(s["Close"].iloc[-2])

            change_pct = round((latest_close - prev_close) / prev_close * 100, 2)
            sign = "+" if change_pct > 0 else ""
            change_text = f"{sign}{change_pct:.2f}%"

            rows.append((label, f"{latest_close:.2f}", change_text))
        except Exception:
            rows.append((label, "N/A", "N/A"))

    return rows


def colorize_change(change_text: str) -> str:
    if change_text == "N/A":
        return '<span style="color:#666;">N/A</span>'
    if change_text.startswith("+"):
        return f'<span style="color:green;font-weight:bold;">{change_text}</span>'
    if change_text.startswith("-"):
        return f'<span style="color:red;font-weight:bold;">{change_text}</span>'
    return f'<span style="color:#333;">{change_text}</span>'


def build_html(rows):
    table_rows = []
    for label, value, change in rows:
        table_rows.append(f"""
        <tr>
            <td style="padding:8px 10px;border-bottom:1px solid #ddd;">{label}</td>
            <td style="padding:8px 10px;border-bottom:1px solid #ddd;text-align:right;">{value}</td>
            <td style="padding:8px 10px;border-bottom:1px solid #ddd;text-align:right;">{colorize_change(change)}</td>
        </tr>
        """)

    # 日本時間の日付
    jst = timezone(timedelta(hours=9))
    today_jst = datetime.now(jst).strftime("%Y-%m-%d")

    html = f"""
    <html>
    <body style="font-family:Arial, Helvetica, sans-serif; color:#222; line-height:1.7;">
        <h2 style="margin-bottom:10px;">🌏 市場サマリー</h2>
        <p>{today_jst} 時点のYahoo Financeベースのサマリー</p>

        <table style="border-collapse:collapse;width:100%;max-width:760px;font-size:14px;">
            <tr style="background:#f4f6f8;">
                <th style="padding:10px;text-align:left;border-bottom:2px solid #ccc;">項目</th>
                <th style="padding:10px;text-align:right;border-bottom:2px solid #ccc;">値</th>
                <th style="padding:10px;text-align:right;border-bottom:2px solid #ccc;">前日比</th>
            </tr>
            {''.join(table_rows)}
        </table>

        <p style="margin-top:16px;color:#666;font-size:12px;">
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
    rows = get_market_data()
    html, today_jst = build_html(rows)
    subject = f"{today_jst} 市場サマリー（日経・NASDAQ・S&P500・VIX・GOLD・BTC）"
    send_mail(subject, html)
    print("done")


if __name__ == "__main__":
    main()
