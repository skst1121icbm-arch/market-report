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
        "VIX", "警戒", "逆転"
    ]
    return any(k in sentence for k in keywords)


def _format_text(text: str):
    if not text:
        return "要約: 生成失敗"

    sentences = _split_sentences(text)

    if not sentences:
        return f"要約: {text}"

    first = sentences[0]
    summary = f"要約: {first}"

    out = [summary, ""]

    for s in sentences:
        if _is_important(s):
            s = f"<b>{s}</b>"
        out.append(s)

    return "\n".join(out)


def _events_to_text(events):
    lines = []
    for e in events or []:
        name = e.get("event_name")
        country = e.get("country")
        forecast = e.get("forecast")
        actual = e.get("actual")
        previous = e.get("previous")
        status = e.get("event_status")

        line = f"{country} {name} 予想={forecast} 結果={actual} 前回={previous} 区分={status}"
        lines.append(line)

    return "\n".join(lines) if lines else "なし"


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
・250〜500文字
・最初の一文で全体像
・スコアという単語は使わない
・最後に「戦略: 売り」または「戦略: 待機」のどちらかを1行で書く
・Breadth、ETF、Options、金利逆転、経済指標を反映する
・昨日の経済指標結果と、本日の経済指標（結果または予定）を分けて認識する

【市場】
{chr(10).join(market_lines)}

【セクター】
{chr(10).join(sector_lines)}

【昨日の経済指標】
{_events_to_text(recent_events)}

【本日の経済指標】
{_events_to_text(upcoming_events)}

【Breadth】
{breadth}

【ETF】
{etf_flows}

【Options】
{options_data}

【シグナル】
{signal}

【補足理由】
{" / ".join(reasons) if reasons else "なし"}
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
