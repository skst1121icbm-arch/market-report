import os
from openai import OpenAI


def generate_ai_summary(
    market_rows,
    sector_data=None,    sector_rows,
):

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        return "AI要約未設定"

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
市場データをもとに日本語で簡潔に概況を説明してください。

【条件】
・箇条書き禁止
・200〜500文字

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
"""

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )

    return res.choices[0].message.content
    recent_events,
    upcoming_events,
    score,
    regime,
    signal,
    signal_details,
    reasons,
    breadth=None,
    etf_flows=None,
