from utils.datetime_utils import now_jst
from logic.market_calc import summarize_sector_attention


def build_market_table(rows):
    if not rows:
        return "<p>なし</p>"

    html = "<table border='1' cellpadding='5'>"
    html += "<tr><th>項目</th><th>変化</th></tr>"

    for r in rows:
        html += f"<tr><td>{r['label']}</td><td>{r.get('change_text', 'N/A')}</td></tr>"

    html += "</table>"
    return html


def build_html(
    market_rows,
    sector_rows,
    score,
    regime,
    signal,
    signal_details,
    reasons,
    ai_summary,
):
    today = now_jst().strftime("%Y-%m-%d")

    sector_attention = summarize_sector_attention(sector_rows)

    html = f"""
    <html>
    <body>
        <h2>📊 市場レポート ({today})</h2>

        <h3>■ AI概況</h3>
        <p>{ai_summary}</p>

        <h3>■ 市場</h3>
        {build_market_table(market_rows)}

        <h3>■ セクター</h3>
        {build_market_table(sector_rows)}

        <h3>■ レジーム</h3>
        <p>{regime}（Score: {score}）</p>

        <h3>■ トレンドシグナル</h3>
        <p>{signal}</p>
        <p>{" / ".join(signal_details)}</p>

        <h3>■ 理由</h3>
        <p>{" / ".join(reasons)}</p>
    </body>
    </html>
    """

    return html