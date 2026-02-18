from euroleague_api import play_by_play_data
import pandas as pd
import numpy as np

def check_score_sparsity():
    pbp = play_by_play_data.PlayByPlay()
    # Fetch small sample
    df = pbp.get_game_play_by_play_data_multiple_seasons(2025, 2025)
    
    # Pick a game
    game_code = df['Gamecode'].iloc[0]
    game_df = df[df['Gamecode'] == game_code].copy()
    
    print(f"Checking Game {game_code}")
    print("Head of POINTS_A column:")
    print(game_df['POINTS_A'].head(20))
    
    # Check if NaNs exist
    nans = game_df['POINTS_A'].isna().sum()
    print(f"Total NaNs in POINTS_A: {nans} out of {len(game_df)}")
    
    # Check if misses have scores
    misses = game_df[game_df['PLAYTYPE'].isin(['2FGA', '3FGA'])]
    print("Sample Misses scores:")
    print(misses[['PLAYTYPE', 'POINTS_A', 'POINTS_B']].head())

if __name__ == "__main__":
    check_score_sparsity()
