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
        "VIX", "警戒", "逆転",
        "金利上昇", "金利低下", "ドル高", "ドル安",
        "ナスダック", "S&P500", "生活必需品", "ディフェンシブ"
    ]
    return any(k in sentence for k in keywords)


def _format_text(text: str):
    """
    AI出力をそのまま整形する。
    - 「要約:」は付けない
    - 主因 / 市場の反応 / 結論 をそのまま維持
    - 重要表現だけ <b> で強調
    """
    if not text:
        return "主因: N/A\n市場の反応: N/A\n結論: N/A"

    s = str(text).strip()

    # 余計なコードブロック除去
    s = s.replace("```", "").strip()

    lines = [line.strip() for line in s.splitlines() if line.strip()]
    out = []

    for line in lines:
        if _is_important(line):
            line = f"<b>{line}</b>"
        out.append(line)

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
        return "主因: AI未設定\n市場の反応: N/A\n結論: N/A"

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
以下の市場データをもとに、日本語で簡潔にまとめてください。

【最重要ルール】
・全体で200文字前後
・「要約」という言葉は禁止
・必ず以下の3項目形式で出力する
・各項目は重複禁止
・同じ内容を言い換えない
・結論には必ず数値を1つ以上入れる（例: ナスダック-1.8%、VIX+12%、米10年金利+0.08%）
・結論には必ず相場の強弱判定を含める（例: リスクオン / リスクオフ / 方向感乏しい）

【出力形式】
主因:
※ 市場を大きく動かしたイベントや指標だけを書く
※ 金利・ドル・株・セクターの値動きは書かない

市場の反応:
※ それを受けて金利、ドル、主要指数、セクターがどう動いたかだけを書く
※ 原因やイベント名を繰り返さない

結論:
※ 最終的にどんな相場だったかを1文で書く
※ 必ず数値を入れる
※ 必ず強弱判定を入れる
※ 例: リスクオフ。ナスダック-1.8%の一方、生活必需品に資金移動

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
        return f"主因: AIエラー\n市場の反応: N/A\n結論: {e}"
