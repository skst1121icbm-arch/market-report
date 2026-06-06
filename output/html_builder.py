from utils.datetime_utils import now_jstfrom utils.datetime_utils    try:
        return f"{float(v):.2f}%"
    except Exception:
        return "N/A"


def _find(label, rows):
    for r in rows:
        if r["label"] == label:
            return r
    return None


def _val(label, rows):
    r = _find(label, rows)
    if not r:
        return None, None
    return r.get("value"), r.get("change_text")


def _safe(v):
    if v in [None, "", "None"]:
        return "N/A"
    return str(v)


def _color_change(text):
    if not text:
        return ""
    s = str(text)
    if s.startswith("+"):
        return f'<span style="color:#0a8f2a; font-weight:600;">{s}</span>'
    elif s.startswith("-"):
        return f'<span style="color:#c62828; font-weight:600;">{s}</span>'
    return s


def _warn(text):
    return f'<span style="color:#c62828; font-weight:700;">{text}</span>'


def _render_summary(summary_text: str) -> str:
    """
    AIの出力のうち、先頭の「要約: ...」行だけ太字にする
    """
    if not summary_text:
        return "N/A"

    lines = str(summary_text).split("\n")
    out = []

    for i, line in enumerate(lines):
        if i == 0 and line.strip().startswith("要約:"):
            out.append(f"<b>{line}</b>")
        else:
            out.append(line)

    return "<br>".join(out)


def _importance_to_stars(event: dict) -> str:
    """
    経済指標の重要度を ★ で表示
    priority:
      importance_label を優先
      なければ event_status 文字列も補助的に見る
    """
    level = _safe(event.get("importance_label"))
    status = _safe(event.get("event_status"))
    text = f"{level} {status}"

    if "高" in text or "重要" in text:
        return "★★★"
    elif "中" in text:
        return "★★"
    else:
        return "★"


# =========================
# style constants
# =========================
COMMON_TABLE_STYLE = """
width:100%;
border-collapse:collapse;
table-layout:fixed;
font-size:14px;
"""

COMMON_TH_STYLE = """
background:#eaf3ff;
padding:10px 12px;
border-bottom:1px solid #d9e3f0;
text-align:left;
"""

COMMON_TD_STYLE = """
padding:10px 12px;
border-bottom:1px solid #eceff4;
vertical-align:middle;
"""

# 縦線を消すため、左右borderは使わない
RIGHT_TD_STYLE = COMMON_TD_STYLE + " text-align:right;"
CENTER_TD_STYLE = COMMON_TD_STYLE + " text-align:center;"


def _table_open():
    return f'<table style="{COMMON_TABLE_STYLE}">'


def _table_close():
    return "</table>"


def _th(label, align="left", width=None):
    align_css = f"text-align:{align};"
    width_css = f"width:{width};" if width else ""
    return f'<th style="{COMMON_TH_STYLE} {align_css} {width_css}">{label}</th>'


def _td(text, align="left"):
    style = COMMON_TD_STYLE
    if align == "right":
        style = RIGHT_TD_STYLE
    elif align == "center":
        style = CENTER_TD_STYLE
    return f'<td style="{style}">{text}</td>'


def _section_title(icon, title):
    return f'<h3 style="margin:22px 0 10px 0;">{icon} {title}</h3>'


# =========================
# generic tables
# =========================
def _table_3col(title_icon, title, rows):
    """
    項目 / 値 / 前日比
    主要指数・金利・為替・コモディティ・仮想通貨で使用
    """
    body = ""
    for name, value, change in rows:
        body += "<tr>"
        body += _td(name, "left")
        body += _td(_fmt_num(value) if value not in ["", None] else "", "right")
        body += _td(_color_change(change), "right")
        body += "</tr>"

    return (
        _section_title(title_icon, title)
        + _table_open()
        + "<tr>"
        + _th("項目", "left", "40%")
        + _th("値", "right", "30%")
        + _th("前日比", "right", "30%")
        + "</tr>"
        + body
        + _table_close()
    )


def _table_2col(title_icon, title, rows, col1="項目", col2="値", col1_width="50%", col2_width="50%"):
    """
    2列テーブル
    ETFフロー / オプション / 市場の広がり / セクター で使用
    """
    body = ""
    for c1, c2 in rows:
        body += "<tr>"
        body += _td(c1, "left")
        body += _td(c2, "right")
        body += "</tr>"

    return (
        _section_title(title_icon, title)
        + _table_open()
        + "<tr>"
        + _th(col1, "left", col1_width)
        + _th(col2, "right", col2_width)
        + "</tr>"
        + body
        + _table_close()
    )


def _table_econ(title_icon, title, events):
    """
    経済指標（昨日 / 本日）
    国 / 指標 / 予想 / 結果 / 前回 / 重要度
    """
    body = ""
    if not events:
        body = (
            "<tr>"
            + _td("なし", "left")
            + _td("", "left")
            + _td("", "right")
            + _td("", "right")
            + _td("", "right")
            + _td("", "center")
            + "</tr>"
        )
    else:
        for e in events:
            country = _safe(e.get("country"))
            event_name = _safe(e.get("event_name"))
            forecast = _safe(e.get("forecast"))
            actual = _safe(e.get("actual"))
            previous = _safe(e.get("previous"))
            stars = _importance_to_stars(e)

            body += "<tr>"
            body += _td(country, "left")
            body += _td(event_name, "left")
            body += _td(forecast, "right")
            body += _td(actual, "right")
            body += _td(previous, "right")
            body += _td(stars, "center")
            body += "</tr>"

    return (
        _section_title(title_icon, title)
        + _table_open()
        + "<tr>"
        + _th("国", "left", "10%")
        + _th("指標", "left", "35%")
        + _th("予想", "right", "15%")
        + _th("結果", "right", "15%")
        + _th("前回", "right", "15%")
        + _th("重要度", "center", "10%")
        + "</tr>"
        + body
        + _table_close()
    )


# =========================
# main HTML
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
    for label in ["S&P500", "NASDAQ", "NYダウ", "Russell2000", "日経平均"]:
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
        y2_change_text = ""

    rate_rows = [
        ("米10年債利回り", y10, y10c),
        ("米2年債利回り", y2, y2_change_text),
    ]
    rate_table = _table_3col("✅", "金利", rate_rows)

    # 10Y-2Y コメント（逆転なら赤）
    try:
        spread = float(y10) - float(y2)
        spread_text = f"{spread:.2f}"
        if spread < 0:
            spread_text = _warn(spread_text)
    except Exception:
        spread_text = "N/A"

    rate_comment = f"""
    <div style="margin-top:8px; margin-bottom:18px;">
        <b>10年債利回り - 2年債利回り:</b> {spread_text}
    </div>
    """

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
        crypto_rows.append((label, v, c))

    crypto_table = _table_3col("🪙", "仮想通貨", crypto_rows)

    # ===== ETFフロー（値列なし）=====
    etf_rows = [
        ("SPY", _color_change(_safe(etf_flows.get("SPY")))),
        ("QQQ", _color_change(_safe(etf_flows.get("QQQ")))),
        ("IWM", _color_change(_safe(etf_flows.get("IWM")))),
    ]

    etf_table = _table_2col(
        "💰",
        "ETFフロー",
        etf_rows,
        col1="項目",
        col2="前日比",
        col1_width="50%",
        col2_width="50%",
    )

    etf_comment = f"""
    <div style="margin-top:8px; margin-bottom:18px;">
        <b>市場傾向の解釈:</b> {_safe(etf_flows.get("interpretation"))}
    </div>
    """

    # ===== オプション（アイコン変更）=====
    options_rows = [
        ("Put/Call", _fmt_num(options_data.get("put_call"))),
    ]

    options_table = _table_2col(
        "🎯",
        "オプション",
        options_rows,
        col1="項目",
        col2="値",
        col1_width="50%",
        col2_width="50%",
    )

    options_comment = f"""
    <div style="margin-top:8px; margin-bottom:18px;">
        <b>センチメント:</b> {_safe(options_data.get("sentiment"))}
    </div>
    """

    # ===== 市場の広がり =====
    ratio = breadth.get("ratio")
    ratio_text = _fmt_pct(ratio)
    if ratio is not None and ratio <= 30:
        ratio_text = _warn(ratio_text)

    breadth_rows = [
        ("上昇銘柄比率", ratio_text),
        ("状態", _safe(breadth.get("state"))),
    ]

    breadth_table = _table_2col(
        "📈",
        "市場の広がり",
        breadth_rows,
        col1="項目",
        col2="値",
        col1_width="50%",
        col2_width="50%",
    )

    # ===== セクター =====
    sector_rows_for_table = []
    for r in sector_rows:
        sector_rows_for_table.append(
            (r["label"], _color_change(_safe(r.get("change_text"))))
        )

    sector_table = _table_2col(
        "✅",
        "セクター",
        sector_rows_for_table,
        col1="セクター",
        col2="前日比",
        col1_width="50%",
        col2_width="50%",
    )

    # ===== 経済指標（昨日 / 本日）=====
    yesterday_events = macro_payload.get("yesterday_events", [])
    today_events = macro_payload.get("today_events", [])

    econ_yesterday_table = _table_econ("📅", "経済指標（昨日）", yesterday_events)
    econ_today_table = _table_econ("📅", "経済指標（本日）", today_events)

    # ===== まとめ =====
    summary_html = _render_summary(ai_summary)

    summary_section = f"""
    <div style="margin:22px 0 24px 0;">
        <div style="font-weight:700; margin-bottom:8px;">🧠 まとめ</div>
        <div style="background:#f8f9fb; padding:12px; border-radius:8px; line-height:1.8;">
            {summary_html}
        </div>
    </div>
    """

    # ===== スコア =====
    score_section = f"""
    <div style="margin:22px 0 24px 0;">
        <div style="font-weight:700; margin-bottom:8px;">✅ スコア</div>
        {score} ({_safe(regime)})<br>
        {_safe(signal)}
    </div>
    """

    html = f"""
    <html>
    <body style="font-family:Arial, sans-serif; line-height:1.7; color:#222; max-width:960px; margin:20px auto;">

    <h2 style="margin-bottom:18px;">Daily Market Report ({today})</h2>

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
    {sector_table}
    {econ_yesterday_table}
    {econ_today_table}
    {summary_section}
    {score_section}

    </body>
    </html>
    """

    return html


# =========================
# format helpers
# =========================
def _fmt_num(v):
    try:
        return f"{float(v):.2f}"
    except Exception:
        return "N/A"


def _fmt_pct(v):
