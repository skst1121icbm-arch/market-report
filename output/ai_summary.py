import os
from openai import OpenAI


def generate recent_events,def generate_ai_summary(
    upcoming_events,
    score,
    regime,
    signal,
    signal_details,
    reasons,
    breadth=None,
    etf_flows=None,
    options_data=None,
    themes=None
):
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        return "AI要約は未設定"

    client = OpenAI(api_key=api_key)

    # 市場
    market_lines = []
    for r in market_rows:
        label = r.get("label", "")
        change = r.get("change_text", "N/A")
        market_lines.append(f"{label} {change}")

    # セクター
    sector_lines = []
    for r in sector_rows:
        label = r.get("label", "")
        change = r.get("change_text", "N/A")
        sector_lines.append(f"{label} {change}")

    # プロンプト（安全な連結方式）
    prompt = "あなたは金融アナリストです。\n\n"

    prompt += "以下をもとに市場概況を書いてください。\n"
    prompt += "・箇条書き禁止\n"
    prompt += "・500〜800文字\n"
    prompt += "・最後にトレンドを一言\n\n"

    prompt += "【市場】\n" + "\n".join(market_lines) + "\n\n"
    prompt += "【セクター】\n" + "\n".join(sector_lines) + "\n\n"

    prompt += f"【Breadth】\n{breadth}\n\n"
    prompt += f"【ETF】\n{etf_flows}\n\n"
    prompt += f"【Options】\n{options_data}\n\n"
    prompt += f"【テーマ】\n{themes}\n\n"
    prompt += f"【スコア】\n{score} / {regime}\n\n"
    prompt += f"【シグナル】\n{signal}\n"

    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        return res.choices[0].message.content

    except Exception as e:
        return f"AIエラー: {e}"
    market_rows,
    sector_rows,
