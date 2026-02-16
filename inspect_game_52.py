import pandas as pd
import os
import ast

def inspect():
    file_path = "data_cache/pbp_lineups_2025.csv"
    print(f"Loading {file_path} for Game 52...")
    df = pd.read_csv(file_path, low_memory=False)
    
    game_df = df[df['GameCode'] == 52].copy()
    if game_df.empty:
        print("Game 52 not found.")
        return
        
    print(f"Columns: {list(game_df.columns)}")
    
    # Check Periods
    periods = game_df['PERIOD'].unique()
    print(f"Unique Periods: {periods}")
    
    # Check Seconds
    def process_time_str(t_str):
        if not isinstance(t_str, str): return 0
        try:
            parts = t_str.split(':')
            return int(parts[0]) * 60 + int(parts[1])
        except: return 0
        
    game_df['Seconds'] = game_df['MARKERTIME'].apply(process_time_str)
    
    for p in periods:
        p_data = game_df[game_df['PERIOD'] == p]['Seconds']
        print(f"Period {p} Stats: Count={len(p_data)}, Max={p_data.max()}, Min={p_data.min()}, Unique={len(p_data.unique())}")
        print(f"  Head: {p_data.head(5).tolist()}")
        print(f"  Tail: {p_data.tail(5).tolist()}")
    
    # Check Lineups
    target = {"KURUCS, RODIONS", "SIMMONS, KOBI"}
    lineup_cols = [c for c in game_df.columns if 'Lineup_' in c]
    
    found_count = 0
    for col in lineup_cols:
        col_count = 0
        for idx, val in game_df[col].items():
            if isinstance(val, str):
                try:
                    players = set(ast.literal_eval(val))
                    if target.issubset(players):
                        col_count += 1
                except: pass
        if col_count > 0:
            print(f"Column {col} has {col_count} rows with target pair.")
        found_count += col_count
    
    print(f"Total rows with target pair: {found_count}")

if __name__ == "__main__":
    inspect()
