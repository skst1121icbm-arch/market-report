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

    # ===================================
    # ① 市場データ
    # ===================================
    market_df = download_ohlc(list(MARKET_SYMBOLS.values()))
    sector_df = download_ohlc(list(SECTOR_ETFS.values()))

    print("[DEBUG] market_df is None =", market_df is None)

    if market_df is not None:
        print("[DEBUG] df columns =", market_df.columns)
        print("[DEBUG] market_df head =")
        print(market_df.head())
    else:
        print("[DEBUG] market_df is None → yfinance失敗")

    # ===================================
    # 行データ生成
    # ===================================
    market_rows = build_rows(market_df, MARKET_SYMBOLS)
    sector_rows = build_rows(sector_df, SECTOR_ETFS)

    print("[DEBUG] market_rows =", market_rows[:5])
    print("[DEBUG] sector_rows =", sector_rows[:5])

    sector_attention = summarize_sector_attention(sector_rows)

    # ===================================
    # ② 経済指標
    # ===================================
    events = fetch_minkabu_economic_events()
    macro_payload = split_events_for_mail(events, now)

    recent_events = macro_payload["yesterday_events"]
    upcoming_events = macro_payload["today_events"]

    print("[DEBUG] recent_events =", recent_events)
    print("[DEBUG] upcoming_events =", upcoming_events)

    # ===================================
    # ③ 金利
    # ===================================
    rate_extras = fetch_us_rate_extras()
    print("[DEBUG] rate_extras =", rate_extras)

    # ===================================
    # ✅ ④ 内部データ（ここが今回の変更ポイント）
    # ===================================

    # ✅ Breadthに market_rows を渡す
    breadth = fetch_market_breadth(market_rows)

    # ✅ ETF / Options
    etf_flows = fetch_etf_flows(market_rows)
    options_data = fetch_options_data(market_rows)

    print("[DEBUG] breadth =", breadth)
    print("[DEBUG] etf_flows =", etf_flows)
    print("[DEBUG] options_data =", options_data)

    # ===================================
    # ⑤ スコア
    # ===================================
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

    print("[DEBUG] score =", score)
    print("[DEBUG] reasons =", reasons)

    # ===================================
    # ⑥ シグナル
    # ===================================
    signal, signal_details = generate_trend_signal(
        score,
        market_rows,
        sector_attention,
        recent_events,
        upcoming_events,
    )

    print("[DEBUG] signal =", signal)
    print("[DEBUG] signal_details =", signal_details)

    # ===================================
    # ⑦ テーマ
    # ===================================
    themes = detect_market_themes(sector_rows, market_rows, reasons)
    print("[DEBUG] themes =", themes)

    # ===================================
    # ⑧ AI
    # ===================================
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
        breadth=breadth,
        etf_flows=etf_flows,
        options_data=options_data,
        themes=themes,
    )

    print("[DEBUG] ai_summary =", ai_summary[:200])

    # ===================================
    # ⑨ HTML
    # ===================================
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

    print("[DEBUG] HTML saved =", LATEST_HTML_FILE)

    # ===================================
    # ⑩ メール
    # ===================================
    send_mail("Daily Market Report", html)

    print("===== END MARKET AI =====")

    return {
        "score": score,
        "regime": regime,
        "breadth": breadth,
        "etf_flows": etf_flows,
        "options_data": options_data,
    }
