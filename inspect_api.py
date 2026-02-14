from euroleague_api import shot_data
import pandas as pd

try:
    print("Fetching Shot Data for 2024 Game 1...")
    shots = shot_data.ShotData()
    # Try fetching for single game? 
    # Usually get_game_shot_data(season, gamecode)
    df = shots.get_game_shot_data(2024, 1)
    
    if not df.empty:
        print("\nColumns:", list(df.columns))
        print("\nSample Shots:")
        # Show Make/Miss and Coords
        print(df[['PLAYER', 'ID_ACTION', 'COORD_X', 'COORD_Y']].head(10).to_string())
        
        # Check range of coords
        print("\nCoord Range:")
        print(f"X: {df['COORD_X'].min()} to {df['COORD_X'].max()}")
        print(f"Y: {df['COORD_Y'].min()} to {df['COORD_Y'].max()}")
        
except Exception as e:
    print(f"Error: {e}")
