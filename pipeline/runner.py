from config.settings import (
    MARKET_SYMBOLS,
    SECTOR_ETFS,
    LATEST_HTML_FILE,
)

# data
from data.market_data import download_ohlc
from data.economic_calendar import fetch_minkabu_economic_events, split_events_for_mail

events = fetch_minkabu_economic_events()

# logic
from logic.market_calc import build_rows, summarize_sector_attention
from logic.scoring import score_market, classify_regime
from logic.signal import generate_trend_signal

# output
from output.ai_summary import generate_ai_summary
from output.html_builder import build_html
from output.mailer import send_mail
from output.csv_logger import save_daily_log, save_event_log

# utils
from utils.datetime_utils import now_jst
from utils.logging_utils import log_error


def run():
    print("===== START MARKET AI =====")

    try:
        now = now_jst()
        print(f"[INFO] now_jst = {now}")

        # =========================================
        # ① 市場データ取得
        # =========================================
        symbols = list(MARKET_SYMBOLS.values())
        sector_symbols = list(SECTOR_ETFS.values())

        print("[INFO] downloading market data...")
        market_df = download_ohlc(symbols)

        print("[INFO] downloading sector data...")
        sector_df = download_ohlc(sector_symbols)

        # =========================================
        # ② データ整形
        # =========================================
        print("[INFO] building market rows...")
        market_rows = build_rows(market_df, MARKET_SYMBOLS)

        print("[INFO] building sector rows...")
        sector_rows = build_rows(sector_df, SECTOR_ETFS)

        print("[INFO] summarizing sector attention...")
        sector_attention = summarize_sector_attention(sector_rows)

        # =========================================
        # ③ 経済指標取得（みんかぶ）
        # =========================================
        print("[INFO] fetching economic events from MINKABU...")
        events = fetch_minkabu_economic_events()

        print(f"[DEBUG] events_total = {len(events)}")

        for i, e in enumerate(events[:5], start=1):
            print(f"[DEBUG] EVENT SAMPLE {i}: {e}")

        # =========================================
        # ④ メール用分割
        # =========================================
        macro_payload = split_events_for_mail(events, now)

        print(f"[DEBUG] macro_payload_mode = {macro_payload['mode']}")
        print(f"[DEBUG] yesterday_events = {len(macro_payload['yesterday_events'])}")
        print(f"[DEBUG] today_events = {len(macro_payload['today_events'])}")
        print(f"[DEBUG] weekly_upcoming = {len(macro_payload['weekly_upcoming'])}")

        # AI・スコア用
        if macro_payload["mode"] == "monday":
            print("[INFO] monday mode detected")
            recent_events = []
            upcoming_events = macro_payload["weekly_upcoming"]
        else:
            print("[INFO] daily mode detected")
            recent_events = macro_payload["yesterday_events"]
            upcoming_events = macro_payload["today_events"]

        print(f"[INFO] recent_events = {len(recent_events)}")
        print(f"[INFO] upcoming_events = {len(upcoming_events)}")

        # サンプル確認
        for i, e in enumerate(recent_events[:3], start=1):
            print(f"[DEBUG] RECENT EVENT {i}: {e}")

        for i, e in enumerate(upcoming_events[:3], start=1):
            print(f"[DEBUG] UPCOMING EVENT {i}: {e}")

        # =========================================
        # ⑤ スコア計算
        # =========================================
        print("[INFO] scoring market...")
        score, reasons = score_market(
            market_rows,
            sector_rows,
            recent_events,
            upcoming_events,
        )

        regime = classify_regime(score)

        print(f"[INFO] score = {score}")
        print(f"[INFO] regime = {regime}")

        # =========================================
        # ⑥ シグナル生成
        # =========================================
        print("[INFO] generating trend signal...")
        signal, signal_details = generate_trend_signal(
            score,
            market_rows,
            sector_attention,
            recent_events,
            upcoming_events,
        )

        print(f"[INFO] signal = {signal}")
        print(f"[INFO] signal_details = {signal_details}")

        # =========================================
        # ⑦ AI概況生成
        # =========================================
        print("[INFO] generating ai summary...")
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
        # ⑧ HTML生成
        # =========================================
        print("[INFO] building html...")
        html = build_html(
            market_rows=market_rows,
            sector_rows=sector_rows,
            score=score,
            regime=regime,
            signal=signal,
            signal_details=signal_details,
            reasons=reasons,
            ai_summary=ai_summary,
            macro_payload=macro_payload,
        )

        # HTML保存
        print(f"[INFO] saving html to {LATEST_HTML_FILE} ...")
        with open(LATEST_HTML_FILE, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"[INFO] HTML saved to {LATEST_HTML_FILE}")

        # =========================================
        # ⑨ メール送信
        # =========================================
        print("[INFO] sending email...")
        send_mail("マーケットレポート", html)

        # =========================================
        # ⑩ ログ保存
        # =========================================
        print("[INFO] saving csv logs...")
        save_daily_log(score, regime, signal)
        save_event_log(events)

        print("===== END MARKET AI =====")

        return {
            "score": score,
            "regime": regime,
            "signal": signal,
            "event_count": len(events),
        }

    except Exception as e:
        err_msg = f"runner.py 実行エラー: {e}"
        print(f"[ERROR] {err_msg}")
        log_error(err_msg)
        raise
