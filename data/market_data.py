import yfinance as yf
import pandas as pd


def download_ohlc(symbols, period="5d", interval="1d"):

    try:
        df = yf.download(
            tickers=" ".join(symbols),   # ← 重要変更
            period=period,
            interval=interval,
            auto_adjust=False,
            progress=False
        )

        # ✅ 空チェック
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

        # ✅ MultiIndex（複数銘柄）
        if isinstance(df.columns, pd.MultiIndex):

            if symbol not in df.columns.levels[0]:
                return None, None

            closes = df[symbol]["Close"].dropna()

        # ✅ fallback
        else:
            closes = df["Close"].dropna()

        if len(closes) < 2:
            return None, None

        return float(closes.iloc[-1]), float(closes.iloc[-2])

    except Exception:
        return None, None
