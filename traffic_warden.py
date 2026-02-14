import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import json

# --- Configuration ---
DATA_DIR = "data"

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

def analyze_traffic_wardens(df, season):
    # 1. Calculate Games Played per Player (from ALL events)
    # We define "Played" as having at least one event in the game.
    games_played = df.groupby('PLAYER_ID')['Gamecode'].nunique().reset_index()
    games_played.rename(columns={'Gamecode': 'GamesPlayed'}, inplace=True)
    
    # 2. Filter for RV (Foul Drawn) and Count
    rv_events = df[df['PLAYTYPE'] == 'RV'].copy()
    
    if rv_events.empty:
        # If no fouls drawn, return empty or zeroed (but we need names)
        # For simplicity, let's just proceed.
        fouls_drawn = pd.DataFrame(columns=['PLAYER_ID', 'FoulsDrawn', 'PlayerName', 'TeamCode'])
    else:
        fouls_drawn = rv_events.groupby('PLAYER_ID').agg({
            'PLAYTYPE': 'count',
            'PLAYER': 'first',
            'CODETEAM': 'first'
        }).reset_index()
        fouls_drawn.rename(columns={'PLAYTYPE': 'FoulsDrawn', 'PLAYER': 'PlayerName', 'CODETEAM': 'TeamCode'}, inplace=True)
    
    # 3. Merge
    stats = pd.merge(games_played, fouls_drawn, on='PLAYER_ID', how='left')
    stats['FoulsDrawn'] = stats['FoulsDrawn'].fillna(0)
    
    # Fill missing names/teams for players with 0 fouls drawn?
    # We can get names from the main df if needed, but usually top players have fouls.
    # Let's try to fill Name/Team from main df if missing
    if stats['PlayerName'].isnull().any():
        # Create a mapping from main df
        player_meta = df.dropna(subset=['PLAYER_ID', 'PLAYER', 'CODETEAM']).drop_duplicates('PLAYER_ID')[['PLAYER_ID', 'PLAYER', 'CODETEAM']]
        stats = stats.drop(columns=['PlayerName', 'TeamCode'], errors='ignore') # Drop partials
        stats = pd.merge(stats, player_meta, on='PLAYER_ID', how='left')
        stats.rename(columns={'PLAYER': 'PlayerName', 'CODETEAM': 'TeamCode'}, inplace=True)

    stats['Season'] = season
    return stats

def main():
    start_season = 2007
    end_season = 2025
    
    print(f"Analyzing 'The Traffic Warden' (Fouls Drawn Per Game) from {start_season} to {end_season}...")
    
    all_seasons_stats = []
    
    for season in range(start_season, end_season + 1):
        print(f"Loading season {season}...")
        df = fetch_season_data(season)
        if df.empty: continue
        
        season_stats = analyze_traffic_wardens(df, season)
        all_seasons_stats.append(season_stats)
                    
    # Concatenate all seasons
    full_df = pd.concat(all_seasons_stats, ignore_index=True)
    
    # Filter: Min 15 games
    filtered_df = full_df[full_df['GamesPlayed'] >= 15].copy()
    
    # Calculate Metric
    filtered_df['FoulsDrawnPerGame'] = filtered_df['FoulsDrawn'] / filtered_df['GamesPlayed']
    
    # Resolve Team Names
    team_mapping = load_team_names()
    filtered_df['TeamName'] = filtered_df['TeamCode'].apply(lambda x: team_mapping.get(str(x).strip(), x))
    
    # Sort
    top_wardens = filtered_df.sort_values('FoulsDrawnPerGame', ascending=False).head(20)
    
    print("\nTop 20 'Traffic Wardens' Seasons (Fouls Drawn Per Game, Min 15 GP):")
    print(top_wardens[['PlayerName', 'Season', 'TeamName', 'GamesPlayed', 'FoulsDrawn', 'FoulsDrawnPerGame']].to_string(index=False))
    
    # Save
    top_wardens.to_json("traffic_warden.json", orient='records', indent=4)
    print("Saved traffic_warden.json")
    
    # Visualize Top 10
    try:
        plt.figure(figsize=(12, 8))
        plot_data = top_wardens.head(15).copy()
        
        # Label: Name (Season) - Team
        plot_data['Label'] = plot_data['PlayerName'] + " (" + plot_data['Season'].astype(str) + ")\n" + plot_data['TeamName']
        
        sns.barplot(data=plot_data, x='FoulsDrawnPerGame', y='Label', palette='Oranges_r')
        plt.title("The Traffic Warden: Most Fouls Drawn Per Game (Single Season, Min 15 GP)", fontsize=16)
        plt.xlabel("Fouls Drawn Per Game", fontsize=12)
        plt.ylabel(None)
        plt.tight_layout()
        plt.savefig("traffic_warden.png")
        print("Saved traffic_warden.png")
    except Exception as e:
        print(f"Error plotting: {e}")

if __name__ == "__main__":
    main()
