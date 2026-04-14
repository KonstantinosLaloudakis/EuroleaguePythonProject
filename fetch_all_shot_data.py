"""
Fetch Euroleague shot data for all historical seasons (2007-2024).
Run: python fetch_all_shot_data.py

After this completes, run:
    python preprocess_wp_data.py
to inject the shot coordinates into the WP replay JSON files.
"""
import pandas as pd
from euroleague_api import shot_data
import os
import time

SEASONS = list(range(2007, 2025))  # 2007 through 2024
OUTPUT_DIR = 'data'

os.makedirs(OUTPUT_DIR, exist_ok=True)

shots_api = shot_data.ShotData()
total = len(SEASONS)

for i, season in enumerate(SEASONS, 1):
    file_path = os.path.join(OUTPUT_DIR, f'shot_data_{season}_{season}.csv')
    root_path = f'shot_data_{season}_{season}.csv'

    if os.path.exists(file_path):
        print(f"[{i}/{total}] Season {season}: already cached at {file_path}, skipping")
        continue

    print(f"[{i}/{total}] Season {season}: fetching from API...")
    t0 = time.time()
    try:
        df = shots_api.get_game_shot_data_single_season(season)
    except AttributeError:
        df = shots_api.get_game_shot_data_range_seasons(season, season)

    elapsed = time.time() - t0

    if df is not None and not df.empty:
        df.to_csv(file_path, index=False)
        df.to_csv(root_path, index=False)
        print(f"    -> {len(df)} shots saved ({elapsed:.1f}s)")
    else:
        print(f"    -> No data returned ({elapsed:.1f}s)")

print("\nDone! Next step: python preprocess_wp_data.py")
