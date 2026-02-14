import pandas as pd
import os

df = pd.read_csv('data/pbp_2024.csv') # Read full file to get samples
# Check RV, CM, FV, AG, BP, OF
playtypes = ['RV', 'CM', 'FV', 'AG', 'BP', 'OF']
for pt in playtypes:
    print(f"\n--- {pt} ---")
    subset = df[df['PLAYTYPE'] == pt]
    if not subset.empty:
        print(subset['PLAYINFO'].dropna().head(10).to_string())
    else:
        print("No events found")
