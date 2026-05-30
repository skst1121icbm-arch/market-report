import yfinance as yf

SYMBOLS = {
    "日経平均": "^N225",
    "NASDAQ": "^IXIC",
    "S&P500": "^GSPC",
    "VIX": "^VIX",
    "GOLD": "GC=F",
    "BTC": "BTC-USD",
}

def get_data():
    for name, symbol in SYMBOLS.items():
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="2d")

        if len(data) < 2:
            print(f"{name}: データ不足")
            continue

        curr = data["Close"].iloc[-1]
        prev = data["Close"].iloc[-2]

        change = (curr - prev) / prev * 100
        print(f"{name}: {curr:.2f} ({change:.2f}%)")

if __name__ == "__main__":
    get_data()
