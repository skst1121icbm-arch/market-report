import yfinance as yf
import pandas as pd


def download    frames = []def download_ohlc(symbols, period="5d", interval="1d"):

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

            # MultiIndex化
            df.columns = pd.MultiIndex.from_product([[symbol], df.columns])

            frames.append(df)

        except Exception as e:
            print(f"[ERROR] {symbol}: {e}")

    if not frames:
        return None

    return pd.concat(frames, axis=1)


def get_close_pair(df, symbol):

    try:
        if df is None:
            return None, None

        if not isinstance(df.columns, pd.MultiIndex):
            return None, None

        if symbol not in df.columns.get_level_values(0):
            return None, None

        closes = df[(symbol, "Close")].dropna()

        if len(closes) < 2:
            return None, None

        return float(closes.iloc[-1]), float(closes.iloc[-2])

    except Exception as e:
        print(f"[ERROR] get_close_pair {symbol}: {e}")
        return None, None

