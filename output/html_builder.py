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
    """
    常に2要素タプルを返す
    """
    r = _find(label, rows)
    if not r:
        return None, ""
    return r.get("value"), r.get("change_text", "")


def _color_change(v):
    if not v:
        return ""
    s = str(v)
    if s.startswith("+"):
        return f'<span class="up">{escape(s)}</span>'
    if s.startswith("-"):
        return f'<span class="down">{escape(s)}</span>'
    return escape(s)


def _warn(text):
    return f'<span class="warn">{escape(str(text))}</span>'


# =========================
# SUMMARY
# =========================
def _clean_summary_text(text: str) -> str:
    """
    既存の <b> や markdown の ** を落として、
    先頭の「要約: ...」行だけ太字にする
    """
    if not text:
        return "N/A"

    s = str(text)
    s = re.sub(r"</?b>", "", s, flags=re.IGNORECASE)
    s = s.replace("**", "")

    lines = s.split("\n")
    blocks = []

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        esc = escape(line)
        if i == 0 and line.startswith("要約:"):
            blocks.append(f'<div class="summary-lead">{esc}</div>')
        else:
            blocks.append(f"<div>{esc}</div>")

    return "".join(blocks) if blocks else "N/A"


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


# =========================
# CSS
# =========================
def _style_block():
    return """
    <style>
      body {
        font-family: Arial, sans-serif;
        color: #222;
        line-height: 1.7;
        max-width: 960px;
        margin: 20px auto;
      }

      h2 {
        margin: 0 0 18px 0;
        font-size: 24px;
      }

      h3 {
        margin: 22px 0 10px 0;
        font-size: 18px;
      }

      p {
        margin: 8px 0 18px 0;
      }

      .report-table {
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed;
        font-size: 14px;
        margin-bottom: 12px;
      }

      .report-table th {
        background: #eaf3ff;
        padding: 8px 10px;
        border-bottom: 1px solid #d9e3f0;
        text-align: center;
        font-weight: 700;
      }

      .report-table td {
        padding: 8px 10px;
        border-bottom: 1px solid #eceff4;
        text-align: center;
        vertical-align: middle;
        word-wrap: break-word;
      }

      .report-table th,
      .report-table td {
        border-left: none;
        border-right: none;
      }

      .up {
        color: #0a8f2a;
        font-weight: 600;
      }

      .down {
        color: #c62828;
        font-weight: 600;
      }

      .warn {
        color: #c62828;
        font-weight: 700;
      }

      .summary-box {
        background: #f8f9fb;
        padding: 12px;
        border-radius: 8px;
        line-height: 1.8;
      }

      .summary-lead {
        font-weight: 700;
        margin-bottom: 8px;
      }

      .comment-line {
        margin: 8px 0 18px 0;
      }

      @media only screen and (max-width: 640px) {
        body {
          max-width: 100%;
          margin: 12px;
        }

        .report-table {
          font-size: 12px;
        }

        .report-table th,
        .report-table td {
          padding: 6px 6px;
        }
      }
    </style>
    """


# =========================
# TABLE BUILDERS
# =========================
def _table_3col(title_icon, title, rows):
    body = []
    for name, value, change in rows:
        body.append(f"""
        <tr>
          <td>{escape(str(name))}</td>
          <td>{_fmt_num(value) if value not in ["", None] else ""}</td>
          <td>{_color_change(change)}</td>
        </tr>
        """)

    return f"""
    <h3>{title_icon} {title}</h3>
    <table class="report-table">
      <colgroup>
        <col style="width:40%">
        <col style="width:30%">
        <col style="width:30%">
      </colgroup>
      <tr>
        <th>項目</th>
        <th>値</th>
        <th>前日比</th>
      </tr>
      {''.join(body)}
    </table>
    """


def _table_2col(title_icon, title, rows, col1="項目", col2="値"):
    body = []
    for left, right in rows:
        body.append(f"""
        <tr>
          <td>{escape(str(left))}</td>
          <td>{right}</td>
        </tr>
        """)

    return f"""
    <h3>{title_icon} {title}</h3>
    <table class="report-table">
      <colgroup>
        <col style="width:50%">
        <col style="width:50%">
      </colgroup>
      <tr>
        <th>{escape(col1)}</th>
        <th>{escape(col2)}</th>
      </tr>
      {''.join(body)}
    </table>
    """


def _table_econ(title_icon, title, events):
    body = []

    if not events:
        body.append("""
        <tr>
          <td colspan="6">なし</td>
        </tr>
        """)
    else:
        for e in events:
            body.append(f"""
            <tr>
              <td>{escape(_safe(e.get("country")))}</td>
              <td>{escape(_safe(e.get("event_name")))}</td>
              <td>{escape(_safe(e.get("forecast")))}</td>
              <td>{escape(_safe(e.get("actual")))}</td>
              <td>{escape(_safe(e.get("previous")))}</td>
              <td>{_stars(e)}</td>
            </tr>
            """)

    return f"""
    <h3>{title_icon} {title}</h3>
    <table class="report-table">
      <colgroup>
        <col style="width:10%">
        <col style="width:35%">
        <col style="width:15%">
        <col style="width:15%">
        <col style="width:15%">
        <col style="width:10%">
      </colgroup>
      <tr>
        <th>国</th>
        <th>指標</th>
        <th>予想</th>
        <th>結果</th>
        <th>前回</th>
        <th>重要度</th>
      </tr>
      {''.join(body)}
    </table>
    """


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
        y2_change_text = "N/A"

    rate_rows = [
        ("米10年債利回り", y10, y10c),
        ("米2年債利回り", y2, y2_change_text),
    ]
    rate_table = _table_3col("✅", "金利", rate_rows)

    try:
        spread_val = float(y10) - float(y2)
        spread_text = f"{spread_val:.2f}"
        if spread_val < 0:
            spread_text = _warn(spread_text)
    except Exception:
        spread_text = "N/A"

    rate_comment = f"""
    <div class="comment-line">
      <b>10Y-2Y:</b> {spread_text}
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
        display_name = label.replace(" (USD)", "")
        crypto_rows.append((display_name, v, c))

    crypto_table = _table_3col("🪙", "仮想通貨", crypto_rows)

    # ===== ETFフロー =====
    etf_rows = [
        ("SPY", _color_change(_safe(etf_flows.get("SPY")))),
        ("QQQ", _color_change(_safe(etf_flows.get("QQQ")))),
        ("IWM", _color_change(_safe(etf_flows.get("IWM")))),
    ]

    etf_table = _table_2col("💰", "ETFフロー", etf_rows, col1="項目", col2="前日比")

    etf_comment = f"""
    <div class="comment-line">
      <b>市場傾向の解釈:</b> {escape(_safe(etf_flows.get("interpretation")))}
    </div>
    """

    # ===== オプション =====
    options_rows = [
        ("Put/Call", _fmt_num(options_data.get("put_call"))),
    ]

    options_table = _table_2col("🎯", "オプション", options_rows, col1="項目", col2="値")

    options_comment = f"""
    <div class="comment-line">
      <b>センチメント:</b> {escape(_safe(options_data.get("sentiment")))}
    </div>
    """

    # ===== 市場の広がり =====
    ratio = breadth.get("ratio")
    ratio_text = _fmt_pct(ratio)
    if ratio is not None and ratio <= 30:
        ratio_text = _warn(ratio_text)

    breadth_rows = [
        ("上昇銘柄比率", ratio_text),
        ("状態", escape(_safe(breadth.get("state")))),
    ]

    breadth_table = _table_2col("📈", "市場の広がり", breadth_rows, col1="項目", col2="値")

    # ===== セクター =====
    sector_rows_for_table = []
    for r in sector_rows:
        sector_rows_for_table.append(
            (r["label"], _color_change(_safe(r.get("change_text"))))
        )

    sector_table = _table_2col("✅", "セクター", sector_rows_for_table, col1="セクター", col2="前日比")

    # ===== 経済指標（昨日 / 本日） =====
    econ_yesterday = _table_econ("📅", "経済指標（昨日）", macro_payload.get("yesterday_events", []))
    econ_today = _table_econ("📅", "経済指標（本日）", macro_payload.get("today_events", []))

    # ===== まとめ =====
    summary_section = f"""
    <h3>🧠 まとめ</h3>
    <div class="summary-box">
      {_clean_summary_text(ai_summary)}
    </div>
    """

    # ===== スコア =====
    score_section = f"""
    <h3>📊 スコア</h3>
    <div>{escape(str(score))} ({escape(_safe(regime))})<br>{escape(_safe(signal))}</div>
    """

    return f"""
    <html>
    <head>
      {_style_block()}
    </head>
    <body>

      <h2>Daily Market Report ({today})</h2>

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

      {econ_yesterday}
      {econ_today}

      {summary_section}
      {score_section}

    </body>
    </html>
    """
