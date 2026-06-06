from datetime import timezone, timedelta

# タイムゾーン
JST = timezone(timedelta(hours=9))

# 市場シンボル
MARKET_SYMBOLS = {
    "日経平均": "^N225",
    "NYダウ": "^DJI",
    "NASDAQ": "^IXIC",
    "S&P500": "^GSPC",
    "Russell2000": "^RUT",
    "VIX": "^VIX",

    # 金利
    "米10年金利": "^TNX",

    # 為替
    "DXY": "DX-Y.NYB",
    "USD/JPY": "USDJPY=X",
    "EUR/USD": "EURUSD=X",

    # コモディティ
    "WTI原油": "CL=F",
    "ゴールド": "GC=F",
    "銅": "HG=F",
    
    # 仮想通貨
    "BTC (USD)": "BTC-USD",
    "ETH (USD)": "ETH-USD",
    "XRP (USD)": "XRP-USD",
    "SOL (USD)": "SOL-USD",
    
}

SECTOR_ETFS = {
    "テクノロジー": "XLK",
    "金融": "XLF",
    "ヘルスケア": "XLV",
    "一般消費": "XLY",
    "生活必需": "XLP",
    "資本財": "XLI",
    "エネルギー": "XLE",
    "素材": "XLB",
    "通信": "XLC",
    "公益": "XLU",
    "不動産": "XLRE",
}

# FRED
FRED_BASE_URL = "https://api.stlouisfed.org/fred"
FRED_SERIES_IDS = {
    "米2年債利回り": "DGS2",
    "実質金利(10Y)": "DFII10",
}

# ファイル設定
DAILY_LOG_FILE = "market_ai_daily_log.csv"
EVENT_LOG_FILE = "market_ai_event_log.csv"
ERROR_LOG_FILE = "market_ai_error.log"
LATEST_HTML_FILE = "market_ai_latest_report.html"
