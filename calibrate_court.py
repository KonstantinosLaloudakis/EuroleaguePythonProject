from euroleague_api import shot_data
import pandas as pd
import numpy as np

try:
    shots = shot_data.ShotData()
    df = shots.get_game_shot_data(2024, 1) # Game 1
    
    # Filter for makes
    makes = df[df['ID_ACTION'].isin(['2FGM', '3FGM'])].copy()
    
    # Calculate distance from (0,0)
    # Assuming (0,0) is hoop center?
    makes['Distance'] = np.sqrt(makes['COORD_X']**2 + makes['COORD_Y']**2)
    
    print("--- 3FGM Distances ---")
    print(makes[makes['ID_ACTION'] == '3FGM']['Distance'].describe())

    print("\n--- 2FGM Distances ---")
    print(makes[makes['ID_ACTION'] == '3FGM']['Distance'].describe())
    
    # Check if this matches meters (cm)
    # Euroleague 3pt line = 6.75m = 675cm
    
except Exception as e:
    print(f"Error: {e}")
