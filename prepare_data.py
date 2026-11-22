"""Clean the raw hotel bookings CSV and write an analysis-ready file.

Usage:
    python prepare_data.py path/to/hotel_bookings.csv
Writes hotel_bookings_clean.csv next to this script.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

MONTHS = [
    "January", "February", "March", "April", "May", "June", "July",
    "August", "September", "October", "November", "December",
]


def clean(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.drop_duplicates().copy()

    df["children"] = df["children"].fillna(0).astype(int)
    df["country"] = df["country"].fillna("Unknown")
    df["agent"] = df["agent"].fillna(0).astype(int)      # 0 = no agent
    df["company"] = df["company"].fillna(0).astype(int)  # 0 = no company
    df["meal"] = df["meal"].replace({"Undefined": "SC"})
    df["hotel"] = df["hotel"].str.strip()

    df["total_guests"] = df["adults"] + df["children"] + df["babies"]
    df = df[df["total_guests"] > 0].copy()

    df["total_nights"] = df["stays_in_weekend_nights"] + df["stays_in_week_nights"]
    df = df[df["total_nights"] > 0].copy()

    month_num = {m: i + 1 for i, m in enumerate(MONTHS)}
    df["arrival_month_num"] = df["arrival_date_month"].map(month_num)
    df["arrival_date"] = pd.to_datetime(
        dict(
            year=df["arrival_date_year"],
            month=df["arrival_month_num"],
            day=df["arrival_date_day_of_month"],
        )
    )

    df["is_zero_adr"] = df["adr"] == 0
    df["revenue"] = df["adr"] * df["total_nights"]
    df["status"] = np.where(df["is_canceled"] == 1, "Canceled", "Stayed or no-show")
    return df


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python prepare_data.py path/to/hotel_bookings.csv")
    raw = pd.read_csv(sys.argv[1])
    clean_df = clean(raw)
    out = Path(__file__).with_name("hotel_bookings_clean.csv")
    clean_df.to_csv(out, index=False)
    print(f"Raw rows: {len(raw):,}  Clean rows: {len(clean_df):,}  Written to {out.name}")
