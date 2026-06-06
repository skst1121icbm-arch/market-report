import yfinance as yf
import pandas as pd


def _normalize_single_ticker_columns(df):
    """
    yfinance が単一銘柄でも MultiIndex を返す場合があるため、
    いったん列名をフラット化して
    ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume'] のようにそろえる。
    """
    if df is None or df.empty:
        return df

    # すでに MultiIndex の場合
    if isinstance(df.columns, pd.MultiIndex):
        new_cols = []
        for col in df.columns:
            # 例: ('Close', '^N225') -> 'Close'
            if isinstance(col, tuple):
                new_cols.append(str(col[0]))
            else:
                new_cols.append(str(col))
        df = df.copy()
        df.columns = new_cols
        return df

    # 単純な Index の場合はそのまま
    return df


def download_ohlc(symbols, period="5d", interval="1d"):
    """
    1銘柄ずつ取得して、最後に (symbol, field) の
    2階層 MultiIndex DataFrame に結合する。
    """
    frames = []

    for symbol in symbols:
        try:
            df = yf.download(
                tickers=symbol,
                period=period,
                interval=interval,
                auto_adjust=False,
                progress=False,
                threads=False,
            )

            if df is None or df.empty:
                print(f"[WARN] empty: {symbol}")
                continue

            # ここが重要:
            # 取得直後の列を必ずフラット化
            df = _normalize_single_ticker_columns(df)

            # Close 等の基本列があるか軽く確認
            if "Close" not in df.columns:
                print(f"[WARN] no Close column: {symbol} / cols={list(df.columns)}")
                continue

            # (symbol, field) の2階層に統一
            df = df.copy()
            df.columns = pd.MultiIndex.from_tuples(
                [(symbol, col) for col in df.columns]
            )

            frames.append(df)

        except Exception as e:
            print(f"[ERROR] {symbol}: {e}")

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
    columns が (symbol, field) の2階層 MultiIndex である前提で、
    symbol の Close 直近2本を返す。
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

            key = (symbol, "Close")
            if key not in df.columns:
                return None, None

            closes = df[key].dropna()

        if len(closes) < 2:
            return None, None

        curr = float(closes.iloc[-1])
        prev = float(closes.iloc[-2])

        return curr, prev

    except Exception as e:
        print(f"[ERROR] get_close_pair {symbol}: {e}")
        return None, None
