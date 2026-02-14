import pandas as pd
import numpy as np

def debug_game(season, gamecode):
    print(f"\n--- Debugging Season {season}, Game {gamecode} ---")
    try:
        df = pd.read_csv(f'data/pbp_{season}.csv')
    except FileNotFoundError:
        print("File not found")
        return

    game = df[df['Gamecode'] == gamecode].copy()
    if game.empty:
        print("Game not found")
        return

    # Check Play Types
    print("Unique PlayTypes:", game['PLAYTYPE'].unique())
    
    # Check CodeTeam
    print("Unique Teams:", game['CODETEAM'].unique())
    
    # Check Scoring Breakdown
    game['Val'] = 0
    # Strip whitespace
    game['PLAYTYPE'] = game['PLAYTYPE'].astype(str).str.strip()
    game['CODETEAM'] = game['CODETEAM'].astype(str).str.strip()
    
    game.loc[game['PLAYTYPE'] == '2FGM', 'Val'] = 2
    game.loc[game['PLAYTYPE'] == '3FGM', 'Val'] = 3
    game.loc[game['PLAYTYPE'] == 'FTM', 'Val'] = 1
    game.loc[game['PLAYTYPE'] == 'LAYUPMD', 'Val'] = 2
    game.loc[game['PLAYTYPE'] == 'DUNK', 'Val'] = 2
    
    print("\n--- Scoring Breakdown ---")
    print(game.groupby(['CODETEAM', 'PLAYTYPE'])['Val'].sum().to_string())
    
    # Print ALL playtypes to see what we missed
    print("\nAll Unique PlayTypes involved in this game:")
    print(game['PLAYTYPE'].unique())
    
    total_score = game.groupby('CODETEAM')['Val'].sum()
    print("\nTotal Calculated Score:")
    print(total_score)
    
    print("\nMax POINTS_A/B in CSV:")
    print(game[['POINTS_A', 'POINTS_B']].max())

debug_game(2012, 176)
