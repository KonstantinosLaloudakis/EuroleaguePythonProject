import pandas as pd
from euroleague_api import play_by_play_data
import json

def analyze_columns(season=2023):
    pbp = play_by_play_data.PlayByPlay()
    print(f"Fetching Game 1 of Season {season} to inspect columns...")
    try:
        data = pbp.get_game_play_by_play_data(season, 1)
        df = pd.DataFrame(data)
        print("COLUMNS FOUND:")
        print(df.columns.tolist())
        print("HEAD:")
        print(df.head(3))
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze_columns()
