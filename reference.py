import requests
import pandas as pd

from config import RAW_DIR


PARTNER_AREA_URL = (
    "https://comtradeapi.un.org/files/v1/app/reference/partnerAreas.json"
)


def fetch_partner_codes():
    """
    拉取所有有效伙伴国代码（排除汇总项）。
    """
    resp = requests.get(PARTNER_AREA_URL, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    df = pd.DataFrame(data["results"])

    # 排除汇总项（World 等）
    df = df[df["id"] != "0"]

    return df

def save_partner_codes(df):
    path = RAW_DIR / "partner_codes.csv"
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"Saved: {path}")

if __name__ == "__main__":
    df = fetch_partner_codes()
    save_partner_codes(df)
    print(f"Total partners: {len(df)}")