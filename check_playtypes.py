
from euroleague_api import play_by_play_data
import pandas as pd

def check_all_playtypes(season=2023):
    pbp = play_by_play_data.PlayByPlay()
    print(f"Fetching play-by-play data for Season {season} (Game 1-10)...")
    try:
        # Fetch a few games to get a good spread of playtypes
        all_games = []
        for game_code in range(1, 11):
            try:
                data = pbp.get_game_play_by_play_data(season, game_code)
                all_games.extend(data)
            except:
                pass
        
        df = pd.DataFrame(all_games)
        if not df.empty:
            print("UNIQUE PLAYTYPES FOUND:")
            unique_types = sorted(df['PLAYTYPE'].astype(str).unique())
            print(unique_types)
            
            # Check for substitutions specifically
            print(f"\n'IN' in playtypes? {'IN' in unique_types}")
            print(f"'OUT' in playtypes? {'OUT' in unique_types}")
        else:
            print("No data found.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_all_playtypes()
