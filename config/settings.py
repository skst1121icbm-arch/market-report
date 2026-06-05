from datetime import timezone, timedelta

# =========================================================
# タイムゾーン
# =========================================================
JST = timezone(timedelta(hours=9))

# =========================================================
# 市場シンボル
# =========================================================
# 注:
# - Russell2000 は Yahoo Finance の ^RUT を採用
# - 米2年債利回りは Yahoo 側より FRED(DGS2) のほうが安定しやすいため、
#   MARKET_SYMBOLS には入れず FRED_SERIES_IDS で定義
# - DXY は Yahoo 環境差が出る可能性があるため、必要に応じて調整してください
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
    "DXY": "DX-Y.NYB",      # 環境によっては要調整
    "USD/JPY": "USDJPY=X",
    "EUR/USD": "EURUSD=X",

    # コモディティ
    "WTI原油": "CL=F",
    "ゴールド": "GC=F",
    "銅": "HG=F",

    # 参考で残す
    "BTC (USD)": "BTC-USD",
}

# =========================================================
# セクターETF
# =========================================================
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

# =========================================================
# FRED API
# =========================================================
FRED_BASE_URL = "https://api.stlouisfed.org/fred"

# 米2年債利回り・実質金利など
FRED_SERIES_IDS = {
    "米2年債利回り": "DGS2",
    "実質金利(10Y)": "DFII10",
}

# =========================================================
# Economic Calendar / Event Source
# =========================================================
# みんかぶの経済指標ページを利用
MINKABU_INDICATORS_URL = "https://fx.minkabu.jp/indicators"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://fx.minkabu.jp/",
}

# =========================================================
# ファイル設定
# =========================================================
DAILY_LOG_FILE = "market_ai_daily_log.csv"
EVENT_LOG_FILE = "market_ai_event_log.csv"
ERROR_LOG_FILE = "market_ai_error.log"
LATEST_HTML_FILE = "market_ai_latest_report.html"

# =========================================================
# Daily Market Checklist 表示設定
# =========================================================
CHECKLIST_THEME_CANDIDATES = [
    "AI",
    "データセンター",
    "半導体",
    "エネルギー",
    "ドローン",
    "インフラ",
    "通信",
]

VIX_STATE_RULES = {
    "low": (10, 15, "低ボラ（強気）"),
    "mid": (15, 20, "中立"),
    "high": (20, 999, "リスク警戒"),
}

# Breadth / Flow / Options
# いまは本番ソース未接続のため、HTMLでは「未取得」表示できるようにする
ENABLE_BREADTH = True
ENABLE_ETF_FLOWS = True
ENABLE_OPTIONS_DATA = True
