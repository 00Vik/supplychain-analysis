import pandas as pd
import numpy as np
from pandas.api.types import is_object_dtype, is_categorical_dtype
from config import (
    RAW_DIR,
    PROCESSED_DIR,
    PRODUCT_CONFIG,
    COLUMN_MAPPING,
    NUMERIC_COLUMNS,
    STRING_COLUMNS,
    CODE_COLUMNS,
    QTY_UNIT_MAP,
    RAW_CODE_DTYPES,
    FAKE_MISSING,
    START_YEAR,
    END_YEAR,
    duplicate_columns,
)

# ============================================================
# 必需列检查
# ============================================================
def check_required_columns(df, required):
    """一次性检查必需列，缺任意一列直接抛错。"""
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"缺少必需列：{missing}")

# ============================================================
# 全列空值检查
# ============================================================
def check_empty_columns(df, columns):
    """检查指定列是否整列为空，有空列则抛错中断。"""

    empty_cols = []

    for col in columns:
        if col not in df.columns:
            continue
        # 整列全是 NaN / 空串
        if df[col].isna().all():
            empty_cols.append(col)

    if empty_cols:
        raise ValueError(
            f"以下列整列为空，无法继续：{empty_cols}"
        )

# ============================================================
# 提取脏数字行
# ============================================================

def extract_dirty_numeric(df, columns=NUMERIC_COLUMNS):
    """
    找出数字列里"空值、无法转成数字、负值"的行。

    返回:
        dirty_df   : 脏数据明细（每行标明哪列、原值是什么）
        dirty_mask : 布尔 Series，True 表示该行是脏的
    """

    dirty_mask = pd.Series(False, index=df.index)
    records = []

    for col in columns:

        s = df[col]
        converted = pd.to_numeric(s, errors="coerce")

        # 三类脏数据类型
        is_missing = s.isna()                          # 原本就空
        is_non_numeric = s.notna() & converted.isna()  # 有值但转不了
        is_negative = converted.notna() & (converted < 0)  # 负值

        bad_mask = is_missing | is_non_numeric | is_negative


        if bad_mask.any():

            dirty_mask |= bad_mask

            bad_df = df.loc[bad_mask].copy()
            bad_df["bad_column"] = col
            bad_df["bad_value"] = s.loc[bad_mask].astype(str)

            bad_df["bad_type"] = np.select(
                [
                    is_negative.loc[bad_mask],
                    is_non_numeric.loc[bad_mask],
                    is_missing.loc[bad_mask],
                ],
                [
                    "negative",
                    "non_numeric",
                    "is_missing",
                ],
                default="unknown",
            )

            records.append(bad_df)

    dirty_df = pd.concat(records, ignore_index=True) if records else pd.DataFrame()

    return dirty_df, dirty_mask

# ============================================================
# 年份检查
# ============================================================
def extract_dirty_year(df, col="year"):

    if col not in df.columns:
        return pd.DataFrame(), pd.Series(False, index=df.index)

    s = df[col]
    converted = pd.to_numeric(s, errors="coerce")

    is_out_of_range = converted.notna() & (
        (converted < START_YEAR) | (converted > END_YEAR)
    )
    is_not_integer = converted.notna() & (converted % 1 != 0)

    bad_mask = is_out_of_range | is_not_integer

    if not bad_mask.any():
        return pd.DataFrame(), pd.Series(False, index=df.index)

    bad_df = df.loc[bad_mask].copy()
    bad_df["bad_column"] = col
    bad_df["bad_value"] = s.loc[bad_mask].astype(str)
    bad_df["bad_type"] = np.select(
        [
            is_out_of_range.loc[bad_mask],
            is_not_integer.loc[bad_mask],
        ],
        ["out_of_range", "not_integer"],
        default="unknown",
    )

    return bad_df, bad_mask

# ============================================================
# 提取脏代码行
# ============================================================
def extract_dirty_code(df, columns=CODE_COLUMNS):

    dirty_mask = pd.Series(False, index=df.index)
    records = []

    for col in columns:

        s = df[col]

        # 统一转字符串、去缺失值、转小写
        s_str = s.astype("string")
        s_stripped = s_str.str.strip()
        s_lowered = s_stripped.str.lower()


        # 各类脏数据
        is_missing = s.isna()                                                    # 缺失值标记
        is_fake_missing = s.notna() & s_lowered.isin(FAKE_MISSING)               # 伪缺失标记
        has_dot_zero = s_stripped.str.contains(r"\.0$", regex=True, na=False)    # float格式标记

        # hs_code 额外判长度
        if col == "hs_code":
            wrong_length = (
                s.notna()
                & ~is_fake_missing
                & (s_stripped.str.len() != 6)
            )
        else:
            wrong_length = pd.Series(False, index=df.index)

        bad_mask = (
            is_missing
            | is_fake_missing
            | has_dot_zero
            | wrong_length
        )

        if bad_mask.any():

            dirty_mask |= bad_mask

            bad_df = df.loc[bad_mask].copy()
            bad_df["bad_column"] = col
            bad_df["bad_value"] = s.loc[bad_mask].astype(str)

            bad_df["bad_type"] = np.select(
                [
                    is_missing.loc[bad_mask],
                    is_fake_missing.loc[bad_mask],
                    has_dot_zero.loc[bad_mask],
                    wrong_length.loc[bad_mask],
                ],
                [
                    "is_missing",
                    "fake_missing",
                    "has_dot_zero",
                    "wrong_length",
                ],
                default="unknown",
            )

            records.append(bad_df)

    dirty_df = pd.concat(records, ignore_index=True) if records else pd.DataFrame()

    return dirty_df, dirty_mask

# ============================================================
# 提取脏字符串行
# ============================================================

def extract_dirty_string(df, columns=STRING_COLUMNS):
    """
    找出数字列里"空字符串、常见伪缺失标记、常见伪缺失标记、前后有多余空白"的行。

    返回:
        dirty_df   : 脏数据明细（每行标明哪列、原值是什么）
        dirty_mask : 布尔 Series，True 表示该行是脏的
    """

    dirty_mask = pd.Series(False, index=df.index)
    records = []


    for col in columns:

        s = df[col]

    # 只处理字符串/object/category 列
        if not (is_object_dtype(s)
            or isinstance(s.dtype, pd.StringDtype)
            or is_categorical_dtype(s)):
            continue

        # 统一转字符串、去缺失值、转小写
        s_str = s.astype(str)                     
        s_stripped = s_str.str.strip()
        s_lowered = s_stripped.str.lower()

        # 缺失值标记
        is_missing = s.isna()
        
        # 伪缺失标记
        is_fake_missing = s.notna() & s_lowered.isin(FAKE_MISSING)

        bad_mask = is_missing | is_fake_missing

        if bad_mask.any():

            dirty_mask |= bad_mask

            bad_df = df.loc[bad_mask].copy()
            bad_df["bad_column"] = col
            bad_df["bad_value"] = s.loc[bad_mask].astype(str)

            # 标记脏数据类型
            bad_df["bad_type"] = np.where(
                is_missing.loc[bad_mask],
                "is_missing",
                "fake_missing",
            )

            records.append(bad_df)

    dirty_df = pd.concat(records, ignore_index=True) if records else pd.DataFrame()

    return dirty_df, dirty_mask

# ============================================================
# 国家字符串映射
# ============================================================

def map_country_names(df):
    """把 reporter_code / partner_code 映射成国家名。
    映射不中的直接跳过（置空），不中断。
    """
    ref = pd.read_csv(RAW_DIR / "partner_codes.csv", dtype=str)
    id_to_name = dict(zip(ref["id"], ref["text"]))

    for code_col, name_col in [
        ("reporter_code", "reporter"),
        ("partner_code", "partner"),
    ]:
        
        codes = df[code_col]

        mapped = codes.map(id_to_name)

        # 映射不中的，直接置空，不中断
        unmapped_mask = mapped.isna()
        if unmapped_mask.any():
            bad = codes[unmapped_mask].unique()
            print(
                f"[跳过] {code_col} 有 {unmapped_mask.sum()} 行映射不上，"
                f"未知代码：{bad[:5]}"
            )
            mapped = mapped.fillna("")   # 置空

        df[name_col] = mapped

    return df

# ============================================================
# 单位映射
# ============================================================

def map_quantity_unit(df):
    """把 quantity_unit_code 映射成单位名。
    """
    codes = df["quantity_unit_code"]

    mapped = codes.map(QTY_UNIT_MAP)

    unmapped_mask = mapped.isna()
    if unmapped_mask.any():
        bad = codes[unmapped_mask].unique()
        raise ValueError(
            f"quantity_unit_code 存在未映射的代码，共 {unmapped_mask.sum()} 行，"
            f"未知代码：{bad[:5]}"
        )

    df["quantity_unit"] = mapped
    return df

# ============================================================
# 保存脏数据
# ============================================================

def save_dirty_data(dirty_df, output_path):

    dirty_df.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig",
    )
    
    print(f"Dirty rows saved: {output_path}  (rows={len(dirty_df)})")

# ============================================================
# 清洗主程序
# ============================================================

def clean_trade_data(df: pd.DataFrame):

    df = df.copy()

    # --------------------------------------------------------
    # 字段统一
    # --------------------------------------------------------

    rename_dict = {
        old: new
        for old, new in COLUMN_MAPPING.items()
        if old in df.columns
    }

    df = df.rename(columns=rename_dict)

    # --------------------------------------------------------
    # 必需列检查
    # --------------------------------------------------------

    all_check_columns = (
        NUMERIC_COLUMNS
        + STRING_COLUMNS
        + CODE_COLUMNS
    )

    check_required_columns(df, all_check_columns)

    # --------------------------------------------------------
    # 数字列和代码列全列空值检查
    # --------------------------------------------------------

    num_code_colums = (
        NUMERIC_COLUMNS
        + CODE_COLUMNS
    )

    check_empty_columns(df, num_code_colums)

    # --------------------------------------------------------
    # 处理脏数据
    # --------------------------------------------------------

    # 代码挑脏
    dirty_code_df, dirty_code_mask = extract_dirty_code(df)
    
    # 国家字符串映射
    df = map_country_names(df)
        
    # 单位映射
    df = map_quantity_unit(df)

    # 数字挑脏
    dirty_num_df, dirty_num_mask = extract_dirty_numeric(df)

    # 年份检查
    dirty_year_df, dirty_year_mask = extract_dirty_year(df)

    # 字符串挑脏
    dirty_str_df, dirty_str_mask = extract_dirty_string(df)
    

    # 生成脏数据总表
    dirty_all = pd.concat(
        [dirty_num_df, dirty_year_df, dirty_str_df, dirty_code_df],
        ignore_index=True,
    )

    # 四类 mask 合并，一次性剔行
    dirty_mask = dirty_code_mask | dirty_num_mask | dirty_str_mask |dirty_year_mask
    df = df[~dirty_mask].copy()


    # --------------------------------------------------------
    # 产品阶段
    # --------------------------------------------------------

    stage_mapping = PRODUCT_CONFIG["stages"]

    df["stage"] = (
        df["hs_code"]
        .map(stage_mapping)
        .fillna("unknown")
    )

    # --------------------------------------------------------
    # 去重
    # --------------------------------------------------------

    subset_columns = [
        c for c in duplicate_columns
        if c in df.columns
    ]

    if subset_columns:
        df = df.drop_duplicates(
            subset=subset_columns
        )

    # --------------------------------------------------------
    # 单位贸易价值
    # --------------------------------------------------------

    df["unit_value_usd_per_kg"] = np.where(
        df["net_weight"] > 0,
        df["trade_value_usd"] / df["net_weight"],
        np.nan
    )

    # --------------------------------------------------------
    # 最终排序
    # --------------------------------------------------------

    df = df.sort_values(
        [
            "year",
            "reporter",
            "partner",
        ]
    )

    return dirty_all, df

# ============================================================
# 保存
# ============================================================

def save_clean_data(df, output_path):

    df.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig",
    )

    print(
        f"Clean data saved to: {output_path}"
    )

# ============================================================
# 最终目标目录清洗
# ============================================================
def clean_one(raw_path, out_dir):
    df = pd.read_csv(raw_path, dtype=RAW_CODE_DTYPES)

    dirty_df, clean_df = clean_trade_data(df)

    out_dir.mkdir(parents=True, exist_ok=True)
    save_dirty_data(dirty_df, out_dir / "dirty_data.csv")
    save_clean_data(clean_df, out_dir / "trade_clean.csv")
