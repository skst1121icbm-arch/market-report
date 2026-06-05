from config.settings import MARKET_SYMBOLS, SECTOR_ETFS, LATEST_HTML_FILE

from data.market_data import download_ohlc
from data.economic_calendar import fetch_minkabu_economic_events, split_events_for_mail
from data.fred_api import fetch_us_rate_extras
from data.market_internals import (
    fetch_market_breadth,
    fetch_etf_flows,
    fetch_options_data,
    detect_market_themes,
)

from logic.market_calc import build_rows, summarize_sector_attention
from logic.scoring import score_market, classify_regime
from logic.signal import generate_trend_signal

from output.ai_summary import generate_ai_summary
from output.html_builder import build_html
from output.mailer import send_mail

from utils.datetime_utils import now_jst


def run():
    print("===== START MARKET AI =====")

    now = now_jst()

    # =========================
    # ① 市場データ
    # =========================
    market_df = download_ohlc(list(MARKET_SYMBOLS.values()))
    sector_df = download_ohlc(list(SECTOR_ETFS.values()))

    market_rows = build_rows(market_df, MARKET_SYMBOLS)
    sector_rows = build_rows(sector_df, SECTOR_ETFS)

    sector_attention = summarize_sector_attention(sector_rows)

    # =========================
    # ② 経済指標
    # =========================
    events = fetch_minkabu_economic_events()
    macro_payload = split_events_for_mail(events, now)

    recent_events = macro_payload["yesterday_events"]
    upcoming_events = macro_payload["today_events"]

    # =========================
    # ③ 金利（FRED）
    # =========================
    rate_extras = fetch_us_rate_extras()

    # =========================
    # ④ 市場内部データ
    # =========================
    breadth = fetch_market_breadth()
    etf_flows = fetch_etf_flows()
    options_data = fetch_options_data()

    # =========================
    # ⑤ スコア
    # =========================
    score, reasons = score_market(
        market_rows,
        sector_rows,
        recent_events,
        upcoming_events,
        breadth=breadth,
        etf_flows=etf_flows,
        options_data=options_data,
    )

    regime = classify_regime(score)

    # =========================
    # ⑥ シグナル
    # =========================
    signal, signal_details = generate_trend_signal(
        score,
        market_rows,
        sector_attention,
        recent_events,
        upcoming_events,
    )

    # =========================
    # ⑦ テーマ
    # =========================
    themes = detect_market_themes(sector_rows, market_rows, reasons)

    # =========================
    # ⑧ AI
    # =========================
    ai_summary = generate_ai_summary(
        market_rows,
        sector_rows,
        recent_events,
        upcoming_events,
        score,
        regime,
        signal,
        signal_details,
        reasons,
        breadth,
        etf_flows,
        options_data,
        themes,
    )

    # =========================
    # ⑨ HTML
    # =========================
    html = build_html(
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
        themes,
        rate_extras,
    )

    with open(LATEST_HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    # =========================
    # ⑩ メール送信
    # =========================
    send_mail("Daily Market Report", html)

    print("===== END MARKET AI =====")

    return {
        "score": score,
        "regime": regime,
        "breadth": breadth,
    }
