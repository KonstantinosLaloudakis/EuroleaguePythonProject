import pandas as pd
import json

def calculate_mvp_scores_2024():
    # Load Parsed Game Stats
    try:
        df_games = pd.read_json('mvp_parsed_games_2024.json')
    except ValueError:
        print("No parsed games found.")
        return

    # Load Derived Standings
    with open('mvp_standings_derived_2024.json', 'r') as f:
        standings = json.load(f)

    # Load Clutch Stats
    try:
        with open('clutch_stats_2024_2024.json', 'r') as f:
            clutch_data = json.load(f)
        # Clutch data structure: {'2024': [ {...}, ... ]}
        clutch_list = clutch_data.get('2024', [])
        df_clutch = pd.DataFrame(clutch_list)
    except (FileNotFoundError, ValueError):
        print("Clutch stats not found! Proceeding without (zeros).")
        df_clutch = pd.DataFrame(columns=['Player', 'ClutchPoints'])

    print(f"Loaded {len(df_games)} player-games.")
    
    # DETERMINE PRIMARY TEAM for each player
    player_teams = df_games.groupby(['PlayerCode', 'PlayerName'])['TeamCode'].agg(lambda x: x.mode().iloc[0] if not x.mode().empty else "UNKNOWN").reset_index()
    player_teams.rename(columns={'TeamCode': 'PrimaryTeam'}, inplace=True)
    
    df_games = pd.merge(df_games, player_teams[['PlayerCode', 'PrimaryTeam']], on='PlayerCode', how='left')
    
    # Aggregated Base Stats
    player_stats = df_games.groupby(['PlayerCode', 'PlayerName', 'PrimaryTeam']).agg({
        'GmSc': 'mean',
        'GameCode': 'count', 
        'PTS': 'mean',
        'PIR': 'mean' 
    }).reset_index()
    
    player_stats.rename(columns={'GameCode': 'GP', 'PrimaryTeam': 'TeamCode'}, inplace=True)
    
    # Filter small sample size
    player_stats = player_stats[player_stats['GP'] >= 5]
    
    # Team Impact
    def get_win_pct(team_code):
        return standings.get(team_code, {}).get('WinPct', 0.5) # Default 0.5 if unknown?
        
    player_stats['TeamWinPct'] = player_stats['TeamCode'].apply(get_win_pct)
    
    # Rank Bonus
    sorted_standings = sorted(standings.items(), key=lambda x: x[1]['WinPct'], reverse=True)
    rank_map = {k: i+1 for i, (k, v) in enumerate(sorted_standings)}
    
    player_stats['TeamRank'] = player_stats['TeamCode'].map(rank_map).fillna(18)
    
    def get_rank_multiplier(rank):
        if rank <= 4: return 1.10
        if rank <= 8: return 1.05
        return 1.0
        
    player_stats['RankMultiplier'] = player_stats['TeamRank'].apply(get_rank_multiplier)

    # 4. Usage/Value Factor (Points Share)
    team_points = df_games.groupby('TeamCode')['PTS'].sum().to_dict()
    
    def get_points_share(row):
        t_pts = team_points.get(row['TeamCode'], 0)
        if t_pts == 0: return 0
        return (row['PTS'] * row['GP']) / t_pts

    player_stats['PointsShare'] = player_stats.apply(get_points_share, axis=1)
    
    # 5. Clutch Factor
    if not df_clutch.empty:
        df_clutch['PlayerUpper'] = df_clutch['Player'].str.upper().str.strip()
        player_stats['PlayerUpper'] = player_stats['PlayerName'].str.upper().str.strip()
        
        merged = pd.merge(player_stats, df_clutch[['PlayerUpper', 'ClutchPoints']], on='PlayerUpper', how='left')
        merged['ClutchPoints'].fillna(0, inplace=True)
    else:
        merged = player_stats.copy()
        merged['ClutchPoints'] = 0
        
    merged['ClutchPPG'] = merged['ClutchPoints'] / merged['GP']
    
    # Normalization
    def normalize(series):
        if series.max() == series.min(): return 0
        return (series - series.min()) / (series.max() - series.min()) * 100
        
    merged['GmSc_Norm'] = normalize(merged['GmSc'])
    merged['Team_Norm'] = normalize(merged['TeamWinPct'])
    merged['Clutch_Norm'] = normalize(merged['ClutchPPG'])
    merged['Share_Norm'] = normalize(merged['PointsShare'])
    
    # Final Formula (Matches 2025 weights)
    # Weights: Base 60%, Team 20%, Clutch 10%, Share 10%
    
    merged['MVP_Score'] = (
        (merged['GmSc_Norm'] * 0.60) + 
        (merged['Team_Norm'] * 0.20 * merged['RankMultiplier']) + 
        (merged['Clutch_Norm'] * 0.10) +
        (merged['Share_Norm'] * 0.10)
    )
    
    # Sort and Rank
    merged.sort_values('MVP_Score', ascending=False, inplace=True)
    merged['MVP_Rank'] = range(1, len(merged) + 1)
    
    # Output Top 20
    cols = ['MVP_Rank', 'PlayerName', 'TeamCode', 'MVP_Score', 'GmSc', 'TeamWinPct', 'ClutchPoints', 'GP']
    print("\n--- MVP LADDER 2024 (VALIDATION) ---")
    print(merged[cols].head(20).to_string(index=False))
    
    merged.to_json('mvp_rankings_2024.json', orient='records', indent=4)
    print("Saved mvp_rankings_2024.json")

if __name__ == "__main__":
    calculate_mvp_scores_2024()
