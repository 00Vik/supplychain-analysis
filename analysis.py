import pandas as pd
import numpy as np

from config import (
    FLOW_CODE,
    ANALYSIS_MODE,
    CONCENTRATION_N,
    TOP_N,
)


# ============================================================
# 一、基础聚合函数（通用，不筛流向）
# ============================================================

def aggregate_by(df, group_cols, value_cols=("trade_value_usd", "net_weight")):
    """
    按指定维度分组聚合。所有分析的底层函数。

    df:         输入
    group_cols: 分组键列表，如 ["year", "reporter"]
    value_cols: 要聚合的数值列

    返回: 分组聚合后的 DataFrame
    """

    agg_dict = {col: "sum" for col in value_cols}

    result = (
        df.groupby(group_cols)
        .agg(agg_dict)
        .reset_index()
    )

    return result


def add_share(df, group_col, value_col="trade_value_usd", share_name="share"):
    """
    在 df 内，按 group_col 分组，算 value_col 占组内总和的比例。

    df:        输入
    group_col: 按哪列分组算份额（如 "year"）
    value_col: 份额基于哪列
    share_name: 新列名

    返回: 加了 share 列的 DataFrame
    """

    df = df.copy()

    df[share_name] = (
        df[value_col]
        / df.groupby(group_col)[value_col].transform("sum")
    )

    return df


def add_rank(df, group_col, by_col="share", rank_name="rank", ascending=False, method="min"):
    """
    在 df 内，按 group_col 分组，对 by_col 排名。

    df:         输入
    group_col:  按哪列分组排名
    by_col:     按哪列排
    rank_name:  新列名

    返回: 加了 rank 列的 DataFrame
    """

    df = df.copy()

    df[rank_name] = (
        df.groupby(group_col)[by_col]
        .rank(ascending=ascending, method=method)
    )

    return df


# ============================================================
# 二、流量分析（按当前 FLOW_CODE）
# ============================================================

def flow_summary(df, group_cols):
    """
    通用流向汇总：按 group_cols 聚合贸易额、重量，并算份额、排名。

    df:         已筛过流向的数据
    group_cols: 分组维度，如 ["year", "reporter"]

    返回: 含 trade_value_usd, net_weight, share, rank 的 DataFrame
    """

    result = aggregate_by(df, group_cols)

    result = add_share(result, group_col="year")

    result = add_rank(result, group_col="year")

    return result


def country_flow(df):
    """
    各国流量分析：按 年 + 报告国 汇总。

    输出: year, reporter, trade_value_usd, net_weight, share, rank
    """

    return flow_summary(df, group_cols=["year", "reporter"])


def partner_flow(df):
    """
    各伙伴国流量分析：按 年 + 伙伴国 汇总。

    输出: year, partner, trade_value_usd, net_weight, share, rank
    """

    return flow_summary(df, group_cols=["year", "partner"])


# ============================================================
# 三、集中度分析
# ============================================================

def concentration_ratio(df, group_col, n=5, value_col="trade_value_usd"):
    """
    集中度 CRn：按年+group_col 算份额，取前 n 名求和。

    df:        已筛流向的数据
    group_col: 按哪列算集中度（reporter 或 partner）
    n:         前 n 名
    value_col: 基于哪列

    输出: year, CR{n}
    """

    result = aggregate_by(df, ["year", group_col], value_cols=(value_col,))

    result = add_share(result, group_col="year", value_col=value_col)

    result = add_rank(result, group_col="year", by_col="share",
                       rank_name="rank", method="first")

    top = result[result["rank"] <= n]

    cr = (
        top.groupby("year")["share"]
        .sum()
        .reset_index(name=f"CR{n}")
    )

    return cr


def hhi(df, group_col, value_col="trade_value_usd"):
    """
    HHI：按年+group_col 算份额（%），平方求和。

    df:        已筛流向的数据
    group_col: 按哪列算（reporter 或 partner）
    value_col: 基于哪列

    输出: year, HHI
    """

    result = aggregate_by(df, ["year", group_col], value_cols=(value_col,))

    result["share_pct"] = (
        result[value_col]
        / result.groupby("year")[value_col].transform("sum")
        * 100
    )

    hhi_result = (
        result.groupby("year")["share_pct"]
        .apply(lambda x: (x ** 2).sum())
        .reset_index(name="HHI")
    )

    return hhi_result


# ============================================================
# 四、供应商依赖分析（进口视角）
# ============================================================

def supplier_dependency(df):
    """
    供应商依赖：按 年 + 报告国 + 伙伴国 汇总，算供应份额、排名。

    df: 已筛进口流向的数据

    输出: year, reporter, partner, trade_value_usd, share, rank
    """

    result = aggregate_by(
        df,
        ["year", "reporter", "partner"],
        value_cols=("trade_value_usd",),
    )

    result = add_share(
        result,
        group_col=["year", "reporter"],
    )

    result = add_rank(
        result,
        group_col=["year", "reporter"],
    )

    return result


def top_supplier(supplier_df, top_n=1):
    """
    取每个 年+报告国 的前 top_n 个供应商。

    输出: year, reporter, partner, trade_value_usd, share, rank
    """

    return supplier_df[supplier_df["rank"] <= top_n].copy()


def supplier_hhi(supplier_df):
    """
    供应商集中度 HHI：按 年+报告国 算供应份额平方和。

    输出: year, reporter, supplier_hhi
    """

    result = (
        supplier_df
        .groupby(["year", "reporter"])["share"]
        .apply(lambda x: (x * 100).pow(2).sum())
        .reset_index(name="supplier_hhi")
    )

    return result


def supplier_share_change(supplier_df):
    """
    供应商份额逐年变化：按 reporter+partner 排序，算 share 的差分。

    输出: 原列 + share_change
    """

    result = supplier_df.copy()

    result = result.sort_values(["reporter", "partner", "year"])

    result["share_change"] = (
        result.groupby(["reporter", "partner"])["share"].diff()
    )

    return result


# ============================================================
# 五、贸易路线
# ============================================================

def trade_routes(df):
    """
    贸易路线：按 年+报告国+伙伴国 汇总，算路线份额、排名。

    输出: year, reporter, partner, trade_value_usd, share, rank
    """

    result = aggregate_by(
        df,
        ["year", "reporter", "partner"],
        value_cols=("trade_value_usd",),
    )

    result = add_share(result, group_col="year")

    result = add_rank(result, group_col="year")

    return result


# ============================================================
# 六、单位价值
# ============================================================

def unit_trade_value(df, group_cols=("year", "reporter")):
    """
    单位价值：按 group_cols 汇总后算 USD/kg。

    df:         已筛流向的数据
    group_cols: 分组维度

    输出: group_cols + trade_value_usd, net_weight, unit_value_usd_per_kg
    """

    result = aggregate_by(df, list(group_cols))

    result["unit_value_usd_per_kg"] = (
        result["trade_value_usd"]
        / result["net_weight"].replace(0, np.nan)
    )

    return result


# ============================================================
# 七、时间趋势
# ============================================================

def time_trend(df, group_cols=("year",)):
    """
    时间趋势：按 group_cols 汇总，算同比。

    df:         已筛流向的数据
    group_cols: 分组维度（通常含 year）

    输出: group_cols + trade_value_usd, net_weight, trade_value_yoy, weight_yoy
    """

    result = aggregate_by(df, list(group_cols))

    result = result.sort_values(list(group_cols))

    result["trade_value_yoy"] = (
        result["trade_value_usd"].pct_change()
    )

    result["weight_yoy"] = (
        result["net_weight"].pct_change()
    )

    return result


# ============================================================
# 九、模式判断
# ============================================================

def detect_mode(df):
    """
    从数据推断分析模式。
    reporter 1 个、partner 多个 → A
    partner 1 个、reporter 多个 → B
    其余情况抛错。
    """
    n_reporter = df["reporter"].nunique()
    n_partner = df["partner"].nunique()

    if n_reporter == 1 and n_partner > 1:
        return "A"
    if n_partner == 1 and n_reporter > 1:
        return "B"
    raise ValueError(
        f"无法判断模式：reporter={n_reporter} 个，partner={n_partner} 个"
    )

def resolve_mode(df):
    """
    确定分析模式：
    config 指定 A/B 则强制用；
    config 为 auto 则从数据判断。
    """
    if ANALYSIS_MODE != "auto":
        return ANALYSIS_MODE
    return detect_mode(df)


# ============================================================
# 十、调度
# ============================================================

def run_analysis(df):
    """
    按 FLOW_CODE + ANALYSIS_MODE 调度所有分析。

    df: 已清洗的完整数据（含 X、M 两个流向）
    """

    results = {}

    # ---------- 筛当前流向 ----------
    flow_df = df[df["flow_code"] == FLOW_CODE].copy()

    # ---------- 筛当前模式 ----------
    mode = resolve_mode(flow_df)
    print(f"检测到分析模式：{mode}")

    # ---------- 通用分析 ----------
    results["time_trend"] = time_trend(flow_df)

    results["trade_routes"] = trade_routes(flow_df)

    results["unit_values"] = unit_trade_value(flow_df)

    # ---------- 按模式选集中度分组键 ----------
    if mode == "A":
        group_col = "partner"
    else:
        group_col = "reporter"

    for n in CONCENTRATION_N:
        results[f"cr{n}"] = concentration_ratio(
            flow_df, group_col=group_col, n=n
        )

    results["hhi"] = hhi(flow_df, group_col=group_col)

    # ---------- 模式相关 ----------
    if ANALYSIS_MODE == "B":
        # 各国对比
        results["country_flow"] = country_flow(flow_df)

    if ANALYSIS_MODE == "A":
        # 伙伴国视角
        results["partner_flow"] = partner_flow(flow_df)

        # 供应商依赖仅进口有意义
        if FLOW_CODE == "M":
            suppliers = supplier_dependency(flow_df)
            results["supplier_dependency"] = suppliers
            results["top_supplier"] = top_supplier(suppliers, top_n=TOP_N)
            results["supplier_hhi"] = supplier_hhi(suppliers)
            results["supplier_changes"] = supplier_share_change(suppliers)

    return results


def save_results(results, out_dir):

    out_dir.mkdir(parents=True, exist_ok=True)

    for name, df in results.items():
        df.to_csv(
            out_dir / f"{name}.csv",
            index=False,
            encoding="utf-8-sig",
        )
        print(f"Saved: {out_dir / f'{name}.csv'}")