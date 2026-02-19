import pandas as pd
import json
import time
from euroleague_api import game_stats
import traceback

def fetch_mvp_data_2024():
    season = 2024
    gst = game_stats.GameStats()
    
    all_game_stats = []
    
    # 2024-25 Season (Last Year)
    # Approx 34 Rounds + Play-in + Playoffs + F4?
    # Let's fetch huge range to be safe.
    
    print(f"Fetching games for season {season}...")
    
    consecutive_errors = 0
    max_games = 330 # Should cover F4
    
    for game_code in range(1, max_games + 1):
        try:
            df = gst.get_game_stats(season, game_code)
            
            if df is None or df.empty:
                consecutive_errors += 1
                if consecutive_errors > 10: 
                    print(f"\nStopped at Game {game_code} (10 consecutive empty).")
                    break
                continue
            
            consecutive_errors = 0
            
            # Enrich with Game Code just in case
            df['GameCode'] = game_code
            all_game_stats.append(df)
            
        except Exception as e:
            consecutive_errors += 1
            if consecutive_errors > 20: 
                print(f"\nStopped at Game {game_code} (20 consecutive errors).")
                break
    
    if not all_game_stats:
        print("No data fetched!")
        return

    full_df = pd.concat(all_game_stats, ignore_index=True)
    print(f"\nFetched {len(full_df)} rows of stats.")
    
    # Save raw
    full_df.to_json('mvp_all_game_stats_2024.json', orient='records', indent=4)
    print("Saved mvp_all_game_stats_2024.json")

if __name__ == "__main__":
    fetch_mvp_data_2024()
