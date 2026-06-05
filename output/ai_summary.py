import os
from openai import OpenAI


def _event_to_text(e):
    name = str(e.get("event_name") or "")

    country = e.get("country")
    if country == "US":
        country_name = "米国"
    elif country == "JP":
        country_name = "日本"
    else:
        country_name = str(country or "")

    status = e.get("event_status") or ""

    forecast = e.get("forecast")
    actual = e.get("actual")
    previous = e.get("previous")

    parts = [f"[{country_name}][{status}] {name}"]

    if actual is not None:
        parts.append(f"結果={actual}")
    if forecast is not None:
        parts.append(f"予想={forecast}")
    if previous is not None:
        parts.append(f"前回={previous}")

    return " / ".join(parts)


def generate_ai_summary(
    market_rows,
    sector_rows,
    recent_events,
    upcoming_events,
    score,
    regime,
    signal,
    signal_details,
    reasons,
    breadth=None,
    etf_flows=None,
    options_data=None,
    themes=None,
):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return "OPENAI_API_KEY が未設定のため、AI概況は生成していません。"

    client = OpenAI(api_key=api_key)

    market_lines = [
        f"{r['label']} 値={r.get('value')} 変化={r.get('change_text', 'N/A')}"
        for r in market_rows
    ]

    sector_lines = [
        f"{r['label']} {r.get('change_text', 'N/A')}"
        for r in sector_rows
    ]

    recent_lines = [
        _event_to_text(e)
        for e in (recent_events or [])
        if e.get("event_name")
    ]

    upcoming_lines = [
        _event_to_text(e)
        for e in (upcoming_events or [])
        if e.get("event_name")
    ]

    prompt = f"""
あなたは日本語で金融市場サマリーを書くプロのアナリストです。
以下のデータをもとに自然な日本語で概況を書いてください。

■ 出力ルール
- 箇条書きは禁止
- 500〜900文字
- 内容ごとに改行する
- 断定しすぎず市場コメントとして書く
- 「フロー分析」を必ず1段落入れる
- 最後にトレンドシグナルの意味を短く書く

■ 必ず触れる項目
- 日経平均、NYダウ、NASDAQ、S&P500、Russell2000
- VIX
- 米10年金利・米2年債利回り・長短金利差
- USD/JPY、DXY、EUR/USD
- WTI原油、ゴールド、銅
- セクター強弱
- 注目テーマ
- 経済指標（直近結果と今日の予定）
- Breadth
- ETFフロー
- Put/Call / オプションセンチメント

■ 市場データ
{chr(10).join(market_lines)}

■ セクター
{chr(10).join(sector_lines)}

■ 直近経済指標（結果重視）
{chr(10).join(recent_lines) if recent_lines else "なし"}

■ 今日の経済指標
{chr(10).join(upcoming_lines) if upcoming_lines else "なし"}

■ Breadth
{breadth if breadth else "なし"}

■ ETFフロー
{etf_flows if etf_flows else "なし"}

■ オプション
{options_data if options_data else "なし"}

■ 注目テーマ
{themes if themes else "なし"}

■ スコア
score={score}
regime={regime}

■ シグナル
{signal}
{"; ".join(signal_details) if signal_details else "特記事項なし"}

■ 理由
{"; ".join(reasons) if reasons else "特記事項なし"}
"""

    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        return res.choices[0].message.content
    except Exception as e:
        return f"AI要約の生成に失敗しました: {e}"
