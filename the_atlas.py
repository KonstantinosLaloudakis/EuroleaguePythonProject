import pandas as pd
import numpy as np
import os
import json
import matplotlib.pyplot as plt
import seaborn as sns

# Reuse caching logic
CACHE_DIR = "data"
os.makedirs(CACHE_DIR, exist_ok=True)

def fetch_season_data(season):
    file_path = os.path.join(CACHE_DIR, f"pbp_{season}.csv")
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    return pd.DataFrame()

def parse_column_string(col_str):
    """Parses a dataframe-like string into a dict {index: value}"""
    result = {}
    lines = col_str.strip().split('\n')
    for line in lines:
        parts = line.strip().split(None, 1)
        if len(parts) >= 2:
            idx_str = parts[0]
            val = parts[1]
            try:
                idx = int(idx_str)
                result[idx] = val
            except ValueError:
                continue
    return result

def load_team_names():
    try:
        with open("teamNames.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            
        codes_map = parse_column_string(data['team1'])
        names_map = parse_column_string(data['team2'])
        
        mapping = {}
        common_indices = set(codes_map.keys()) & set(names_map.keys())
        
        # Use setdefault to keep the FIRST mapping (lower index)
        # This avoids bad overwrites like PAN -> Baskonia appearing later in the file
        for idx in sorted(common_indices):
            code_entry = codes_map[idx].strip()
            name_entry = names_map[idx].strip()
            
            sub_codes = code_entry.split(';')
            for sc in sub_codes:
                sc = sc.strip()
                if sc:
                    mapping.setdefault(sc, name_entry)
                    
        return mapping
    except FileNotFoundError:
        return {}

def get_game_seconds(row):
    """Converts MARKERTIME (MM:SS) to game seconds (descending from 40:00 or 10:00)."""
    # Actually, MARKERTIME is usually remaining time in quarter.
    # But we need absolute time for ordering?
    # Or just relative seconds from string for fuzzy matching.
    time_str = str(row['MARKERTIME'])
    if ':' not in time_str:
        return 0
    
    mm, ss = map(int, time_str.split(':'))
    
    # We need a continuous time to sort events properly?
    # Actually, events are already ordered in the CSV (usually).
    # But we want to do a fuzzy match on time.
    # Let's just return total seconds in the quarter.
    return mm * 60 + ss

def format_game_time(total_seconds):
    """Simple formatter."""
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"

def analyze_atlas(df, season):
    atlas_performances = []
    
    # Filter for relevant seasons if needed, but 'df' is passed per season loop usually?
    # Here we process the whole df passed in.
    
    # 1. Calculate Score Values
    # Map PLAYTYPE to Points
    # 2FGM -> 2, 3FGM -> 3, FTM -> 1
    
    # Strip whitespace just in case
    df['PLAYTYPE'] = df['PLAYTYPE'].astype(str).str.strip()
    df['CODETEAM'] = df['CODETEAM'].astype(str).str.strip()
    
    df['PointValue'] = 0
    df.loc[df['PLAYTYPE'] == '2FGM', 'PointValue'] = 2
    df.loc[df['PLAYTYPE'] == '3FGM', 'PointValue'] = 3
    df.loc[df['PLAYTYPE'] == 'FTM', 'PointValue'] = 1
    df.loc[df['PLAYTYPE'] == 'LAYUPMD', 'PointValue'] = 2
    df.loc[df['PLAYTYPE'] == 'DUNK', 'PointValue'] = 2
    
    # Convert Time
    df['QuarterSeconds'] = df.apply(get_game_seconds, axis=1)
    
    # Group by Game
    grouped_games = df.groupby('Gamecode')
    
    for game_code, game_df in grouped_games:
        # Sort by index to maintain event order (assuming CSV is ordered)
        # But for time proximity, we need the seconds.
        # Let's trust the index order is roughly chronological, but we check seconds for proximity.
        
        # Calculate Team Totals
        team_points = game_df.groupby('CODETEAM')['PointValue'].sum()
        
        if len(team_points) < 2:
            continue # Skip games with missing data
            
        # Get Teams
        teams = game_df['CODETEAM'].unique()
        valid_teams = [t for t in teams if t.upper() != 'NAN' and len(t) > 0]
        
        for team in valid_teams:
            total_team_points = team_points.get(team, 0)
            if total_team_points < 50: # Filter out low scoring/incomplete games
                continue
            
            team_events = game_df[game_df['CODETEAM'] == team].copy()
            
            # --- Calculate Points Generated ---
            
            # 1. Scored Points
            player_points = team_events.groupby('PLAYER_ID')['PointValue'].sum()
            
            # 2. Assisted Points
            # ... (omitted for brevity, assume assist logic here)
            # We need to link AS events to Point events
            # Logic: For each AS, find scores within ±4 seconds
            
            # Optimization: 1-to-1 matching of Assists to Scores

            
            # 2. Assisted Points
            # We need to link AS events to Point events
            # Logic: For each AS, find scores within ±4 seconds
            
            # Optimization: 1-to-1 matching of Assists to Scores
            # We iterate through assists and find the single closest score group.
            
            # Create a list of score events with their time and value
            # We treat consecutive FTMs by same player as one "Score Event"
            
            score_groups = []
            # ... preprocessing to group FTMs is complex.
            # Simpler: Iterate assists. Find nearest score. Use it.
            # But we must avoid re-using the score if we had 2 fast breaks.
            # Given limited assist density, simple nearest unclaim is fine.
            
            # Sort events by Index (Time)
            team_events = team_events.sort_index()
            
            assist_points = {} # PlayerID -> Points
            
            assist_indices = team_events[team_events['PLAYTYPE'] == 'AS'].index
            score_indices = team_events[team_events['PointValue'] > 0].index
            
            claimed_scores = set()
            
            for as_idx in assist_indices:
                assister_id = team_events.loc[as_idx, 'PLAYER_ID']
                as_time = team_events.loc[as_idx, 'QuarterSeconds']
                
                # Find closest score index
                # We care about index distance primarily (adjacency)
                # But time distance as sanity check (e.g. < 5 sec)
                
                best_s_idx = None
                best_dist = float('inf')
                
                # Search locally
                # We can search the whole score_indices array efficiently or just local window
                # Let's search all scores (game is small) but pick closest
                
                # Filter for scores within ±5 indcies
                # fast approximation
                
                # Let's iterate all scores (max 100 per game) - it's fast.
                for s_idx in score_indices:
                    if s_idx in claimed_scores:
                        continue
                        
                    # Index distance
                    dist = abs(s_idx - as_idx)
                    
                    if dist > 8: # Optimization: skip far events
                        continue
                        
                    # Time distance check
                    s_time = team_events.loc[s_idx, 'QuarterSeconds']
                    time_diff = abs(s_time - as_time)
                    
                    if time_diff > 4: # Must be close in time
                        continue
                    
                    # Tie breaker: Prefer score BEFORE assist? Or same time.
                    # Usually Score is just before or same time.
                    # We prefer smallest dist.
                    
                    if dist < best_dist:
                        best_dist = dist
                        best_s_idx = s_idx
                
                if best_s_idx is not None:
                    # Found a score.
                    # If it's FTM, check for siblings (e.g. 2/2)
                    # We claim this one. And any adjacent FTMs by same player?
                    # Actually, if the assist is for the foul, it covers all FTs.
                    # So we should sum all FTMs in that cluster.
                    
                    base_score_row = team_events.loc[best_s_idx]
                    pts = base_score_row['PointValue']
                    claimed_scores.add(best_s_idx)
                    
                    if base_score_row['PLAYTYPE'] == 'FTM':
                         # Look for neighbors
                         shooter = base_score_row['PLAYER_ID']
                         # Look adjacent
                         for offset in [-1, -2, 1, 2]:
                             neighbor_idx = best_s_idx + offset
                             if neighbor_idx in team_events.index and \
                                neighbor_idx not in claimed_scores and \
                                team_events.loc[neighbor_idx, 'PLAYTYPE'] == 'FTM' and \
                                team_events.loc[neighbor_idx, 'PLAYER_ID'] == shooter:
                                    
                                    # Claim it too
                                    pts += team_events.loc[neighbor_idx, 'PointValue']
                                    claimed_scores.add(neighbor_idx)
                    
                    if pd.notna(assister_id):
                        assist_points[assister_id] = assist_points.get(assister_id, 0) + pts

            # --- Aggregate ---
            # Get list of all players
            all_players = set(player_points.index) | set(assist_points.keys())
            
            for player_id in all_players:
                if not isinstance(player_id, str): continue
                
                p_scored = player_points.get(player_id, 0)
                p_assisted = assist_points.get(player_id, 0)
                p_generated = p_scored + p_assisted
                
                # Find Opponent
                opponent = "Unknown"
                opponent_score = 0
                for t in valid_teams:
                    if t != team:
                        opponent = t
                        opponent_score = team_points.get(t, 0)
                        break
                
                atlas_index = (p_generated / total_team_points) * 100
                
                # Player Name (take first occurrence)
                p_name_rows = team_events[team_events['PLAYER_ID'] == player_id]
                p_name = p_name_rows['PLAYER'].iloc[0] if not p_name_rows.empty else player_id
                
                # Filter out known bad data
                # Shved 2018 Game 5 (Missing 16 points, 66 vs 82)
                if int(season) == 2018 and int(game_code) == 5 and player_id == 'PKVZ':
                    continue
                
                atlas_performances.append({
                    'Season': int(season),
                    'Gamecode': int(game_code),
                    'PlayerID': player_id,
                    'PlayerName': p_name,
                    'TeamCode': team,
                    'OpponentCode': opponent,
                    'TeamScore': int(total_team_points),
                    'OpponentScore': int(opponent_score),
                    'PointsScored': int(p_scored),
                    'PointsAssisted': int(p_assisted),
                    'PointsGenerated': int(p_generated),
                    'TeamTotalPoints': int(total_team_points),
                    'AtlasIndex': round(atlas_index, 2)
                })

    return atlas_performances

def main():
    start_season = 2007
    end_season = 2025
    
    print(f"Analyzing 'The Atlas' performances from {start_season} to {end_season}...")
    
    all_performances = []
    
    for season in range(start_season, end_season + 1):
        print(f"Loading data for season {season}...")
        df = fetch_season_data(season)
        if not df.empty:
            results = analyze_atlas(df, season)
            all_performances.extend(results)
            
    # Create DataFrame
    atlas_df = pd.DataFrame(all_performances)
    
    if not atlas_df.empty:
        # Load Team Names
        team_mapping = load_team_names()
        atlas_df['TeamName'] = atlas_df['TeamCode'].apply(lambda x: team_mapping.get(x, x))
        atlas_df['OpponentName'] = atlas_df['OpponentCode'].apply(lambda x: team_mapping.get(x, x))
        
        # Sort by Atlas Index
        top_atlas = atlas_df.sort_values('AtlasIndex', ascending=False).head(20)
        
        print("\nTop 10 Atlas Performances (Highest % of Team Points Generated):")
        print(top_atlas[['PlayerName', 'TeamName', 'PointsGenerated', 'TeamTotalPoints', 'AtlasIndex']].head(10))
        
        # Save
        filename = "atlas.json"
        top_atlas.to_json(filename, orient='records', indent=4)
        print(f"Saved {filename}")
        
        # Visualize
        try:
            plt.figure(figsize=(14, 10))
            
            plot_data = top_atlas.head(10).copy()
            
            plot_data['Label'] = (
                plot_data['PlayerName'] + "\n" +
                plot_data['TeamName'] + " " + plot_data['TeamScore'].astype(str) + " - " + plot_data['OpponentScore'].astype(str) + " " + plot_data['OpponentName'] + "\n" +
                "Season " + plot_data['Season'].astype(str) + "\n" +
                "Scored: " + plot_data['PointsScored'].astype(str) + " | Ast Pts: " + plot_data['PointsAssisted'].astype(str) + "\n" +
                "Total Gen: " + plot_data['PointsGenerated'].astype(str) + " (" + plot_data['AtlasIndex'].round(1).astype(str) + "%)"
            )
            
            sns.barplot(data=plot_data, x='AtlasIndex', y='Label', palette='viridis')
            plt.title(f"The Atlas: Highest % of Team Points Generated ({start_season}-{end_season})", fontsize=16)
            plt.xlabel("% of Team Points Generated (Scored + Assisted)", fontsize=12)
            plt.ylabel("Player Performance", fontsize=12)
            plt.tight_layout()
            plt.savefig("atlas.png")
            print("Saved atlas.png")
        except Exception as e:
            print(f"Error plotting: {e}")

if __name__ == "__main__":
    main()
