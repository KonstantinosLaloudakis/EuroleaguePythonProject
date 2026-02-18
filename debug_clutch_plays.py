from euroleague_api import play_by_play_data
import pandas as pd

def get_seconds_from_time(time_str):
    try:
        minutes, seconds = map(int, str(time_str).split(':'))
        return minutes * 60 + seconds
    except (ValueError, AttributeError):
        return 0

def list_clutch_plays():
    season = 2025
    players_to_check = ["WATSON, GLYNN", "HIFI, NADIR", "WRIGHT IV, MCKINLEY"]
    
    pbp = play_by_play_data.PlayByPlay()
    print(f"Fetching data for season {season}...")
    full_df = pbp.get_game_play_by_play_data_multiple_seasons(season, season)
    
    # --- Data Processing (Same as clutchStats.py) ---
    if 'NUMBEROFPLAY' in full_df.columns:
        full_df = full_df.sort_values(['Gamecode', 'NUMBEROFPLAY'])

    if 'POINTS_A' in full_df.columns and 'POINTS_B' in full_df.columns:
        full_df['POINTS_A'] = pd.to_numeric(full_df['POINTS_A'], errors='coerce')
        full_df['POINTS_B'] = pd.to_numeric(full_df['POINTS_B'], errors='coerce')
        full_df['POINTS_A'] = full_df.groupby('Gamecode')['POINTS_A'].ffill().fillna(0)
        full_df['POINTS_B'] = full_df.groupby('Gamecode')['POINTS_B'].ffill().fillna(0)
        
        # Calculate Pre-Play Margin
        full_df['Prev_POINTS_A'] = full_df.groupby('Gamecode')['POINTS_A'].shift(1).fillna(0)
        full_df['Prev_POINTS_B'] = full_df.groupby('Gamecode')['POINTS_B'].shift(1).fillna(0)
        full_df['PrePlayMargin'] = abs(full_df['Prev_POINTS_A'] - full_df['Prev_POINTS_B'])
    
    # Filter Clutch
    if 'MARKERTIME' in full_df.columns:
         full_df['SecondsRemaining'] = full_df['MARKERTIME'].apply(get_seconds_from_time)
         
    full_df['PERIOD'] = pd.to_numeric(full_df['PERIOD'], errors='coerce')
    
    clutch_df = full_df[
        (full_df['PERIOD'] >= 4) & 
        (full_df['SecondsRemaining'] <= 300) &
        (full_df['PrePlayMargin'] <= 5)
    ].copy()
    
    clutch_df['ScoreMargin'] = abs(clutch_df['POINTS_A'] - clutch_df['POINTS_B'])
    
    # --- Inspect Players ---
    for player in players_to_check:
        print(f"\n--- Checking {player} ---")
        p_df = clutch_df[clutch_df['PLAYER'] == player].copy()
        
        total_points = 0
        scoring_plays = []
        
        for _, row in p_df.iterrows():
            pts = 0
            ptype = row['PLAYTYPE']
            if ptype == '2FGM': pts = 2
            elif ptype == '3FGM': pts = 3
            elif ptype == 'FTM': pts = 1
            
            if pts > 0:
                total_points += pts
                scoring_plays.append(row)
                # print(f"[Game {row['Gamecode']}] {row['MARKERTIME']} (Q{row['PERIOD']}) | {ptype} ({pts}pts) | Score: {row['POINTS_A']}-{row['POINTS_B']} (Diff: {row['ScoreMargin']})")
        
        result = f"Player: {player}\nTotal Logic Points: {total_points}\nTotal Scoring Plays: {len(scoring_plays)}\n----------------\n"
        print(result)
        with open("debug_final_results.txt", "a") as f:
            f.write(result)

if __name__ == "__main__":
    # Clear file first
    open("debug_final_results.txt", "w").close()
    list_clutch_plays()
