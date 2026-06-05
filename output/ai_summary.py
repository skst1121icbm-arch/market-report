import os
from openai import OpenAI


# =========================
# 経済指標 → AI入力用テキスト
# =========================
def _event_to_text(e):
    name = str(e.get("event_name") or "")

    country = e.get("country")
    if country == "US":
        country_name = "米国"
    elif country == "JP":
        country_name = "日本"
    else:
        country_name = str(country or "")

    forecast = e.get("forecast")
    actual = e.get("actual")
    previous = e.get("previous")

    parts = [f"[{country_name}] {name}"]

    if actual is not None:
        parts.append(f"結果={actual}")
    if forecast is not None:
        parts.append(f"予想={forecast}")
    if previous is not None:
        parts.append(f"前回={previous}")

    return " / ".join(parts)


# =========================
# AIサマリー本体
# =========================
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
):
    api_key = os.getenv("OPENAI_API_KEY")

    # APIキー未設定でも落とさない
    if not api_key:
        return "OPENAI_API_KEY が未設定のため、AI概況は生成していません。"

    client = OpenAI(api_key=api_key)

    # =========================
    # 市場データ整形
    # =========================
    market_lines = [
        f"{r['label']} {r.get('change_text', 'N/A')}"
        for r in market_rows
    ]

    sector_lines = [
        f"{r['label']} {r.get('change_text', 'N/A')}"
        for r in sector_rows
    ]

    # =========================
    # 経済指標整形（重要）
    # =========================
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

    # =========================
    # プロンプト
    # =========================
    prompt = f"""
あなたは日本語で金融市場サマリーを書くプロのアナリストです。
以下のデータをもとに、市場の流れを自然な文章で説明してください。

■ 出力ルール（必須）
- 箇条書きは禁止
- 500〜800文字
- 内容ごとに改行する
- 話題が変わるごとに改行する
- 段落として読みやすくする
- 断定しすぎず、分析コメントとして書く

■ 必ず触れるもの
- 日経平均、NYダウ、NASDAQ、S&P500
- VIX、米10年金利
- USD/JPY、ゴールド、BTC
- セクターの強弱

■ 経済指標ルール（最重要）
- 「結果(actual)」を最優先で解釈する
- 予想との差（サプライズ）にも必要に応じて触れる
- 市場への影響として自然に説明する

■ 最後
- トレンドシグナルの意味を簡潔に書く

========================

【市場データ】
{chr(10).join(market_lines)}

【セクター】
{chr(10).join(sector_lines)}

【直近の経済指標（結果重視）】
{chr(10).join(recent_lines) if recent_lines else "なし"}

【今後の経済指標】
{chr(10).join(upcoming_lines) if upcoming_lines else "なし"}

【スコア】
score={score}
regime={regime}

【シグナル】
{signal}
{"; ".join(signal_details) if signal_details else "特記事項なし"}

【理由】
{"; ".join(reasons) if reasons else "特記事項なし"}
"""

    # =========================
    # API実行
    # =========================
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )

        return res.choices[0].message.content

    except Exception as e:
        return f"AI要約の生成に失敗しました: {e}"
