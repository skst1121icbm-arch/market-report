import os
from openai import OpenAI


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
    if not api_key:
        return "OPENAI_API_KEY が未設定のため、AI概況は生成していません。"

    client = OpenAI(api_key=api_key)

    market_lines = [
        f"{r['label']} {r.get('change_text', 'N/A')}"
        for r in market_rows
    ]

    sector_lines = [
        f"{r['label']} {r.get('change_text', 'N/A')}"
        for r in sector_rows
    ]

    
recent_lines = [
    str(e.get("event_name") or "")
    for e in recent_events or []
]

upcoming_lines = [
    str(e.get("event_name") or "")
    for e in upcoming_events or []
]

prompt = f"""
あなたは日本語で金融市場サマリーを書くアナリストです。
以下のデータをもとに自然な日本語で概況を書いてください。

条件:
- 箇条書きは使わない
- 500〜800文字程度
- 主要指数・金利・為替・BTC・金・セクター・経済指標に触れる
- 最後にトレンドシグナルの意味を書く

【市場データ】
{chr(10).join(market_lines)}

【セクター】
{chr(10).join(sector_lines)}

【直近指標】
{chr(10).join(recent_lines) if recent_lines else "なし"}

【今後指標】
{chr(10).join(upcoming_lines) if upcoming_lines else "なし"}

【スコア】
{score}, {regime}

【シグナル】
{signal} / {'; '.join(signal_details)}
"""

    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        return res.choices[0].message.content
    except Exception:
        return "AI要約の生成に失敗しました。"
