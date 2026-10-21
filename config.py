from pathlib import Path


# ============================================================
# 项目路径
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUT_DIR = DATA_DIR / "output"

for directory in [RAW_DIR, PROCESSED_DIR, OUTPUT_DIR]:
    directory.mkdir(parents=True, exist_ok=True)


# ============================================================
# 项目参数
# ============================================================

PROJECT_NAME = "pv_supply_chain"


# ========================================================================================================================
# 产品配置
#
# 注意：
# 这里的 HS code 必须与你实际采用的 HS 版本一致。
# 不同 HS 版本不能直接混用。

PRODUCTS = {

    "pv": {
        "name": "Photovoltaic",
        "hs_version": "HS2022",

        # 示例：
        # 这里保留两个品类，底层数据分开。
        "hs_codes": [
            "854142",
            "854143",
        ],

        "stages": {
            "854142": "cell",
            "854143": "module",
        }
    },

    "ev_battery": {
        "name": "Lithium-ion Accumulator",
        "hs_version": "HS2022",

        "hs_codes": [
            "850760",
        ],

        "stages": {
            "850760": "battery",
        }
    }
}

# ============================================================
# 当前运行产品
PRODUCT_KEY = "pv"

PRODUCT_CONFIG = PRODUCTS[PRODUCT_KEY]

HS_CODES = PRODUCT_CONFIG["hs_codes"]
HS_VERSION = PRODUCT_CONFIG["hs_version"]

# ============================================================
# 分析对象
REPORTER_NAMES = {"China": 156}

# ============================================================
# 分析模式
ANALYSIS_MODE = "auto" 

# ============================================================
# 时间范围
START_YEAR = 2022
END_YEAR = 2025

# ============================================================
# 运输方式
MOT_CODE = "0" 

# ============================================================
# 进出口
FLOW_CODE = "X"

# ============================================================
# 伙伴国
PARTNER_CODE =  None

# ============================================================
# 第二伙伴国
PARTNER2_CODE = "0"

# ============================================================
# 海关程序代码
CUSTOMS_CODE = "C00"

# ============================================================
# 每次请求的记录数
MAX_RECORDS = 500

# ============================================================
# 字段映射
# ============================================================

COLUMN_MAPPING = {

    "period": "year",

    "reporterCode": "reporter_code",
    "reporterDesc": "reporter",

    "partnerCode": "partner_code",
    "partnerDesc": "partner",

    "cmdCode": "hs_code",
    "cmdDesc": "product_description",

    "flowCode": "flow_code",
    "flowDesc": "flow",

    "primaryValue": "trade_value_usd",

    "netWgt": "net_weight",

    "qty": "quantity",

    "qtyUnitCode": "quantity_unit_code",
    "qtyUnitAbbr": "quantity_unit",

    "motCode": "mot_code",
    "customsCode": "customs_code",
}


# ============================================================
# 需要检查的列
# ============================================================

# 数字列
NUMERIC_COLUMNS = [
    "year",
    "trade_value_usd",
    "net_weight",
    "quantity",
]

  
# 字符串列
STRING_COLUMNS = [
    "reporter",
    "partner",
] 

# 标识符代码列
CODE_COLUMNS = [
    "reporter_code",
    "partner_code",
    "hs_code",
    "flow_code",
    "quantity_unit_code",
    "mot_code",
    "customs_code",
]

# 代码类型映射
RAW_CODE_DTYPES = {
    "reporterCode": str,
    "partnerCode": str,
    "cmdCode": str,
    "flowCode": str,
    "qtyUnitCode": str,
    "motCode": str,
    "customsCode": str,
}

# 视为"伪缺失"的字符串（不区分大小写）
FAKE_MISSING = {
    "", "n/a", "na", "-", "--",
    "null", "none", "nan",
    "unknown", "#", "?",}

# ============================================================
# 数量单位映射（Comtrade qtyUnitCode → 单位名）
# ============================================================

QTY_UNIT_MAP = {
    "-1": "unknown",
    "1": "no_quantity",
    "2": "items",
    "3": "pairs",
    "4": "dozens",
    "5": "kg",
    "6": "packages",
    "8": "litres",
    "9": "m3",
    "10": "meters",
    "11": "m2",
    "12": "carats",
    "13": "tonnes",
    "14": "GBq",
}

# ============================================================
# 去重列
# ============================================================

duplicate_columns = [
    "year",
    "reporter_code",
    "partner_code",
    "hs_code",
    "flow_code",
    "mot_code"
    ]

# ============================================================
# Comtrade
# ============================================================

COMTRADE_BASE_URL = (
    "https://comtradeapi.un.org/public/v1/preview/C/A/HS"
)

# 每次请求间隔
REQUEST_SLEEP = 1.5
REQUEST_MAX_RETRIES = 3     # 429 重试次数

# ============================================================
# 数据库
# ============================================================

DATABASE_PATH = DATA_DIR / "supply_chain.db"

# ============================================================
# 分析参数
# ============================================================

TOP_N = 20
CONCENTRATION_N = [3, 5]