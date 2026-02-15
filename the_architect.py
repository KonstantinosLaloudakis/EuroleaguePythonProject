import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from euroleague_api import play_by_play_data
import os
import json

# --- Configuration ---
START_SEASON = 2023
END_SEASON = 2025

def fetch_pbp_data(start_season, end_season):
    cache_file = f"pbp_data_{start_season}_{end_season}.csv"
    
    if os.path.exists(cache_file):
        print(f"Loading cached PBP data from {cache_file}...")
        try:
            return pd.read_csv(cache_file, low_memory=False)
        except Exception as e:
            print(f"Error reading cache: {e}. Fetching fresh data...")

    print(f"Fetching play-by-play data from {start_season} to {end_season}...")
    try:
        pbp = play_by_play_data.PlayByPlay()
        # The API doesn't have a multi-season PBP fetcher by default in some versions,
        # but let's check if it exists or we need to loop.
        # Based on previous usage, we might need to loop games.
        # But wait, `euroleague_clutch_analysis.py` used `get_game_play_by_play_data_multiple_seasons`.
        # Let's try that.
        df = pbp.get_game_play_by_play_data_multiple_seasons(start_season, end_season)
        
        if not df.empty:
            print(f"Saving data to {cache_file}...")
            df.to_csv(cache_file, index=False)
            
        return df
    except Exception as e:
        print(f"Error fetching PBP data: {e}")
        return pd.DataFrame()

def analyze_architect(df):
    """
    Calculates Points Created via Assists.
    Logic:
    1. Identify Assist events (PLAYTYPE == 'AS').
    2. Link to the immediately preceding Score event (2FGM, 3FGM) by the same Team.
       - Actually, in PBP data, the Assist usually FOLLOWS the score or vice versa?
       - Based on `assist_context.txt`:
         Row 6: 2FGM (Lessort) at 09:20
         Row 7: AS (Nunn) at 09:17
         In this data, the AS comes AFTER the shot row index-wise?
         Wait, PBP is usually ordered by time descending or ascending?
         In `assist_context.txt`:
         MarkerTime: 09:27 (D), 09:20 (2FGM), 09:17 (AS), 09:04 (CM).
         Time is decreasing (Counting down).
         So row 6 (09:20) happens BEFORE row 7 (09:17).
         
         So the Assist event (Row 7) is recorded AFTER the Shot (Row 6) in terms of game clock (it has lower clock time? No wait).
         09:20 is earlier in the game than 09:17? No, it's a countdown.
         10:00 -> 00:00.
         09:20 is later than 09:17? No. 09:20 means 9 mins 20 sec remaining.
         09:17 means 9 mins 17 sec remaining.
         So 09:20 happened FIRST, then 09:17 happened 3 seconds LATER.
         
         So the Shot (Row 6) happened at 9:20 left.
         The Assist (Row 7) happened at 9:17 left.
         
         So in the DataFrame (which usually follows chronological order of recording?), 
         Row 6 (Index 6) is the Shot.
         Row 7 (Index 7) is the Assist.
         
         So when we find an AS, we look at the PREVIOUS rows (index - 1, -2...) to find the corresponding shot.
         
         Conditions:
         - Same Team
         - Same Period
         - Event Type is 2FGM or 3FGM
         - Time difference is small (e.g. within 5-10 seconds of game clock, or just immediate predecessor in game stream).
    """
    
    # Ensure sorted by Game, Period, Time (Desc or Asc?)
    # Usually indices are reliable if fetched correctly.
    # Let's trust the index order for now, assuming it matches the API list.
    
    points_created_map = {} # PlayerID -> {Name, PointsCreated, Assists}
    
    # It's faster to iterate or use vectorization. 
    # Since we need to look back, let's iterate through AS events.
    
    assists_df = df[df['PLAYTYPE'] == 'AS'].copy()
    
    if assists_df.empty:
        return pd.DataFrame()
        
    print(f"Analyzing {len(assists_df)} assists...")
    
    # We need the full DF access.
    # To optimize: distinct games.
    
    games = df['Gamecode'].unique() # Need verify column name. assist_context said 'Gamecode'.
    seasons = df['Season'].unique()
    
    # This might be slow if we iterate all rows.
    # Better approach: Shift columns?
    # Create 'PrevPlayType', 'PrevPoints', 'PrevTeam', 'PrevPlayer'
    
    # Sort by Season, GameCode, NumberOfPlay (if available) or Index
    if 'NUMBEROFPLAY' in df.columns:
        df = df.sort_values(['Season', 'Gamecode', 'NUMBEROFPLAY'])
    else:
        # Fallback
        pass
        
    # Shift values to align Shot with subsequent Assist
    # We want to check if Row N is AS, does Row N-1 match a shot?
    
    df['Prev_PLAYTYPE'] = df['PLAYTYPE'].shift(1)
    df['Prev_CODETEAM'] = df['CODETEAM'].shift(1)
    df['Prev_POINTS_A'] = df['POINTS_A'].shift(1) # These might be cumulative score? 
    # Wait, Points column?
    # In `assist_context.txt`, POINTS_A/B seem to be cumulative score or null.
    # We need the points *of the shot*.
    # 2FGM = 2 pts, 3FGM = 3 pts.
    
    def get_shot_points(playtype):
        if playtype == '2FGM' or 'DUNK' in str(playtype) or 'LAYUP' in str(playtype):
            return 2
        if playtype == '3FGM':
            return 3
        return 0
    
    df['ShotPoints'] = df['Prev_PLAYTYPE'].apply(get_shot_points)
    
    # Filter for rows where Current is AS
    # And Previous is Shot
    # And Previous Team == Current Team
    
    # Possible sequence: Shot -> ... -> Assist? 
    # Sometimes substitutions or fouls happen in between?
    # Usually Shot -> Assist is immediate or separated by dead ball info. 
    # But strictly, the Assist is credited TO the shot. So they should be linked.
    # Let's assume strict adjacency (N-1) first. If simple shift works, great.
    
    # Refined Logic:
    # 1. Row is AS.
    # 2. Row-1 is 2FGM or 3FGM. [Check]
    # 3. Row-1 Team == Row Team. [Check]
    # 4. Row-1 Period == Row Period. [Check]
    
    mask = (
        (df['PLAYTYPE'] == 'AS') & 
        (df['Prev_PLAYTYPE'].isin(['2FGM', '3FGM', 'DUNK', 'LAYUP'])) & 
        (df['Prev_CODETEAM'] == df['CODETEAM'])
    )
    
    architects = df[mask].copy()
    
    # Points Created = ShotPoints of the previous play
    architects['PointsCreated'] = architects['ShotPoints']
    
    # Aggregation
    player_stats = architects.groupby('PLAYER_ID').agg({
        'PLAYER': 'first',
        'PointsCreated': 'sum',
        'PLAYTYPE': 'count', # Assist Count
        'Season': 'nunique', # seasons played
        'Gamecode': 'nunique' # games played via assists? No, strictly games with assists.
        # We need total games played to calc average. 
        # This is hard from just assists. We need a separate games count per player.
    }).reset_index()
    
    player_stats.rename(columns={'PLAYTYPE': 'Assists', 'PLAYER': 'PlayerName'}, inplace=True)
    
    # Calculate Per Game Stats
    # We need total games for each player from the full DF, not just assist rows.
    total_games = df.groupby('PLAYER_ID')['Gamecode'].nunique().reset_index()
    total_games.rename(columns={'Gamecode': 'TotalGames'}, inplace=True)
    
    player_stats = pd.merge(player_stats, total_games, on='PLAYER_ID', how='left')
    player_stats['PointsCreatedPerGame'] = player_stats['PointsCreated'] / player_stats['TotalGames']
    player_stats['PPC_Ratio'] = player_stats['PointsCreated'] / player_stats['Assists'] # Avg points per assist
    
    return player_stats

def main():
    df = fetch_pbp_data(START_SEASON, END_SEASON)
    if df.empty: return
    
    results = analyze_architect(df)
    
    if results.empty:
        print("No architect stats found.")
        return
        
    # Sort by Total Points Created? Or Per Game?
    # User might prefer Volume or Efficiency.
    # Let's do Total Points Created for "The Architect" title.
    
    top_architects = results.sort_values('PointsCreated', ascending=False).head(20)
    
    print("\nTop 20 'Architects' (Points Created via Assists):")
    print(top_architects[['PlayerName', 'PointsCreated', 'Assists', 'PointsCreatedPerGame', 'PPC_Ratio']].to_string(index=False))
    
    # Save JSON
    top_architects.to_json("the_architect.json", orient='records', indent=4)
    print("Saved to the_architect.json")
    
    # Visualization
    plt.figure(figsize=(12, 8))
    
    # Bar Chart
    sns.barplot(data=top_architects.head(10), x='PointsCreated', y='PlayerName', palette='viridis')
    plt.title(f"The Architect: Most Points Created via Assists ({START_SEASON}-{END_SEASON})", fontsize=16)
    plt.xlabel("Total Points Generated", fontsize=12)
    plt.ylabel(None)
    plt.tight_layout()
    plt.savefig("the_architect.png")
    print("Saved to the_architect.png")

if __name__ == "__main__":
    main()
