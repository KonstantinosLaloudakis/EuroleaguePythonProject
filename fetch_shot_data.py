import pandas as pd
from euroleague_api import shot_data
import os
import sys

def fetch_and_cache_shot_data():
    # Save both in data folder and in root to ensure compatibility with all scripts
    file_path_data = 'data/shot_data_2025_2025.csv'
    file_path_root = 'shot_data_2025_2025.csv'
    
    force_fetch = '--force' in sys.argv
    
    if os.path.exists(file_path_data) and not force_fetch:
        print(f"Loading cached Shot data from {file_path_data}")
        df = pd.read_csv(file_path_data, low_memory=False)
    elif os.path.exists(file_path_root) and not force_fetch:
        print(f"Loading cached Shot data from {file_path_root}")
        df = pd.read_csv(file_path_root, low_memory=False)
    else:
        print(f"Fetching full Shot data (coordinates) for 2025 season...")
        shots = shot_data.ShotData()
        df = shots.get_game_shot_data_multiple_seasons(2025, 2025)
        
        if not df.empty:
            # Ensure data directory exists
            os.makedirs('data', exist_ok=True)
            
            # Save to both locations to prevent breakages in other modules
            df.to_csv(file_path_data, index=False)
            df.to_csv(file_path_root, index=False)
            print(f"Saved {len(df)} shot attempts to {file_path_data} and {file_path_root}")
        else:
            print("Failed to fetch Shot data.")
            
    return df

if __name__ == '__main__':
    fetch_and_cache_shot_data()
