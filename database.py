import pandas as pd
from sqlalchemy import (
    create_engine, 
    text,
    )

from config import DATABASE_PATH


def create_database():

    engine = create_engine(
        f"sqlite:///{DATABASE_PATH}"
    )

    return engine


def save_dataframe(
    df,
    table_name,
    engine
):

    df.to_sql(
        table_name,
        engine,
        if_exists="append",
        index=False
    )

    print(
        f"Table created: {table_name}"
    )

#覆盖相同组别的旧数据
def delete_group(engine, table, country, hs):

    try:
        with engine.begin() as conn:
            conn.execute(
                text(f"DELETE FROM {table} WHERE country=:c AND hs=:h"),
                {"c": country, "h": hs},
            )
            
    except Exception as e:
        # 表不存在，跳过
        if "no such table" in str(e).lower():
            return
        raise

def build_database(
    clean_df,
    results,
    key,
):
    country, hs = key.rsplit("_", 1)

    engine = create_database()
    
    try:
        #删除旧主表和旧分析结果表
        delete_group(engine, "fact_trade", country, hs)
        for name in results:
            delete_group(engine, name, country, hs)

        clean_df = clean_df.copy()
        clean_df["country"] = country
        clean_df["hs"] = hs

        # 主事实表
        save_dataframe(
            clean_df,
            "fact_trade",
            engine
        )

        # 分析结果表
        for name, df in results.items():

            df = df.copy()
            df["country"] = country
            df["hs"] = hs

            save_dataframe(
                df,
                name,
                engine
            )

    finally:
        engine.dispose()