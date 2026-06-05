from utils.datetime_utils import now_jst


# =========================
# 改行変換（AI概況用）
# =========================
def nl2br(text):
    if not text:
        return ""
    return str(text).replace("\n", "<br>")


# =========================
# 市場テーブル
# =========================
def build_market_table(rows):
    if not rows:
        return "<p>なし</p>"

    html = "<table border='1' cellpadding='5' cellspacing='0' style='border-collapse: collapse;'>"
    html += "<tr><th>項目</th><th>変化</th></tr>"

    for r in rows:
        html += f"<tr><td>{r['label']}</td><td>{r.get('change_text', 'N/A')}</td></tr>"

    html += "</table>"
    return html


# =========================
# 経済指標テーブル
# =========================
def build_event_table(events, title):
    if not events:
        return f"<h4>{title}</h4><p>なし</p>"

    html = f"<h4>{title}</h4>"
    html += "<table border='1' cellpadding='5' cellspacing='0' style='border-collapse: collapse;'>"

    html += (
        "<tr>"
        "<th>時刻(JST)</th>"
        "<th>国</th>"
        "<th>指標名</th>"
        "<th>重要度</th>"
        "<th>予想</th>"
        "<th>結果</th>"
        "<th>前回</th>"
        "</tr>"
    )

    for e in events:
        dt = e.get("event_dt_jst")
        time_str = dt.strftime("%m/%d %H:%M") if dt else "-"

        if e.get("country") == "US":
            country = "米国"
        elif e.get("country") == "JP":
            country = "日本"
        else:
            country = e.get("country", "")

        forecast = e.get("forecast") if e.get("forecast") is not None else "-"
        actual = e.get("actual") if e.get("actual") is not None else "-"
        previous = e.get("previous") if e.get("previous") is not None else "-"

        html += (
            "<tr>"
            f"<td>{time_str}</td>"
            f"<td>{country}</td>"
            f"<td>{e.get('event_name', '')}</td>"
            f"<td>{e.get('importance_label', '')}</td>"
            f"<td>{forecast}</td>"
            f"<td>{actual}</td>"
            f"<td>{previous}</td>"
            "</tr>"
        )

    html += "</table>"
    return html


# =========================
# 経済指標セクション
# =========================
def build_macro_html(macro_payload):
    if macro_payload["mode"] == "monday":
        return (
            "<h3>■ 日本・米国の経済指標（今週予定）</h3>"
            + build_event_table(macro_payload["weekly_upcoming"], "今週の予定")
        )

    return (
        "<h3>■ 日本・米国の経済指標</h3>"
        + build_event_table(macro_payload["yesterday_events"], "昨日の結果（JST基準）")
        + build_event_table(macro_payload["today_events"], "今日の予定／結果（JST基準）")
    )


# =========================
# メインHTML
# =========================
def build_html(
    market_rows,
    sector_rows,
    score,
    regime,
    signal,
    signal_details,
    reasons,
    ai_summary,
    macro_payload,
):
    today = now_jst().strftime("%Y-%m-%d")

    html = f"""
    <html>
    <body>
        <h2>📊 市場レポート ({today})</h2>

        <h3>■ 市場</h3>
        {build_market_table(market_rows)}

        <h3>■ セクター</h3>
        {build_market_table(sector_rows)}

        {build_macro_html(macro_payload)}

        <h3>■ レジーム</h3>
        <p>{regime}（Score: {score}）</p>

        <h3>■ トレンドシグナル</h3>
        <p>{signal}</p>
        <p>{" / ".join(signal_details)}</p>

        <h3>■ 理由</h3>
        <p>{" / ".join(reasons)}</p>

        <h3>■ AI概況</h3>
        <div style="line-height: 1.9;">
            {nl2br(ai_summary)}
        </div>
    </body>
    </html>
    """

    return html
