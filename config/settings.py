from datetime import timezone, timedelta

# =========================================================
# タイムゾーン
# =========================================================

JST = timezone(timedelta(hours=9))

# =========================================================
# 市場シンボル
# =========================================================

MARKET_SYMBOLS = {
    "日経平均": "^N225",
    "NYダウ": "^DJI",
    "NASDAQ": "^IXIC",
    "S&P500": "^GSPC",
    "VIX": "^VIX",
    "米10年金利": "^TNX",
    "GOLD (USD)": "GC=F",
    "BTC (USD)": "BTC-USD",
    "USD/JPY": "USDJPY=X",
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

# =========================================================
# FRED API
# =========================================================

FRED_BASE_URL = "https://api.stlouisfed.org/fred"

# 重要イベント
MAJOR_RELEASE_KEYWORDS = [
    "Consumer Price Index",
    "Gross Domestic Product",
    "Employment Situation",
    "Producer Price Index",
    "Retail Sales",
    "Industrial Production",
    "Personal Income and Outlays",
    "Advance Monthly Sales for Retail and Food Services",
    "Employment Cost Index",
    "Unemployment",
    "Job Openings and Labor Turnover",
    "Housing Starts",
    "New Residential Sales",
    "Existing Home Sales",
    "Initial Claims",
    "Selected Interest Rates",
]

# release → seriesマッピング
US_RELEASE_SERIES_MAP = {
    "Consumer Price Index": {
        "series_id": "CPIAUCSL",
        "result_label": "CPI",
    },
    "Gross Domestic Product": {
        "series_id": "A191RL1Q225SBEA",
        "result_label": "GDP",
    },
    "Employment Situation": {
        "series_id": "PAYEMS",
        "result_label": "非農業部門雇用者数",
    },
    "Producer Price Index": {
        "series_id": "PPIACO",
        "result_label": "PPI",
    },
    "Retail Sales": {
        "series_id": "RSAFS",
        "result_label": "小売売上高",
    },
    "Advance Monthly Sales for Retail and Food Services": {
        "series_id": "RSAFS",
        "result_label": "小売売上高",
    },
    "Industrial Production": {
        "series_id": "INDPRO",
        "result_label": "鉱工業生産",
    },
    "Unemployment": {
        "series_id": "UNRATE",
        "result_label": "失業率",
    },
    "Job Openings and Labor Turnover": {
        "series_id": "JTSJOL",
        "result_label": "JOLTS求人件数",
    },
    "Initial Claims": {
        "series_id": "ICSA",
        "result_label": "新規失業保険申請件数",
    },
    "Personal Income and Outlays": {
        "series_id": "PCE",
        "result_label": "PCE",
    },
}

# =========================================================
# ファイル設定
# =========================================================

DAILY_LOG_FILE = "market_ai_daily_log.csv"
EVENT_LOG_FILE = "market_ai_event_log.csv"
ERROR_LOG_FILE = "market_ai_error.log"
LATEST_HTML_FILE = "market_ai_latest_report.html"
EXCEL_CALENDAR_FILE = "schedule.xlsx"