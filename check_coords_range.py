import json
import pandas as pd

def check_range():
    with open('clutch_shots_2024_2024.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    print(df[['CoordX', 'CoordY']].describe())
    
    # Check distribution
    print("\nCoordX Head:")
    print(df['CoordX'].head(10))
    print("\nCoordY Head:")
    print(df['CoordY'].head(10))

if __name__ == "__main__":
    check_range()
