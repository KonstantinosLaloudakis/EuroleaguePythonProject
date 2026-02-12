import pandas as pd
import json

file_path = 'quarter_masters_2007_2024.json'

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    df = pd.DataFrame(data)
    
    # Check for Points < 8
    low_streaks = df[df['Points'] < 8]
    
    if low_streaks.empty:
        print("Verification SUCCESS: No streaks below 8 points found.")
    else:
        print(f"Verification FAILED: Found {len(low_streaks)} streaks below 8 points.")
        print(low_streaks.head())
        
    # Check for Opponent column
    if 'Opponent' in df.columns:
        print("Verification SUCCESS: 'Opponent' column found.")
        print(df[['PLAYER', 'CODETEAM', 'Opponent', 'Points']].head())
    else:
        print("Verification FAILED: 'Opponent' column NOT found.")

except Exception as e:
    print(f"Error reading file: {e}")
