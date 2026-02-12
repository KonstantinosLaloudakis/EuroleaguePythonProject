import json
import pandas as pd

def calibrate():
    with open('clutch_shots_2024_2024.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    
    # Check unique types
    print("Unique Shot Types:", df['Type'].unique())
    
    # Filter for Dunk
    dunks = df[df['Type'].str.contains('DUNK', case=False)]
    if not dunks.empty:
        print(f"\nAnalyzing {len(dunks)} DUNKS:")
        print(f"Mean X: {dunks['CoordX'].mean()}")
        print(f"Mean Y: {dunks['CoordY'].mean()}")
    
    # Filter for Layup
    layups = df[df['Type'].str.contains('LAYUP', case=False)]
    if not layups.empty:
        print(f"\nAnalyzing {len(layups)} LAYUPS:")
        print(f"Mean X: {layups['CoordX'].mean()}")
        print(f"Mean Y: {layups['CoordY'].mean()}")

if __name__ == "__main__":
    calibrate()
