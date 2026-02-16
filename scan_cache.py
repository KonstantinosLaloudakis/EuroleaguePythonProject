import pandas as pd
import ast

def scan():
    file_path = "data_cache/pbp_lineups_2025.csv"
    print(f"Loading {file_path}...")
    df = pd.read_csv(file_path, low_memory=False)
    
    target = {"KURUCS, RODIONS", "SIMMONS, KOBI"}
    lineup_cols = [c for c in df.columns if 'Lineup_' in c]
    
    print(f"Scanning {len(df)} rows across {len(df['GameCode'].unique())} games...")
    
    games_with_pair = {}
    
    for idx, row in df.iterrows():
        gcode = row['GameCode']
        found = False
        for col in lineup_cols:
            val = row[col]
            if isinstance(val, str):
                try:
                    players = set(ast.literal_eval(val))
                    if target.issubset(players):
                        found = True
                        break
                except:
                    pass
        if found:
            games_with_pair[gcode] = games_with_pair.get(gcode, 0) + 1
            
    print("Games containing the pair:")
    for g, count in games_with_pair.items():
        print(f"Game {g}: {count} rows")
        
if __name__ == "__main__":
    scan()
