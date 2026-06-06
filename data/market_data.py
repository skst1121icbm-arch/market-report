import yfinance as yf
_ohlc(symbols, period="5d", interval="1d"):import pandas as pd
    try:
        df = yf.download(
            tickers=symbols,
            period=period,
            interval=interval,
            auto_adjust=False,
            progress=False,
            threads=False,
        )

        if df is None or len(df) == 0:
            print("[WARN] yfinance returned empty")
            return None

        return df

    except Exception as e:
        print("[ERROR] yfinance failed:", e)
        return None


def get_close_pair(df, symbol):
    """
    yfinance.download() は
    - 複数銘柄: MultiIndex columns
    - 単一銘柄: SingleIndex columns
    の両パターンがあるため両対応
    """
    try:
        if df is None:
            return None, None

        if isinstance(df.columns, pd.MultiIndex):
            if symbol not in df.columns.get_level_values(0):
                return None, None

            closes = df[symbol]["Close"].dropna()
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


