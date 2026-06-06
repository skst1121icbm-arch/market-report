import os
ences(text: str):import re
    """
    日本語の句点でざっくり文分割
    """
    if not text:
        return []

    parts = re.split(r'(?<=。)', text)
    return [p.strip() for p in parts if p.strip()]


def _is_important_sentence(sentence: str) -> bool:
    """
    重要文判定
    """
    keywords = [
        "強気", "弱気", "リスクオン", "リスクオフ",
        "上昇", "下落", "資金流入", "資金流出",
        "VIX", "Put/Call", "Breadth",
        "全面安", "全面上昇", "警戒", "追い風", "逆風"
    ]
    return any(k in sentence for k in keywords)


def _make_one_line_summary(sentences):
    """
    最初の要約1行を作る
    """
    if not sentences:
        return "要約: 概況を生成できませんでした。"

    first = sentences[0]
    # 長すぎるときの軽い調整
    if len(first) > 70:
        first = first[:70].rstrip("、，, ") + "…"

    return f"要約: {first}"


def _format_ai_text(raw_text: str) -> str:
    """
    1) 最初に要約1行を追加
    2) 重要文だけ太字
    3) 読みやすいように改行
    """
    if not raw_text:
        return "要約: 概況を生成できませんでした。"

    sentences = _split_sentences(raw_text)
    if not sentences:
        return f"要約: {raw_text}"

    summary_line = _make_one_line_summary(sentences)

    formatted = [summary_line, ""]

    paragraph = []
    for s in sentences:
        if _is_important_sentence(s):
            s = f"<b>{s}</b>"

        paragraph.append(s)

        # 2文ごとに段落を切る
        if len(paragraph) >= 2:
            formatted.append("".join(paragraph))
            formatted.append("")
            paragraph = []

    if paragraph:
        formatted.append("".join(paragraph))

    return "\n".join(formatted).strip()


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
        return "要約: AI要約未設定"

    client = OpenAI(api_key=api_key)

    # 市場データ
    market_lines = [
        f"{r['label']} {r.get('change_text', 'N/A')}"
        for r in market_rows
    ]

    # セクター
    sector_lines = [
        f"{r['label']} {r.get('change_text', 'N/A')}"
        for r in sector_rows
    ]

    # 経済指標（簡易）
    recent_lines = []
    for e in recent_events or []:
        recent_lines.append(
            f"{e.get('event_name')} 結果={e.get('actual')} 予想={e.get('forecast')}"
        )

    upcoming_lines = []
    for e in upcoming_events or []:
        upcoming_lines.append(
            f"{e.get('event_name')} 予想={e.get('forecast')}"
        )

    prompt = f"""
以下のデータをもとに市場概況を日本語で簡潔に説明してください。

【条件】
・箇条書き禁止
・250〜500文字
・最初の1文で全体感がわかるように書く
・スコアやレジームという言葉は出さない
・テーマという見出しは使わない
・Breadth、ETF、Options の意味をやさしく反映する

【市場】
{chr(10).join(market_lines)}

【セクター】
{chr(10).join(sector_lines)}

【直近経済指標】
{chr(10).join(recent_lines) if recent_lines else "なし"}

【今後の経済指標】
{chr(10).join(upcoming_lines) if upcoming_lines else "なし"}

【Market Breadth】
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

        raw_text = res.choices[0].message.content
        return _format_ai_text(raw_text)

    except Exception as e:
        return f"要約: AIエラー\n\n{e}"

from openai import OpenAI


