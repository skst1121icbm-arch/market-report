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
    themes=None
):
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        return "AI要約は未設定"

    client = OpenAI(api_key=api_key)

    # 市場
    market_lines = []
    for r in market_rows:
        market_lines.append(f"{r.get('label')} {r.get('change_text')}")

    # セクター
    sector_lines = []
    for r in sector_rows:
        sector_lines.append(f"{r.get('label')} {r.get('change_text')}")

    prompt = "市場概況を日本語で書いてください。\n\n"

    prompt += "市場:\n" + "\n".join(market_lines) + "\n\n"
    prompt += "セクター:\n" + "\n".join(sector_lines) + "\n\n"
    prompt += f"Breadth:\n{breadth}\n\n"
    prompt += f"ETF:\n{etf_flows}\n\n"
    prompt += f"Options:\n{options_data}\n\n"
    prompt += f"テーマ:\n{themes}\n\n"
    prompt += f"スコア: {score} / {regime}\n"

    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        return res.choices[0].message.content

    except Exception as e:
        return str(e)
