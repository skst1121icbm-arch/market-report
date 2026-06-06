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
    """前日比: +は緑、-は赤"""
    if not v:
        return ""
    s = str(v).strip()

    if s.startswith("+"):
        return f'<span style="color:#16a34a; font-weight:600;">{escape(s)}</span>'
    elif s.startswith("-"):
        return f'<span style="color:#dc2626; font-weight:600;">{escape(s)}</span>'

    return escape(s)


def _sector_change(v):
    """セクター前日比: 色付き + 太字"""
    if not v:
        return ""
    s = str(v).strip()

    if s.startswith("+"):
        return f'<span style="color:#16a34a; font-weight:700;">{escape(s)}</span>'
    elif s.startswith("-"):
        return f'<span style="color:#dc2626; font-weight:700;">{escape(s)}</span>'

    return escape(s)


def _warn(text):
    return f'<span style="color:#dc2626; font-weight:600;">{escape(str(text))}</span>'


# =========================
# SUMMARY
# =========================
def _clean_summary_text(text: str) -> str:
    """
    フォーマット維持 + 主因・市場・結論の分離
    """

    if not text:
        return (
            "<strong>主因:</strong> N/A<br>"
            "<strong>市場の反応:</strong> N/A<br>"
            "<strong>結論:</strong> N/A"
        )

    s = str(text)

    # HTML削除
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("**", "")
    s = s.strip()

    lines = [line.strip() for line in s.splitlines() if line.strip()]

    main = None
    reaction = None
    conclusion = None

    # ✅ ラベル優先
    for line in lines:
        if line.startswith("主因") and not main:
            main = line.split(":", 1)[-1].strip()
        elif line.startswith("市場の反応") and not reaction:
            reaction = line.split(":", 1)[-1].strip()
        elif line.startswith("結論") and not conclusion:
            conclusion = line.split(":", 1)[-1].strip()

    # ✅ fallback（AI崩れ対策）
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

    # ✅ 重複防止（重要）
    if main == reaction:
        reaction = "市場は方向感を探る展開"
    if reaction == conclusion:
        conclusion = "方向感に乏しい相場"

    # ✅ 結論カラー
    if "リスクオフ" in conclusion:
        conclusion_html = f'<span style="color:#dc2626; font-weight:700;">{escape(conclusion)}</span>'
    elif "リスクオン" in conclusion:
        conclusion_html = f'<span style="color:#16a34a; font-weight:700;">{escape(conclusion)}</span>'
    else:
        conclusion_html = escape(conclusion)

    return (
        f"<strong>主因:</strong> {escape(main)}<br>"
        f"<strong>市場の反応:</strong> {escape(reaction)}<br>"
        f"<strong>結論:</strong> {conclusion_html}"
    )


# =========================
# IMPORTANCE
# =========================
def _stars(e):
    txt = f"{_safe(e.get('importance_label'))} {_safe(e.get('event_status'))}"
    if "高" in txt or "重要" in txt:
        return "★★★"
    elif "中" in txt:
        return "★★"
    return "★"


def _is_high_importance(e):
    txt = str(e.get("importance_label", ""))
    return ("高" in txt) or ("重要" in txt)


def _highlight_event_name(e):
    """
    CPIは赤背景、重要指標は太字
    """
    raw_name = _safe(e.get("event_name"))
    safe_name = escape(raw_name)

    # CPI強調
    if "CPI" in raw_name:
        safe_name = (
            '<span style="background:#dc2626; color:#ffffff; '
            'padding:2px 6px; border-radius:4px; font-weight:700;">'
            f'{safe_name}</span>'
        )

    # 高重要度は太字
    if _is_high_importance(e):
        safe_name = f"<strong>{safe_name}</strong>"

    return safe_name


# =========================
# INLINE STYLE HELPERS
# =========================
def _table_open():
    return (
        '<table style="width:100%; border-collapse:collapse; '
        'font-size:14px; line-height:1.5; margin:8px 0 14px 0;">'
    )


def _table_close():
    return "</table><br>"


def _th(text, width_pct=None, align="center"):
    width_style = f"width:{width_pct}%;" if width_pct else ""
    return (
        f'<th style="{width_style} border-bottom:1px solid #d9dde3; '
        f'padding:8px 6px; text-align:{align}; background:#f8fafc; '
        f'font-weight:700;">{escape(str(text))}</th>'
    )


def _td(text, width_pct=None, align="center", colspan=None):
    colspan_attr = f' colspan="{colspan}"' if colspan else ""
    width_style = f"width:{width_pct}%;" if width_pct and not colspan else ""
    return (
        f'<td{colspan_attr} style="{width_style} border-bottom:1px solid #edf2f7; '
        f'padding:8px 6px; text-align:{align}; vertical-align:middle;">{text}</td>'
    )


def _section_title(icon, title):
    return (
        f'<h3 style="margin:18px 0 8px 0; font-size:18px; '
        f'font-weight:700;">{icon} {escape(title)}</h3>'
    )


def _note(text):
    return (
        f'<div style="font-size:12px; color:#666; margin:-6px 0 12px 0;">'
        f'{escape(text)}</div>'
    )


# =========================
# TABLE RENDERERS
# =========================
def _table_3col(title_icon, title, rows):
    """
    40 / 30 / 30 固定
    主要指数 / 金利 / 為替 / コモディティ / 仮想通貨
    """
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
        + "</tr>"
        + "".join(body)
        + _table_close()
    )


def _table_2col(title_icon, title, rows, col1="項目", col2="値", value_renderer=None):
    """
    50 / 50 固定
    ETF / オプション / 市場の広がり / セクター
    """
    body = []
    for left, right in rows:
        rendered = value_renderer(right) if value_renderer else right
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
        + "</tr>"
        + "".join(body)
        + _table_close()
    )


def _table_econ(title_icon, title, events):
    """
    10 / 35 / 15 / 15 / 15 / 10 固定
    国 / 指標 / 予想 / 結果 / 前回 / 重要度
    """
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
        + "</tr>"
        + "".join(body)
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

# ✅ NEW：実質金利
real_rate = rate_extras.get("実質金利")
real_rate_change = rate_extras.get("実質金利_前日比")
try:
    real_rate_change_text = f"{real_rate_change:+.2f}%"
except Exception:
    real_rate_change_text = "N/A"

# ✅ NEW：利下げ折込回数
cut_expect = rate_extras.get("利下げ折込回数")
cut_expect_change = rate_extras.get("利下げ折込回数_変化")
try:
    cut_expect_change_text = f"{cut_expect_change:+.2f}"
except Exception:
    cut_expect_change_text = "N/A"

# ✅ 最終テーブル
rate_rows = [
    ("米10年債利回り", y10, y10c),
    ("米2年債利回り", y2, y2_change_text),
    ("実質金利", real_rate, real_rate_change_text),       # ←追加
    ("利下げ折込回数", cut_expect, cut_expect_change_text),  # ←追加
]
rate_table = _table_3col("✅", "金利", rate_rows)

    try:
        spread_val = float(y10) - float(y2)
        spread_text = f"{spread_val:.2f}"
        if spread_val < 0:
            spread_text = _warn(spread_text)
    except Exception:
        spread_text = "N/A"

    rate_comment = (
        f'<div style="margin:-6px 0 12px 0;"><strong>10Y-2Y:</strong> {spread_text}</div>'
    )

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
    etf_comment = (
        f'<div style="margin:-6px 0 12px 0;"><strong>市場傾向の解釈:</strong> '
        f'{escape(_safe(etf_flows.get("interpretation")))}</div>'
    )

    # ===== オプション =====
    options_rows = [
        ("Put/Call", _fmt_num(options_data.get("put_call"))),
    ]
    options_table = _table_2col("🎯", "オプション", options_rows, col1="項目", col2="値")
    options_comment = (
        f'<div style="margin:-6px 0 12px 0;"><strong>センチメント:</strong> '
        f'{escape(_safe(options_data.get("sentiment")))}</div>'
    )

    # ===== 市場の広がり =====
    ratio = breadth.get("ratio")
    ratio_text = _fmt_pct(ratio)
    if ratio is not None and ratio <= 30:
        ratio_text = _warn(ratio_text)

    breadth_rows = [
        ("上昇銘柄比率", ratio_text),
    ]
    breadth_table = _table_2col("📈", "市場の広がり", breadth_rows, col1="項目", col2="値")
    breadth_comment = (
        f'<div style="margin:-6px 0 12px 0;"><strong>状態:</strong> '
        f'{escape(_safe(breadth.get("state")))}</div>'
    )

    # ===== セクター =====
    sector_rows_for_table = []
    for r in sector_rows:
        sector_rows_for_table.append((r["label"], _safe(r.get("change_text"))))
    sector_table = _table_2col(
        "✅",
        "セクター",
        sector_rows_for_table,
        col1="セクター",
        col2="前日比",
        value_renderer=_sector_change,
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
<h3 style="margin:18px 0 8px 0; font-size:18px; font-weight:700;">🧠 まとめ</h3>
<div>{_clean_summary_text(ai_summary)}</div>
"""

    # ===== スコア =====
    score_section = f"""
<h3 style="margin:18px 0 8px 0; font-size:18px; font-weight:700;">📊 スコア</h3>
<div>{escape(str(score))} ({escape(_safe(regime))})</div>
<div>{escape(_safe(signal))}</div>
"""

    return f"""
<h2 style="margin:0 0 12px 0;">Daily Market Report ({today})</h2>

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

{econ_super_important}
{econ_today}
{econ_week}
{econ_week_comment}
{econ_yesterday}

{summary_section}
{score_section}
"""
