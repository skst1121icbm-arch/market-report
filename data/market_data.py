import yfinance as yf
import pandas as pd


def download_ohlc(symbol df = yf.download(def download_ohlc(symbols, period="5d", interval="1d"):
                tickers=symbol,
                period=period,
                interval=interval,
                auto_adjust=False,
                progress=False,
                threads=False,
            )

            if df is None or df.empty:
                print(f"[WARN] yfinance returned empty for {symbol}")
                continue

            # 列を MultiIndex 化: (symbol, field)
            if not isinstance(df.columns, pd.MultiIndex):
                df.columns = pd.MultiIndex.from_product([[symbol], df.columns])

            frames.append(df)

        except Exception as e:
            print(f"[ERROR] yfinance failed for {symbol}: {e}")

    if not frames:
        print("[WARN] download_ohlc: no symbols fetched")
        return None

    try:
        merged = pd.concat(frames, axis=1)
        return merged
    except Exception as e:
        print(f"[ERROR] concat failed: {e}")
        return None


def get_close_pair(df, symbol):
    """
    MultiIndex前提:
      columns -> (symbol, field)
    から Close の直近2本を返す
    """
    try:
        if df is None or df.empty:
            return None, None

        if not isinstance(df.columns, pd.MultiIndex):
            # 念のため単一構造 fallback
            if "Close" not in df.columns:
                return None, None
            closes = df["Close"].dropna()
        else:
            top_level = df.columns.get_level_values(0)
            if symbol not in top_level:
                return None, None

            if (symbol, "Close") in df.columns:
                closes = df[(symbol, "Close")].dropna()
            else:
                # 念のため symbol配下から Close を探す
                sub = df[symbol]
                if "Close" not in sub.columns:
                    return None, None
                closes = sub["Close"].dropna()

        if len(closes) < 2:
            return None, None

        curr = float(closes.iloc[-1])
        prev = float(closes.iloc[-2])

        return curr, prev

    except Exception as e:
        print(f"[ERROR] get_close_pair failed for {symbol}: {e}")
        return None, None
    """
    1銘柄ずつ取得して、最後に MultiIndex DataFrame に結合する。
    GitHub Actions / yfinance の不安定さ対策。
    """
    frames = []

    for symbol in symbols:
        try:
