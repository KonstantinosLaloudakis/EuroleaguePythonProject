import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import json

# --- Configuration ---
DATA_DIR = "data"
# A "Run" is defined as X unanswered points by the opponent
RUN_THRESHOLD = 8 

def fetch_season_data(season):
    file_path = os.path.join(DATA_DIR, f"pbp_{season}.csv")
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

def analyze_silencers(df):
    silencer_counts = {} # PlayerID -> Count
    player_names = {}    # PlayerID -> Name
    player_teams = {}    # PlayerID -> TeamCode
    
    games = df['Gamecode'].unique()
    
    for game_code in games:
        # Sort by NUMBEROFPLAY to ensure chronological order
        game_df = df[df['Gamecode'] == game_code].sort_values('NUMBEROFPLAY')
        
        # We need to track the "Current Run"
        # Since we have two teams, we track runs for both separately?
        # No, a run is defined by who is scoring consecutively.
        
        # Let's iterate events
        # We need to identify scoringplays and who scored them.
        
        # Scoring Plays: 2FGM, 3FGM, FTM, DUNK, LAYUPMD
        scoring_plays = ['2FGM', '3FGM', 'FTM', 'DUNK', 'LAYUPMD']
        
        # PlayType mapping to points
        def get_points(playtype):
            if '3FG' in playtype: return 3
            if 'FT' in playtype: return 1
            return 2
            
        # State
        current_run_team = None
        current_run_score = 0
        
        teams = game_df['CODETEAM'].dropna().unique()
        if len(teams) != 2: continue # Skip bad data
        
        # Process events
        for _, row in game_df.iterrows():
            playtype = row['PLAYTYPE']
            team = row['CODETEAM']
            player_id = row['PLAYER_ID']
            player_name = row['PLAYER']
            
            if pd.isna(team): continue
            
            if playtype in scoring_plays:
                points = get_points(playtype)
                
                # Update Player Info
                if pd.notna(player_id):
                    player_names[player_id] = player_name
                    player_teams[player_id] = team
                
                if team == current_run_team:
                    # Run continues
                    current_run_score += points
                else:
                    # Run BROKEN by 'team'
                    # Check if previous run was substantial
                    if current_run_score >= RUN_THRESHOLD:
                        # This shot is a SILENCER
                        if pd.notna(player_id):
                             silencer_counts[player_id] = silencer_counts.get(player_id, 0) + 1
                    
                    # Reset run
                    current_run_team = team
                    current_run_score = points
                    
            # Should free throws count as extending a run? Yes.
            # Should missed shots break a run? No, only scoring breaks a run.
            
    print(f"Total Silencers found in season: {len(silencer_counts)} players involved.")
    # Convert to DataFrame
    performances = []
    for pid, count in silencer_counts.items():
        performances.append({
            'PlayerID': pid,
            'PlayerName': player_names.get(pid, pid),
            'TeamCode': player_teams.get(pid, "UNK"),
            'SilencerShots': count
        })
        
    return pd.DataFrame(performances)

def main():
    start_season = 2007
    end_season = 2025
    
    print(f"Analyzing 'The Silencer' ({RUN_THRESHOLD}+ pt run stoppers) from {start_season} to {end_season}...")
    
    all_seasons_df = pd.DataFrame()
    
    # We can process season by season and aggregate
    aggregated_counts = {} # PID -> {Name, Team, Count}
    
    for season in range(start_season, end_season + 1):
        print(f"Loading season {season}...")
        df = fetch_season_data(season)
        if df.empty: 
            # print("Skipping empty season df")
            continue
        
        season_silencers = analyze_silencers(df)

        
        if not season_silencers.empty:
            for _, row in season_silencers.iterrows():
                pid = row['PlayerID']
                if pid not in aggregated_counts:
                    aggregated_counts[pid] = {
                        'PlayerName': row['PlayerName'],
                        'TeamCode': row['TeamCode'], # Note: Players change teams. We might need a list or just latest.
                        'SilencerShots': 0,
                        'Teams': set()
                    }
                
                aggregated_counts[pid]['SilencerShots'] += row['SilencerShots']
                aggregated_counts[pid]['Teams'].add(row['TeamCode'])
                
    # Final List
    final_list = []
    team_mapping = load_team_names()
    
    for pid, data in aggregated_counts.items():
        # Resolve Team Name (join if multiple)
        # Using the mapping
        team_names = []
        for code in data['Teams']:
            t_name = team_mapping.get(code, code)
            team_names.append(t_name)
        
        # If too many teams, maybe just list "Multiple"? 
        # Or join top 2?
        # Let's just create a string, truncate if long
        team_display = ", ".join(sorted(list(set(team_names))))
        if len(team_display) > 50:
            team_display = team_display[:47] + "..."
            
        final_list.append({
            'PlayerName': data['PlayerName'],
            'TeamName': team_display,
            'SilencerShots': data['SilencerShots']
        })
        
    final_df = pd.DataFrame(final_list)
    
    if not final_df.empty:
        # Sort
        top_silencers = final_df.sort_values('SilencerShots', ascending=False).head(20)
        
        print("\nTop 20 'Silencers' (Shots stopping 8+ pt runs):")
        print(top_silencers.to_string(index=False))
        
        # Save
        top_silencers.to_json("silencer.json", orient='records', indent=4)
        print("Saved silencer.json")
        
        # Visualize Top 10
        try:
            plt.figure(figsize=(12, 8))
            plot_data = top_silencers.head(10).copy()
            
            # Label
            plot_data['Label'] = plot_data['PlayerName'] + "\n" + plot_data['TeamName']
            
            sns.barplot(data=plot_data, x='SilencerShots', y='Label', palette='coolwarm')
            plt.title("The Silencer: Most Shots stopping 8+ point Opponent Runs (2007-2025)", fontsize=16)
            plt.xlabel("Number of Silencer Shots", fontsize=12)
            plt.ylabel(None)
            plt.tight_layout()
            plt.savefig("silencer.png")
            print("Saved silencer.png")
        except Exception as e:
            print(f"Error plotting: {e}")

if __name__ == "__main__":
    main()
