import pandas as pd
import json
import time
from euroleague_api import game_stats
import traceback

def fetch_mvp_data_iterative():
    season = 2025
    gst = game_stats.GameStats()
    
    all_game_stats = []
    
    # We don't know exactly how many games per round or how many rounds.
    # But usually 9 games per round.
    # Providing Round Number is enough for get_game_stats? 
    # inspect says `get_game_stats(season, game_code)`? 
    # Or `get_game_stats(season, round, ...)`?
    # check_mvp_stats.py used `get_game_stats(2025, 1)`. 
    # Wait, `get_game_stats(2025, 1)` -> is 1 the game code or round?
    # Usually game code is sequential (1..306+).
    # If I have to iterate game codes, I need to know the range.
    # 18 teams -> 9 games/round * 34 rounds = 306 games.
    # Play-in/Playoffs add more.
    # Let's try fetching game 1 to 300.
    
    print(f"Fetching games for season {season}...")
    
    # We can fetch in batches.
    # If we hit a 404/Empty, we stop?
    # Games are usually 1-indexed.
    
    consecutive_errors = 0
    max_games = 300 # Full season coverage
    
    for game_code in range(1, max_games + 1):
        try:
            # print(f"Fetching Game {game_code}...", end='\r')
            df = gst.get_game_stats(season, game_code)
            
            if df is None or df.empty:
                consecutive_errors += 1
                if consecutive_errors > 10: # If 10 consecutive games empty, assume season end?
                    print(f"\nStopped at Game {game_code} (10 consecutive empty).")
                    break
                continue
            
            consecutive_errors = 0
            
            # Enrich with Game Code just in case
            df['GameCode'] = game_code
            all_game_stats.append(df)
            
        except Exception as e:
            # print(f"Error Game {game_code}: {e}")
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
    full_df.to_json('mvp_all_game_stats_2025.json', orient='records', indent=4)
    print("Saved mvp_all_game_stats_2025.json")

if __name__ == "__main__":
    fetch_mvp_data_iterative()
