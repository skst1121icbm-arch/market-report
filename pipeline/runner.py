from config.settings import MARKET_SYMBOLS, SECTOR_ETFS, EXCEL_CALENDAR_FILE

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
    # =========================================
    # ① データ取得
    # =========================================
    symbols = list(MARKET_SYMBOLS.values())
    sector_symbols = list(SECTOR_ETFS.values())

    market_df = download_ohlc(symbols)
    sector_df = download_ohlc(sector_symbols)

    events = load_events_from_excel(EXCEL_CALENDAR_FILE)

    # =========================================
    # ② データ加工
    # =========================================
    market_rows = build_rows(market_df, MARKET_SYMBOLS)
    sector_rows = build_rows(sector_df, SECTOR_ETFS)

    sector_attention = summarize_sector_attention(sector_rows)

    # イベント区分（簡易版）
    recent_events = []
    upcoming_events = []

    for e in events:
        # 非厳密な分類（後で改善可能）
        if e.get("date"):
            recent_events.append(e)
        else:
            upcoming_events.append(e)

    # =========================================
    # ③ スコア計算
    # =========================================
    score, reasons = score_market(
        market_rows,
        sector_rows,
        recent_events,
        upcoming_events,
    )

    regime = classify_regime(score)

    # =========================================
    # ④ シグナル生成
    # =========================================
    signal, signal_details = generate_trend_signal(
        score,
        market_rows,
        sector_attention,
        recent_events,
        upcoming_events,
    )

    # =========================================
    # ⑤ AI要約
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

    # =========================================
    # ⑦ 出力
    # =========================================
    send_mail("マーケットレポート", html)

    save_daily_log(score, regime, signal)
    save_event_log(events)

    return {
        "score": score,
        "regime": regime,
        "signal": signal,
    }
