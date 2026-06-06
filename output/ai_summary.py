import os
import re
from openai import OpenAI


def _split_sentences(text: str):
    if not text:
        return []

    parts = re.split(r'(?<=。)', text)
    return [p.strip() for p in parts if p.strip()]


def _is_important(sentence: str):
    keywords = [
        "強気", "弱気", "下落", "上昇",
        "リスクオフ", "リスクオン",
        "資金流出", "資金流入",
        "VIX"
    ]
    return any(k in sentence for k in keywords)


def _format_text(text: str):
    if not text:
        return "要約: 生成失敗"

    sentences = _split_sentences(text)

    if not sentences:
        return f"要約: {text}"

    # ✅ 要約1行
    first = sentences[0]
    summary = f"要約: {first}"

    out = [summary, ""]

    for s in sentences:
        if _is_important(s):
            s = f"<b>{s}</b>"
        out.append(s)

    return "\n".join(out)


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
        return "要約: AI未設定"

    client = OpenAI(api_key=api_key)

    market_lines = [
        f"{r['label']} {r.get('change_text','N/A')}"
        for r in market_rows
    ]

    sector_lines = [
        f"{r['label']} {r.get('change_text','N/A')}"
        for r in sector_rows
    ]

    prompt = f"""
市場データをもとに日本語で簡潔に説明してください。

【条件】
・250〜400文字
・最初の一文で全体像
・スコアという単語は使わない

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

    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )

        raw = res.choices[0].message.content

        return _format_text(raw)

    except Exception as e:
        return f"要約: AIエラー\n{e}"
