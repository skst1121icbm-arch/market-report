import os
(from openai import OpenAI
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
        return "AI要約は未設定"

    client = OpenAI(api_key=api_key)

    market_lines = [
        f"{r['label']} {r.get('change_text', 'N/A')}"
        for r in market_rows
    ]

    sector_lines = [
        f"{r['label']} {r.get('change_text', 'N/A')}"
        for r in sector_rows
    ]

    prompt = f"""
あなたは金融アナリストです。

以下をもとに日本語で市場概況を書いてください。

【条件】
・自然な文章（箇条書き禁止）
・500〜800文字
・最後に今のトレンドを一言

【市場】
{chr(10).join(market_lines)}

【セクター】
{chr(10).join(sector_lines)}

【Breadth】
{breadth}

【ETF】
{etf_flows}

【Options】
{options_data}

【テーマ】
{themes}

【スコア】
score={score}
regime={regime}
"""

    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )

        return res.choices[0].message.content

    except Exception as e:
        return f"AIエラー: {e}"


