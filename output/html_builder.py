from utils.datetime_utils import now_jst
import re
from html import escape

# =========================
# BASIC HELPERS
# =========================
def _fmt_num(v):
    if v in [None, "", "None"]:
        return "N/A"
    try:
        return f"{float(v):.2f}"
    except Exception:
        return escape(str(v))


def _fmt_pct(v):
    if v in [None, "", "None"]:
        return "N/A"
    try:
        return f"{float(v):.2f}%"
    except Exception:
        return escape(str(v))


def _safe(v):
    if v in [None, "", "None"]:
        return "N/A"
    return str(v)


def _find(label, rows):
    for r in rows or []:
        if r.get("label") == label:
            return r
    return None


def _val(label, rows):
    """常に (value, change_text) を返す"""
    r = _find(label, rows)
    if not r:
        return None, ""
    return r.get("value"), r.get("change_text", "")


def _color_change(v):
    """前日比文字列をそのまま返す（HTMLメール側で簡素表示）"""
    if not v:
        return ""
    return escape(str(v).strip())


def _sector_change(v):
    if not v:
        return ""
    return escape(str(v).strip())


def _warn(text):
    return escape(str(text))


# =========================
# SUMMARY
# =========================
def _clean_summary_text(text: str) -> str:
    """フォーマット維持 + 主因・市場の反応・結論の分離"""
    if not text:
        return (
            "主因: N/A\n"
            "市場の反応: N/A\n"
            "結論: N/A"
        )

    s = str(text)
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("**", "").strip()

    lines = [line.strip() for line in s.splitlines() if line.strip()]

    main = None
    reaction = None
    conclusion = None

    for line in lines:
        if line.startswith("主因") and not main:
            main = line.split(":", 1)[-1].strip()
        elif line.startswith("市場の反応") and not reaction:
            reaction = line.split(":", 1)[-1].strip()
        elif line.startswith("結論") and not conclusion:
            conclusion = line.split(":", 1)[-1].strip()

    fallback = [l for l in lines if not l.startswith(("主因", "市場の反応", "結論"))]
    i = 0
    if not main:
        main = fallback[i] if i < len(fallback) else "N/A"
        i += 1
    if not reaction:
        reaction = fallback[i] if i < len(fallback) else "N/A"
        i += 1
    if not conclusion:
        conclusion = fallback[i] if i < len(fallback) else "N/A"

    if main == reaction:
        reaction = "市場は方向感を探る展開"
    if reaction == conclusion:
        conclusion = "方向感に乏しい相場"

    return (
        f"主因: {escape(main)}\n"
        f"市場の反応: {escape(reaction)}\n"
        f"結論: {escape(conclusion)}"
    )


# =========================
# IMPORTANCE
# =========================
def _stars(e):
    """経済指標3段階表示"""
    rank = int(e.get("importance_rank", 1))
    is_super = e.get("is_super", False)

    if is_super:
        return "🔥★★★"
    if rank >= 3:
        return "★★★"
    if rank == 2:
        return "★★"
    return "★"


def _highlight_event_name(e):
    """SUPER / CPI系を軽く強調"""
    raw_name = _safe(e.get("event_name"))
    safe_name = escape(raw_name)

    is_super = bool(e.get("is_super", False))
    if is_super:
        return f"<b>🔥 {safe_name}</b>"

    if any(k in raw_name.lower() for k in ["cpi", "ppi", "雇用", "政策金利"]):
        return f"<b>{safe_name}</b>"

    return safe_name


def _policy_impact_stars(item):
    score = int(item.get("market_impact_score", 1))
    if score >= 3:
        return "★★★"
    if score == 2:
        return "★★"
    return "★"


def _highlight_policy_title(item):
    title = _safe(item.get("title"))
    safe_title = escape(title)

    if item.get("is_super"):
        safe_title = f"<b>🔥 {safe_title}</b>"
    elif item.get("is_cpi_linked"):
        safe_title = f"<b>{safe_title}</b>"

    url = _safe(item.get("url"))
    if url not in ["", "N/A"]:
        return f'<a href="{escape(url, quote=True)}" target="_blank">{safe_title}</a>'
    return safe_title


# =========================
# INLINE STYLE HELPERS
# =========================
def _table_open():
    return (
        '<table style="width:100%; border-collapse:collapse; margin:8px 0 16px 0; font-size:13px;">\n'
    )


def _table_close():
    return "</table>\n"


def _th(text, width_pct=None, align="center"):
    width_style = f"width:{width_pct}%;" if width_pct else ""
    return (
        f'<th style="border:1px solid #d9d9d9; padding:6px 8px; background:#f5f5f5; text-align:{align}; {width_style}">'
        f'{escape(str(text))}</th>'
    )


def _td(text, width_pct=None, align="center", colspan=None):
    colspan_attr = f' colspan="{colspan}"' if colspan else ""
    width_style = f"width:{width_pct}%;" if width_pct and not colspan else ""
    return (
        f'<td{colspan_attr} style="border:1px solid #e5e5e5; padding:6px 8px; text-align:{align}; vertical-align:top; {width_style}">'
        f'{text}</td>'
    )


def _section_title(icon, title):
    return f'\n<h4 style="margin:16px 0 8px 0;">{escape(icon)} {escape(title)}</h4>\n'


def _note(text):
    return f'<div style="color:#666; font-size:12px; margin:4px 0 12px 0;">{escape(text)}</div>\n'


# =========================
# TABLE RENDERERS
# =========================
def _table_3col(title_icon, title, rows):
    body = []
    for name, value, change in rows:
        body.append("<tr>")
        body.append(_td(escape(str(name)), 40, "left"))
        body.append(_td(_fmt_num(value) if value not in ["", None] else "", 30, "center"))
        body.append(_td(_color_change(change), 30, "center"))
        body.append("</tr>")

    return (
        _section_title(title_icon, title)
        + _table_open()
        + "<tr>"
        + _th("項目", 40, "left")
        + _th("値", 30)
        + _th("前日比", 30)
        + "</tr>\n"
        + "\n".join(body)
        + _table_close()
    )


def _table_2col(title_icon, title, rows, col1="項目", col2="値", value_renderer=None):
    body = []
    for left, right in rows:
        rendered = value_renderer(right) if value_renderer else escape(str(right))
        body.append("<tr>")
        body.append(_td(escape(str(left)), 50, "left"))
        body.append(_td(rendered, 50, "center"))
        body.append("</tr>")

    return (
        _section_title(title_icon, title)
        + _table_open()
        + "<tr>"
        + _th(col1, 50, "left")
        + _th(col2, 50)
        + "</tr>\n"
        + "\n".join(body)
        + _table_close()
    )


def _table_econ(title_icon, title, events):
    body = []
    if not events:
        body.append("<tr>")
        body.append(_td("該当なし（条件に一致する指標なし）", None, "center", colspan=6))
        body.append("</tr>")
    else:
        for e in events:
            body.append("<tr>")
            body.append(_td(escape(_safe(e.get("country"))), 10, "center"))
            body.append(_td(_highlight_event_name(e), 35, "left"))
            body.append(_td(escape(_safe(e.get("forecast"))), 15, "center"))
            body.append(_td(escape(_safe(e.get("actual"))), 15, "center"))
            body.append(_td(escape(_safe(e.get("previous"))), 15, "center"))
            body.append(_td(_stars(e), 10, "center"))
            body.append("</tr>")

    return (
        _section_title(title_icon, title)
        + _table_open()
        + "<tr>"
        + _th("国", 10)
        + _th("指標", 35, "left")
        + _th("予想", 15)
        + _th("結果", 15)
        + _th("前回", 15)
        + _th("重要度", 10)
        + "</tr>\n"
        + "\n".join(body)
        + _table_close()
    )


def _table_policy_news(title_icon, title, items):
    """
    12 / 18 / 35 / 20 / 8 / 7
    区分 / 発言者 / タイトル / 市場観点 / 影響 / 日付
    """
    body = []
    if not items:
        body.append("<tr>")
        body.append(_td("該当なし（前日の政策・要人発言なし）", None, "center", colspan=6))
        body.append("</tr>")
    else:
        for x in items:
            source = escape(_safe(x.get("source")))
            speaker = escape(_safe(x.get("speaker")))
            title_html = _highlight_policy_title(x)
            relevance = escape(_safe(x.get("market_relevance")))
            impact = escape(_policy_impact_stars(x))
            date_jst = escape(_safe(x.get("date_jst")))

            body.append("<tr>")
            body.append(_td(source, 12, "center"))
            body.append(_td(speaker, 18, "left"))
            body.append(_td(title_html, 35, "left"))
            body.append(_td(relevance, 20, "left"))
            body.append(_td(impact, 8, "center"))
            body.append(_td(date_jst, 7, "center"))
            body.append("</tr>")

    return (
        _section_title(title_icon, title)
        + _table_open()
        + "<tr>"
        + _th("区分", 12)
        + _th("発言者", 18, "left")
        + _th("タイトル", 35, "left")
        + _th("市場観点", 20, "left")
        + _th("影響", 8)
        + _th("日付", 7)
        + "</tr>\n"
        + "\n".join(body)
        + _table_close()
    )


# =========================
# MAIN
# =========================
def build_html(
    market_rows,
    sector_rows,
    score,
    regime,
    signal,
    signal_details,
    reasons,
    ai_summary,
    macro_payload,
    breadth,
    etf_flows,
    options_data,
    rate_extras,
    policy_news_payload=None,
):
    today = now_jst().strftime("%Y-%m-%d")

    # ===== 主要指数 =====
    major_rows = []
    for label in ["S&P500", "NASDAQ", "NYダウ", "Russell2000", "日経平均", "VIX"]:
        v, c = _val(label, market_rows)
        major_rows.append((label, v, c))
    major_table = _table_3col("🚀", "主要指数", major_rows)

    # ===== 金利 =====
    y10, y10c = _val("米10年金利", market_rows)
    y2 = rate_extras.get("米2年債利回り")
    y2_change = rate_extras.get("米2年債利回り_前日比_pct")
    try:
        y2_change_text = f"{y2_change:+.2f}%"
    except Exception:
        y2_change_text = "N/A"

    real_rate_raw = rate_extras.get("実質金利(10Y)")
    real_rate_prev = rate_extras.get("実質金利(10Y)_前回")
    real_rate = _safe(real_rate_raw)
    try:
        change = float(real_rate_raw) - float(real_rate_prev)
        real_rate_change_text = f"{change:+.2f}%"
    except Exception:
        real_rate_change_text = "N/A"

    rate_rows = [
        ("米10年債利回り", y10, y10c),
        ("米2年債利回り", y2, y2_change_text),
        ("実質金利", real_rate, real_rate_change_text),
    ]
    rate_table = _table_3col("✅", "金利", rate_rows)

    try:
        spread_val = float(y10) - float(y2)
        spread_text = f"{spread_val:.2f}"
        if spread_val < 0:
            spread_text = _warn(spread_text)
    except Exception:
        spread_text = "N/A"
    rate_comment = f'<div style="margin:4px 0 12px 0;">10Y-2Y: {spread_text}</div>\n'

    # ===== 為替 =====
    fx_rows = []
    for label in ["DXY", "USD/JPY", "EUR/USD"]:
        v, c = _val(label, market_rows)
        fx_rows.append((label, v, c))
    fx_table = _table_3col("💱", "為替", fx_rows)

    # ===== コモディティ =====
    commodity_rows = []
    for label in ["WTI原油", "ゴールド", "銅"]:
        v, c = _val(label, market_rows)
        commodity_rows.append((label, v, c))
    commodity_table = _table_3col("🛢️", "コモディティ", commodity_rows)

    # ===== 仮想通貨 =====
    crypto_rows = []
    for label in ["BTC (USD)", "ETH (USD)", "XRP (USD)", "SOL (USD)"]:
        v, c = _val(label, market_rows)
        display_name = label.replace(" (USD)", "")
        crypto_rows.append((display_name, v, c))
    crypto_table = _table_3col("🪙", "仮想通貨", crypto_rows)

    # ===== ETFフロー =====
    etf_rows = [
        ("SPY", _safe(etf_flows.get("SPY"))),
        ("QQQ", _safe(etf_flows.get("QQQ"))),
        ("IWM", _safe(etf_flows.get("IWM"))),
    ]
    etf_table = _table_2col(
        "💰",
        "ETFフロー",
        etf_rows,
        col1="項目",
        col2="前日比",
        value_renderer=_color_change,
    )
    etf_comment = f'<div style="margin:4px 0 12px 0;">市場傾向の解釈: {escape(_safe(etf_flows.get("interpretation")))}</div>\n'

    # ===== オプション =====
    options_rows = [
        ("Put/Call", _fmt_num(options_data.get("put_call"))),
    ]
    options_table = _table_2col("🎯", "オプション", options_rows, col1="項目", col2="値")
    options_comment = f'<div style="margin:4px 0 12px 0;">センチメント: {escape(_safe(options_data.get("sentiment")))}</div>\n'

    # ===== 市場の広がり =====
    ratio = breadth.get("ratio")
    ratio_text = _fmt_pct(ratio) if ratio is not None else "N/A"
    if ratio is not None and ratio <= 30:
        ratio_text = _warn(ratio_text)
    breadth_rows = [
        ("上昇銘柄比率", ratio_text),
    ]
    breadth_table = _table_2col("📈", "市場の広がり", breadth_rows, col1="項目", col2="値")
    breadth_comment = f'<div style="margin:4px 0 12px 0;">状態: {escape(_safe(breadth.get("state")))}</div>\n'

    # ===== セクター =====
    sector_rows_for_table = []
    for r in sector_rows or []:
        sector_rows_for_table.append((r["label"], _safe(r.get("change_text"))))
    sector_table = _table_2col(
        "✅",
        "セクター",
        sector_rows_for_table,
        col1="セクター",
        col2="前日比",
        value_renderer=_sector_change,
    )

    # ===== 前日の政策・要人発言サマリー =====
    policy_news_section = _table_policy_news(
        "🗞️",
        "前日の政策・要人発言サマリー",
        policy_news_payload or [],
    )

    # ===== 経済指標 =====
    econ_super_important = _table_econ(
        "🚨",
        "重要経済指標",
        macro_payload.get("super_important_events", []),
    )
    econ_today = _table_econ(
        "📅",
        "経済指標（本日）",
        macro_payload.get("today_events", []),
    )
    econ_week = _table_econ(
        "📅",
        "経済指標（今週・重要）",
        macro_payload.get("week_events", []),
    )
    econ_week_comment = _note("今週の未発表かつ重要度★★以上の指標のみ表示")
    econ_yesterday = _table_econ(
        "📅",
        "経済指標（昨日）",
        macro_payload.get("yesterday_events", []),
    )

    # ===== まとめ =====
    summary_section = f"""
<h4 style=\"margin:16px 0 8px 0;\">🧠 まとめ</h4>
<pre style=\"white-space:pre-wrap; font-family:Arial, sans-serif; font-size:13px; line-height:1.6; margin:0 0 16px 0;\">{_clean_summary_text(ai_summary)}</pre>
"""

    # ===== スコア =====
    score_section = f"""
<h4 style=\"margin:16px 0 8px 0;\">📊 スコア</h4>
<div style=\"margin:0 0 16px 0;\">{escape(str(score))} ({escape(_safe(regime))})<br>{escape(_safe(signal))}</div>
"""

    return f"""
<html>
  <body style=\"font-family:Arial, sans-serif; font-size:13px; color:#222;\">
    <h3 style=\"margin:0 0 16px 0;\">Daily Market Report ({today})</h3>
    {major_table}
    {rate_table}
    {rate_comment}
    {fx_table}
    {commodity_table}
    {crypto_table}
    {etf_table}
    {etf_comment}
    {options_table}
    {options_comment}
    {breadth_table}
    {breadth_comment}
    {sector_table}
    {policy_news_section}
    {econ_super_important}
    {econ_today}
    {econ_week}
    {econ_week_comment}
    {econ_yesterday}
    {summary_section}
    {score_section}
  </body>
</html>
"""
