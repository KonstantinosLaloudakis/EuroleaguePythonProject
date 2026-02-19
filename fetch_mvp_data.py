import pandas as pd
import json
import os
import traceback
from euroleague_api import standings, player_stats

def fetch_mvp_data():
    season = 2025
    
    # 1. Fetch Standings
    print("Fetching Standings...")
    try:
        s = standings.Standings()
        # Positional arguments: (season, round_number)
        # Try round 25 directly
        try:
             df_standings = s.get_standings(season, 25)
        except Exception as e:
             print(f"Round 25 failed ({e}), trying round 20...")
             df_standings = s.get_standings(season, 20)

        if df_standings.empty:
             print("Warning: Standings empty.")
        
        # We need Team Code -> Win % mapping
        print("Standings Columns:", df_standings.columns.tolist())
        
        # Normalize
        if 'team.code' in df_standings.columns:
            df_standings['TeamCode'] = df_standings['team.code']
        elif 'club.code' in df_standings.columns:
            df_standings['TeamCode'] = df_standings['club.code']
            
        standings_dict = {}
        for idx, row in df_standings.iterrows():
            code = row.get('TeamCode', '')
            wins = row.get('won', 0)
            played = row.get('played', 1)
            position = row.get('position', 18)
            standings_dict[code] = {
                'Wins': wins,
                'Played': played,
                'Position': position,
                'WinPct': wins / played if played > 0 else 0
            }
            
        with open('mvp_standings.json', 'w') as f:
            json.dump(standings_dict, f, indent=4)
        print("Saved mvp_standings.json")
            
    except Exception as e:
        print(f"Error fetching standings: {e}")

    # 2. Fetch Accumulated Player Stats
    print("Fetching Player Stats...")
    try:
        p = player_stats.PlayerStats()
        
        # Try just endpoint? Maybe season is not needed or inferred?
        try:
            print("Trying just 'traditional'...")
            df_stats = p.get_player_stats('traditional')
        except Exception as e:
             print(f"Just 'traditional' failed: {e}")
             # try with season as keyword but maybe name is different?
             traceback.print_exc()
             df_stats = pd.DataFrame()

        print("Stats fetched. Rows:", len(df_stats))
        print("Stats Columns:", df_stats.columns.tolist())
        
        # Save raw stats
        df_stats.to_json('mvp_raw_stats.json', orient='records', indent=4)
        print("Saved mvp_raw_stats.json")
        
    except Exception as e:
        print(f"Error fetching player stats: {e}")
        traceback.print_exc()

    print("Data Fetch Complete.")

if __name__ == "__main__":
    fetch_mvp_data()
