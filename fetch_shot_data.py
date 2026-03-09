import pandas as pd
from euroleague_api import shot_data
import os
import sys
import argparse

def fetch_and_cache_shot_data(season=2025):
    # Save both in data folder and in root to ensure compatibility with all scripts
    file_path_data = f'data/shot_data_{season}_{season}.csv'
    file_path_root = f'shot_data_{season}_{season}.csv'
    
    force_fetch = '--force' in sys.argv
    
    if os.path.exists(file_path_data) and not force_fetch:
        print(f"Loading cached Shot data from {file_path_data}")
        df = pd.read_csv(file_path_data, low_memory=False)
    elif os.path.exists(file_path_root) and not force_fetch:
        print(f"Loading cached Shot data from {file_path_root}")
        df = pd.read_csv(file_path_root, low_memory=False)
    else:
        print(f"Fetching full Shot data (coordinates) for {season} season...")
        shots = shot_data.ShotData()
        df = shots.get_game_shot_data_multiple_seasons(season, season)
        
        if not df.empty:
            # Ensure data directory exists
            os.makedirs('data', exist_ok=True)
            
            # Save to both locations to prevent breakages in other modules
            df.to_csv(file_path_data, index=False)
            df.to_csv(file_path_root, index=False)
            print(f"Saved {len(df)} shot attempts to {file_path_data} and {file_path_root}")
        else:
            print(f"Failed to fetch Shot data for {season}.")
            
    return df

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fetch Euroleague shot data')
    parser.add_argument('--season', type=int, default=2025, help='Season year to fetch (default: 2025)')
    parser.add_argument('--force', action='store_true', help='Force re-fetch even if cached')
    args = parser.parse_args()
    fetch_and_cache_shot_data(season=args.season)

