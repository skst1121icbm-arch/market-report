import yfinance as yf
import pandas as pd


def download_ohlc(symbols, period="5d", interval="1d"):
    return yf.download(
        tickers=symbols,
        period=period,
        interval=interval,
        auto_adjust=False,
        progress=False,
        threads=False,
    )


def get_close_pair(df, symbol):
    """
    yfinance.download() の戻り値は、
    - 複数銘柄: MultiIndex columns
    - 単一銘柄: SingleIndex columns
    になることがあるので両対応する
    """
    try:
        if df is None or len(df) == 0:
            return None, None

        # MultiIndex（複数銘柄）
        if isinstance(df.columns, pd.MultiIndex):
            if symbol not in df.columns.get_level_values(0):
                return None, None

            closes = df[symbol]["Close"].dropna()

        # SingleIndex（単一銘柄）
        else:
            if "Close" not in df.columns:
                return None, None

            closes = df["Close"].dropna()

        if len(closes) < 2:
            return None, None

        curr = float(closes.iloc[-1])
        prev = float(closes.iloc[-2])

        return curr, prev

    except Exception:
        return None, None
