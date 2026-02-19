from euroleague_api.EuroLeagueData import EuroLeagueData
import pandas as pd

def inspect_metadata():
    print("Fetching Game Metadata for Season 2025...")
    try:
        # Access the method directly
        df = EuroLeagueData().get_game_metadata_season(season=2025)
        
        print(f"Total Games Found: {len(df)}")
        print("Columns:", df.columns.tolist())
        
        # Check for Round 29
        # Column might be 'round' or 'Round' or 'gameday' (xml mapping)
        # Line 127 says 'round', 'gameday', 'gamenumber'
        # Line 94 says 'gameday' is int.
        
        if 'round' in df.columns:
            r29 = df[df['round'] == '29'] # Might be string in XML
            if r29.empty and 'gameday' in df.columns:
                 r29 = df[df['gameday'] == 29]
            
            print(f"Round 29 Games Found: {len(r29)}")
            if not r29.empty:
                print(r29[['gamenumber', 'round', 'hometeam', 'awayteam']].head(10).to_string())
        else:
            print("Round column not found.")
            print(df.head().to_string())

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_metadata()
