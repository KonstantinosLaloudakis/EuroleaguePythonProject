from euroleague_api.play_by_play_data import PlayByPlay
import pandas as pd

def inspect():
    pbp = PlayByPlay()
    season = 2024
    game_code = 1 
    
    # Set pandas display options
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    
    print(f"Fetching PBP with lineups for Season {season}, Game {game_code}...")
    try:
        df = pbp.get_pbp_data_with_lineups(season, game_code)
        if not df.empty:
            print("Columns:")
            for c in df.columns:
                print(c)
                
            print("\nSample Data (First 3 rows):")
            # Print specific columns of interest
            cols_to_show = ['Time', 'Team', 'Points', 'Points_A', 'Points_B'] 
            # Add lineup cols dynamically
            lineup_cols = [c for c in df.columns if 'Lineup' in c]
            cols_to_show.extend(lineup_cols)
            
            # Filter cols that actually exist
            cols_to_show = [c for c in cols_to_show if c in df.columns]
            
            print(df[cols_to_show].head(3))
            
            # Check type of lineup column
            if lineup_cols:
                first_lineup = df[lineup_cols[0]].iloc[0]
                print(f"\nType of {lineup_cols[0]}: {type(first_lineup)}")
                print(f"Value: {first_lineup}")
                
        else:
            print("DataFrame is empty.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect()
