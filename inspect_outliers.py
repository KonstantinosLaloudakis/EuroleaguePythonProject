import pandas as pd
import os
import ast

CACHE_DIR = "data_cache"
SEASON = 2025
TARGET_DUO = {"KURUCS, RODIONS", "SIMMONS, KOBI"}

def inspect():
    file_path = os.path.join(CACHE_DIR, f"pbp_lineups_{SEASON}.csv")
    if not os.path.exists(file_path):
        print("Cache file not found.")
        return

    print(f"Loading {file_path}...")
    df = pd.read_csv(file_path, low_memory=False)
    
    lineup_cols = [c for c in df.columns if 'Lineup_' in c]
    print(f"Lineup Columns found: {lineup_cols}")
    
    found_games = set()
    
    for idx, row in df.iterrows():
        # Check each lineup col
        for col in lineup_cols:
            val = row[col]
            if isinstance(val, str):
                try:
                    players = set(ast.literal_eval(val))
                    if TARGET_DUO.issubset(players):
                        game_code = row.get('GameCode', 'Unknown')
                        found_games.add(game_code)
                        print(f"Found Pair in Game {game_code}, Column {col}")
                        print(f"  Row Index: {idx}")
                        # print(f"  Lineup: {players}")
                        
                        # Print Team A/B
                        # print(f"  Row Data: {row.to_dict()}")
                        return # Stop after first find to examine
                except:
                    pass
                    
    print(f"Games with target duo: {found_games}")

if __name__ == "__main__":
    inspect()
