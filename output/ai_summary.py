import os
from open_rows,from openai import OpenAI
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

    # 市場
    market_lines = []
    for r in market_rows:
        txt = r.get("change_text", "N/A")
        market_lines.append(f"{r['label']} {txt}")

    # セクター
    sector_lines = []
    for r in sector_rows:
        txt = r.get("change_text", "N/A")
        sector_lines.append(f"{r['label']} {txt}")

    prompt = f"""
あなたは金融アナリストです。

以下をもとに自然な日本語で市場概況を書いてください。

条件:
・箇条書き禁止
・500〜800文字
・最後にトレンドを一言

市場:
{chr(10).join(market_lines)}

セクター:
{chr(10).join(sector_lines)}

Breadth:
{breadth}

ETF:
{etf_flows}

Options:
{options_data}

テーマ:
{themes}

スコア:
{score} / {regime}

シグナル:
{signal}
"""

    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )

        return res.choices[0].message.content

    except Exception as e:
        return f"AIエラー: {e}"


def generate_ai_summary(
