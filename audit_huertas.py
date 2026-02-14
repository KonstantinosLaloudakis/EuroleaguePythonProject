import pandas as pd
import numpy as np

def get_game_seconds(time_str):
    if not isinstance(time_str, str) or ':' not in time_str: return 0
    try:
        mm, ss = map(int, time_str.split(':'))
        return mm * 60 + ss
    except ValueError:
        return 0

print("Loading data...")
df = pd.read_csv('data/pbp_2010.csv')
g130 = df[df['Gamecode'] == 130].copy()
bas = g130[g130['CODETEAM'] == 'BAS'].copy()

# Add Point Value
bas['PointValue'] = 0
bas.loc[bas['PLAYTYPE'] == '2FGM', 'PointValue'] = 2
bas.loc[bas['PLAYTYPE'] == '3FGM', 'PointValue'] = 3
bas.loc[bas['PLAYTYPE'] == 'FTM', 'PointValue'] = 1

# Add Seconds
bas['Seconds'] = bas['MARKERTIME'].apply(get_game_seconds)

total_points = bas['PointValue'].sum()
print(f'Total BAS Points: {total_points}')

huertas_id = 'PJUJ'
huertas_points = bas[bas['PLAYER_ID'] == huertas_id]['PointValue'].sum()
print(f'Huertas Scored: {huertas_points}')

# Find Assisted Points
huertas_assists = bas[(bas['PLAYTYPE'] == 'AS') & (bas['PLAYER_ID'] == huertas_id)]
print(f'Huertas Assists Count: {len(huertas_assists)}')

print('\n--- Checking Unaccounted Baskets ---')
scores = bas[bas['PointValue'] > 0]
accounted_points = 0
unaccounted_points = 0

for idx, score in scores.iterrows():
    is_huertas_score = (score['PLAYER_ID'] == huertas_id)
    
    # Is it assisted by Huertas?
    # Check neighbors for Huertas AS
    loc_idx = bas.index.get_loc(idx)
    start = max(0, loc_idx - 6)
    end = min(len(bas), loc_idx + 6)
    neighbors = bas.iloc[start:end]
    
    time = score['Seconds']
    
    huertas_as_nearby = neighbors[
        (neighbors['PLAYTYPE'] == 'AS') & 
        (neighbors['PLAYER_ID'] == huertas_id) &
        (abs(neighbors['Seconds'] - time) <= 4)
    ]
    
    is_huertas_assist = not huertas_as_nearby.empty
    
    if is_huertas_score:
        accounted_points += score['PointValue']
        print(f"Scored by Huertas: {score['PointValue']} pts")
    elif is_huertas_assist:
        accounted_points += score['PointValue']
        print(f"Assisted by Huertas: {score['PointValue']} pts ({score['PLAYER']})")
    else:
        unaccounted_points += score['PointValue']
        print(f"UNACCOUNTED: {score['MARKERTIME']} {score['PLAYER']} {score['PLAYTYPE']} ({score['PointValue']}pts)")

print(f'\nTotal Accounted Points: {accounted_points}')
print(f'Total Unaccounted Points: {unaccounted_points}')
print(f'Atlas Index: {accounted_points / total_points * 100:.2f}%')
