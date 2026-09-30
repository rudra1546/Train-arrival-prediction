import polars as pl
import os
import glob
import sys

sys.stdout.reconfigure(encoding='utf-8')
data_dir = "e:/train/data/processed/train_features"
partitions = sorted(glob.glob(os.path.join(data_dir, "year_month=*", "features.parquet")))

print("Auditing duplicates and repeated station visits across all 13 partitions...")

total_dups = 0
total_journeys_checked = 0
total_repeated_stations = 0

for p in partitions:
    ym = os.path.basename(os.path.dirname(p)).split("=")[1]
    df = pl.read_parquet(p, columns=["date", "train_no", "station_name"])
    
    # 1. Exact triplet duplicate check
    dups = df.select(pl.struct(["date", "train_no", "station_name"]).is_duplicated()).sum().item()
    total_dups += dups
    
    # 2. Journeys where a station code appears more than once
    # Since dups == 0 per partition, does any (date, train_no) have duplicate station_name?
    stn_counts = df.group_by(["date", "train_no", "station_name"]).len().filter(pl.col("len") > 1)
    n_rep = len(stn_counts)
    total_repeated_stations += n_rep
    
    journeys = df.select(pl.struct(["date", "train_no"]).n_unique()).item()
    total_journeys_checked += journeys
    print(f"  {ym}: journeys={journeys:,}, triplet_duplicates={dups}, repeated_station_visits={n_rep}")

print("\n=== DUPLICATE AUDIT TOTALS ===")
print(f"Total journeys audited: {total_journeys_checked:,}")
print(f"Total duplicate (date, train_no, station_name) records: {total_dups}")
print(f"Total repeated station visits within any single journey: {total_repeated_stations}")

