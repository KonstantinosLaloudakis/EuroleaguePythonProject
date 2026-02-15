import pandas as pd

df = pd.read_csv('data/pbp_2024.csv')
# Sort by Game and NumberOfPlay
if 'NUMBEROFPLAY' in df.columns:
    df = df.sort_values(['Gamecode', 'NUMBEROFPLAY'])
else:
    print("No NUMBEROFPLAY, using index")

# Look for AS events
assists = df[df['PLAYTYPE'] == 'AS'].head(20)

for idx, row in assists.iterrows():
    # Look at previous event
    prev_idx = idx - 1
    if prev_idx in df.index:
        prev_row = df.loc[prev_idx]
        print(f"Game {row['Gamecode']} Play {row['NUMBEROFPLAY']} (AS): {row['PLAYER']}")
        print(f"   --> Prev Play {prev_row['NUMBEROFPLAY']} ({prev_row['PLAYTYPE']}): {prev_row['PLAYER']} ({prev_row['POINTS_A']}-{prev_row['POINTS_B']})")
        print("-" * 20)
