"""
Fetch PBP data for all Euroleague seasons from 2007-08 to 2025-26.
Saves each season as data_cache/pbp_{year}.csv.
Skips seasons that already exist.
"""
import os
import shutil
from euroleague_api import play_by_play_data

SEASONS = list(range(2007, 2026))  # 2007 through 2025
CACHE_DIR = 'data_cache'

os.makedirs(CACHE_DIR, exist_ok=True)

pbp = play_by_play_data.PlayByPlay()

for year in SEASONS:
    filename = f'pbp_{year}.csv'
    cache_path = os.path.join(CACHE_DIR, filename)
    root_path = filename  # Some files might be in root from earlier

    # Check if already fetched
    if os.path.exists(cache_path):
        print(f"  [SKIP] {cache_path} already exists")
        continue
    if os.path.exists(root_path):
        # Move to data_cache
        print(f"  [MOVE] {root_path} -> {cache_path}")
        shutil.move(root_path, cache_path)
        continue

    print(f"  [FETCH] Season {year}-{str(year+1)[-2:]}...")
    try:
        df = pbp.get_game_play_by_play_data_multiple_seasons(year, year)
        if df is not None and len(df) > 0:
            df.to_csv(cache_path, index=False)
            print(f"    Saved {len(df)} events to {cache_path}")
        else:
            print(f"    WARNING: No data for season {year}")
    except Exception as e:
        print(f"    ERROR fetching season {year}: {e}")

print("\nDone! All seasons fetched.")
