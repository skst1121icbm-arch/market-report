import os
import re
from openai import OpenAI


def _events_to_text(events):
    lines = []
    for e in events or []:
        line = f"{e.get('country')} {e.get('event_name')} 予想={e.get('forecast')} 結果={e.get('actual')} 前回={e.get('previous')}"
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
        f"{r['label']} {r.get('change_text','N/A')}"
        for r in market_rows
    ]

    sector_lines = [
        f"{r['label']} {r.get('change_text','N/A')}"
        for r in sector_rows
    ]

    prompt = f"""
以下の市場データを分析し、日本語でまとめてください。

【出力条件】
・200文字前後
・「要約」という言葉は禁止
・以下の形式で出力

主因:
市場を動かしたイベントや指標

市場の反応:
金利、ドル、セクターの動き

結論:
最終的な相場（例：ナスダック下落＋ディフェンシブ上昇）

【市場】
{chr(10).join(market_lines)}

【セクター】
{chr(10).join(sector_lines)}

【昨日の経済指標】
{_events_to_text(recent_events)}

【本日の経済指標】
{_events_to_text(upcoming_events)}

【Breadth】 {breadth}
【ETF】 {etf_flows}
【Options】 {options_data}

【シグナル】 {signal}
【補足理由】 {" / ".join(reasons) if reasons else "なし"}
"""

    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )

        return res.choices[0].message.content

    except Exception as e:
        return f"主因: AIエラー\n市場の反応: N/A\n結論: {e}"
