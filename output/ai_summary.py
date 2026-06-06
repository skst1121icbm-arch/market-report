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
    breadth=None,
    etf_flows=None,
    options_data=None,
):

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        return "AI要約未設定"

    client = OpenAI(api_key=api_key)

    # 市場データ整形
    market_lines = [
        f"{r['label']} {r.get('change_text', 'N/A')}"
        for r in market_rows
    ]

    # セクター
    sector_lines = [
        f"{r['label']} {r.get('change_text', 'N/A')}"
        for r in sector_rows
    ]

    prompt = f"""
以下の市場データをもとに市場概況を日本語で簡潔に説明してください。

【条件】
・箇条書き禁止
・200〜400文字
・客観的に説明する

【市場】
{chr(10).join(market_lines)}

【セクター】
{chr(10).join(sector_lines)}

【Market Breadth】
{breadth}

【ETF】
{etf_flows}

【Options】
{options_data}
"""

    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )

        return res.choices[0].message.content

    except Exception as e:
        return f"AIエラー: {e}"
``
