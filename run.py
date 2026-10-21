import pandas as pd

from config import (
    RAW_DIR,
    PROCESSED_DIR,
    OUTPUT_DIR,
)

from clean import (
    clean_one,
)

from analysis import (
    run_analysis,
    save_results,
)

from database import (
    build_database,
)


def main():

    # 遍历目录
    for raw_file in RAW_DIR.glob("raw_*.csv"):
        stem = raw_file.stem                 #  raw_China_854142
        parts = stem.rsplit("_", 2)

        country, hs = parts[1], parts[2]     #  ["raw", "China", "854142"]
        key = f"{country}_{hs}"              #  China_854142

        # 清洗
        clean_dir = PROCESSED_DIR / key
        clean_one(raw_file, clean_dir)

        # 分析
        clean_df = pd.read_csv(clean_dir / "trade_clean.csv") 
        results = run_analysis(clean_df)
        save_results(results, OUTPUT_DIR / key)

        # 入库
        build_database(clean_df, results, key)


if __name__ == "__main__":
    main()