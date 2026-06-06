import yfinance as yf
import pandas as pd


def download_ohlc(symbols, period="5d", interval="1d"):

    try:
        df = yf.download(
            tickers=" ".join(symbols),   # ←重要
            period=period,
            interval=interval,
            auto_adjust=False,
            progress=False
        )

        if df is None or df.empty:
            print("[WARN] yfinance empty")
            return None

        return df

    except Exception as e:
        print("[ERROR] yfinance:", e)
        return None


def get_close_pair(df, symbol):

    try:
        if df is None:
            return None, None

        # ✅ 複数銘柄（MultiIndex）
        if isinstance(df.columns, pd.MultiIndex):

            # ←ここを修正
            if symbol not in df.columns.get_level_values(0):
                return None, None

            closes = df[symbol]["Close"].dropna()

        # ✅ 単一銘柄
        else:
            if "Close" not in df.columns:
                return None, None

            closes = df["Close"].dropna()

        if len(closes) < 2:
            return None, None

        curr = float(closes.iloc[-1])
        prev = float(closes.iloc[-2])

        return curr, prev

    except Exception as e:
        print("[ERROR] get_close_pair:", e)
        return None, None
