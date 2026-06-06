import os
from openai import OpenAI


_rows,def generate_ai_summary(
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

    # 市場データ
    market_lines = []
    for r in market_rows:
        label = r.get("label")
        change = r.get("change_text", "N/A")
        market_lines.append(f"{label} {change}")

    # セクター
    sector_lines = []
    for r in sector_rows:
        label = r.get("label")
        change = r.get("change_text", "N/A")
        sector_lines.append(f"{label} {change}")

    prompt = (
        "あなたは金融アナリストです。\n\n"
        "以下をもとに市場概況を書いてください。\n\n"
        "条件:\n"
        "- 箇条書き禁止\n"
        "- 500〜800文字\n"
        "- 最後にトレンドを一言\n\n"
        "市場:\n"
        + "\n".join(market_lines)
        + "\n\nセクター:\n"
        + "\n".join(sector_lines)
        + f"\n\nBreadth:\n{breadth}"
        + f"\n\nETF:\n{etf_flows}"
        + f"\n\nOptions:\n{options_data}"
        + f"\n\nテーマ:\n{themes}"
        + f"\n\nスコア:\n{score} / {regime}"
        + f"\n\nシグナル:\n{signal}"
    )

    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return res.choices[0].message.content

    except Exception as e:
        return f"AIエラー: {e}"
    market_rows,
