import pandas as pd
import os

def debug_scores():
    # Load one season
    cache_file = "data/pbp_2023.csv"
    if not os.path.exists(cache_file):
        print("Cache file not found.")
        return

    df = pd.read_csv(cache_file)
    
    # Pick a game
    game_code = df['Gamecode'].iloc[0]
    game_df = df[df['Gamecode'] == game_code].copy()
    
    print(f"Debugging Season 2023 Game {game_code}")
    
    # Show spread of POINTS_A and POINTS_B
    print("Head of Score Cols:")
    print(game_df[['PERIOD', 'MARKERTIME', 'PLAYTYPE', 'POINTS_A', 'POINTS_B']].head(20))
    
    # Check for NaNs
    print("\nNull counts:")
    print(game_df[['POINTS_A', 'POINTS_B']].isnull().sum())
    
    # Check data types
    print("\nData Types:")
    print(game_df[['POINTS_A', 'POINTS_B']].dtypes)

if __name__ == "__main__":
    debug_scores()
