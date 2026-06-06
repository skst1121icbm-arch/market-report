import yfinance as yf
import pandas as pd


def download_ohlc(symbols, period="5d", interval="1d"):

    frames = []

    for symbol in symbols:
        try:
            df = yf.download(
                tickers=symbol,
                period=period,
                interval=interval,
                auto_adjust=False,
                progress=False
            )

            if df is None or df.empty:
                print(f"[WARN] empty: {symbol}")
                continue

            # MultiIndex 化
            df.columns = pd.MultiIndex.from_product([[symbol], df.columns])

            frames.append(df)

        except Exception as e:
            print(f"[ERROR] {symbol}: {e}")

    if not frames:
        return None

    merged = pd.concat(frames, axis=1)
    return merged


def get_close_pair(df, symbol):

    try:
        if df is None:
            return None, None

        if not isinstance(df.columns, pd.MultiIndex):
            return None, None

        # symbol存在チェック
        if symbol not in df.columns.get_level_values(0):
            return None, None

        closes = df[(symbol, "Close")].dropna()

        if len(closes) < 2:
            return None, None

        curr = float(closes.iloc[-1])
        prev = float(closes.iloc[-2])

        return curr, prev

    except Exception as e:
        print(f"[ERROR] get_close_pair {symbol}: {e}")
        return None, None