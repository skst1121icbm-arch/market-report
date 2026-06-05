import yfinance as yf


def download_ohlc(symbols, period="5d", interval="1d"):
    return yf.download(
        tickers=symbols,
        period=period,
        interval=interval,
        auto_adjust=False,
        progress=False,
        threads=False,
        group_by="ticker",
    )


def get_close_pair(df, symbol):
    try:
        sub = df[symbol].copy()
        closes = sub["Close"].dropna()

        if len(closes) < 2:
            return None, None

        return float(closes.iloc[-1]), float(closes.iloc[-2])

    except Exception:
        return None, None
