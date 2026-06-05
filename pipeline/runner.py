from config.settings import (
    MARKET_SYMBOLS,
    SECTOR_ETFS,
    EXCEL_CALENDAR_FILE,
    LATEST_HTML_FILE,
)

# data
from data.market_data import download_ohlc
from data.excel_loader import load_events_from_excel

# logic
from logic.market_calc import build_rows, summarize_sector_attention
from logic.scoring import score_market, classify_regime
from logic.signal import generate_trend_signal

# output
from output.ai_summary import generate_ai_summary
from output.html_builder import build_html
from output.mailer import send_mail
from output.csv_logger import save_daily_log, save_event_log


def run():
    print("===== START MARKET AI =====")

    # =========================================
    # ① データ取得
    # =========================================
    symbols = list(MARKET_SYMBOLS.values())
    sector_symbols = list(SECTOR_ETFS.values())

    market_df = download_ohlc(symbols)
    sector_df = download_ohlc(sector_symbols)

    events = load_events_from_excel(EXCEL_CALENDAR_FILE)

    # =========================================
    # ② 加工
    # =========================================
    market_rows = build_rows(market_df, MARKET_SYMBOLS)
    sector_rows = build_rows(sector_df, SECTOR_ETFS)

    sector_attention = summarize_sector_attention(sector_rows)

    recent_events = [e for e in events if e.get("date")]
    upcoming_events = [e for e in events if not e.get("date")]

    # =========================================
    # ③ スコア
    # =========================================
    score, reasons = score_market(
        market_rows,
        sector_rows,
        recent_events,
        upcoming_events,
    )

    regime = classify_regime(score)

    # =========================================
    # ④ シグナル
    # =========================================
    signal, signal_details = generate_trend_signal(
        score,
        market_rows,
        sector_attention,
        recent_events,
        upcoming_events,
    )

    # =========================================
    # ⑤ AI
    # =========================================
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
    )

    # =========================================
    # ⑥ HTML生成
    # =========================================
    html = build_html(
        market_rows,
        sector_rows,
        score,
        regime,
        signal,
        signal_details,
        reasons,
        ai_summary,
    )

    # ✅ ここが追加ポイント（最重要）
    with open(LATEST_HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"HTML saved to {LATEST_HTML_FILE}")

    # =========================================
    # ⑦ 出力
    # =========================================
    send_mail("マーケットレポート", html)

    save_daily_log(score, regime, signal)
    save_event_log(events)

    print("===== END MARKET AI =====")

    return {
        "score": score,
        "regime": regime,
        "signal": signal,
    }
