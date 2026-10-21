import time
import requests
import pandas as pd

from reference import fetch_partner_codes

from config import (
    COMTRADE_BASE_URL,
    START_YEAR,
    END_YEAR,
    HS_CODES,
    RAW_DIR,
    PROCESSED_DIR,
    REPORTER_NAMES,
    REQUEST_SLEEP,
    REQUEST_MAX_RETRIES,
    MOT_CODE,
    FLOW_CODE,
    PARTNER_CODE,
    PARTNER2_CODE,
    CUSTOMS_CODE,
    MAX_RECORDS,

)

# ============================================================
# 伙伴国列表
# ============================================================
partner_df = fetch_partner_codes()
partner_codes = partner_df["id"].tolist()

# ============================================================
# 请求函数
# ============================================================

def request_comtrade(
    reporter_code: str,
    period: int,
    cmd_code: str,
    flow_code: str = FLOW_CODE,
    partner_code: str = PARTNER_CODE,
    partner_2code: str = PARTNER2_CODE,
    customs_code: str = CUSTOMS_CODE,
    mot_code: str = MOT_CODE,
    max_records: int = MAX_RECORDS,
):
    """
    从 UN Comtrade 获取数据。

    reporter_code:
        报告国代码

    period:
        年份

    cmd_code:
        HS 6位编码

    flow_code:
        X = Export
        M = Import

    partner_code:
        all = 所有伙伴国
    """

    params = {
        "reporterCode": reporter_code,
        "period": period,
        "cmdCode": cmd_code,
        "flowCode": flow_code,
        "partnerCode": partner_code,
        "partner2Code": partner_2code,
        "customsCode": customs_code,
        "motCode": mot_code,
        "maxRecords": max_records,
    }

    for attempt in range(REQUEST_MAX_RETRIES):

        try:
            response = requests.get(
                COMTRADE_BASE_URL,
                params=params,
                timeout=60,
            )

            # 429 / 5xx → 等一会儿重试
            if response.status_code in (429, 500, 502, 503, 504):
                wait = 5 * (attempt + 1)
                print(f"  {response.status_code}, 等待 {wait}s 重试...")
                time.sleep(wait)
                continue

            response.raise_for_status()

            data = response.json()

            if "data" not in data:
                return pd.DataFrame()

            return pd.DataFrame(data["data"])

        except requests.exceptions.RequestException as e:
            wait = 5 * (attempt + 1)
            print(f"  请求异常，{wait}s 后重试：{e}")
            time.sleep(wait)

    # 重试耗尽
    print(f"  重试 {REQUEST_MAX_RETRIES} 次仍失败，放弃")
    return pd.DataFrame()



# ============================================================
# 下载一个产品
# ============================================================

def download_product(
    reporter_code: str,
    product_code: str,
    start_year: int = START_YEAR,
    end_year: int = END_YEAR,
):
    """
    下载指定报告国、产品、年份的数据。
    """

    frames = []

    for year in range(start_year, end_year + 1):

        print(
            f"Downloading: "
            f"reporter={reporter_code}, "
            f"HS={product_code}, "
            f"year={year}"
        )

        for flow in ["X", "M"]:

            try:

                df = request_comtrade(
                    reporter_code=reporter_code,
                    period=year,
                    cmd_code=product_code,
                    flow_code=flow,
                )

                if not df.empty:
                    frames.append(df)

            except Exception as e:

                print(
                    f"Request failed: "
                    f"{year} {product_code} {flow}"
                )

                print(e)

            time.sleep(REQUEST_SLEEP)

    if not frames:
        return pd.DataFrame()

    return pd.concat(
        frames,
        ignore_index=True,
    )


# ============================================================
# 保存
# ============================================================

def save_raw_data(df: pd.DataFrame, filename: str):

    path = RAW_DIR / filename

    df.to_csv(
        path,
        index=False,
        encoding="utf-8-sig",
    )

    print(f"Saved: {path}")


# ============================================================
# 主程序
# ============================================================
if __name__ == "__main__":

    # 遍历报告国
    for name, code in REPORTER_NAMES.items():

        print("=" * 60)
        print(f"Reporter: {name} ({code})")
        print("=" * 60)

        # 遍历该国家的所有 HS 编码
        for hs in HS_CODES:

            df = download_product(
                reporter_code=code,
                product_code=hs,
                # start_year / end_year 不传，默认使用START_YEAR / END_YEAR
            )

            if df.empty:
                print(f"  [skip] {name} HS={hs} 无数据")
                continue

            # 备份到 raw/，文件名带上国家和 HS
            save_raw_data(df, f"raw_{name}_{hs}.csv")