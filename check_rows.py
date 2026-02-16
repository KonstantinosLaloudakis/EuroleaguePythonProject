import pandas as pd
df = pd.read_csv("data_cache/pbp_lineups_2025.csv", low_memory=False)
rows = len(df[df['GameCode'] == 52])
print(f"Rows for Game 52: {rows}")
