import pandas as pd
from euroleague_api import play_by_play_data
import os

import sys

def fetch_and_cache_pbp():
    file_path = 'pbp_2025.csv'
    force_fetch = '--force' in sys.argv
    if os.path.exists(file_path) and not force_fetch:
        print(f"Loading cached Play-By-Play data from {file_path}")
        df = pd.read_csv(file_path)
    else:
        print(f"Fetching full Play-By-Play data for 2025 season...")
        pbp = play_by_play_data.PlayByPlay()
        df = pbp.get_game_play_by_play_data_multiple_seasons(2025, 2025)
        
        # Clean up some types to save space
        if not df.empty:
            df.to_csv(file_path, index=False)
            print(f"Saved {len(df)} play-by-play events to {file_path}")
        else:
            print("Failed to fetch PbP data.")
            
    return df

if __name__ == '__main__':
    fetch_and_cache_pbp()
