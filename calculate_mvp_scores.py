import pandas as pd
import json
import numpy as np

def calculate_mvp_scores():
    # 1. Load Data
    try:
        df_games = pd.read_json('mvp_parsed_games.json')
        # Scores are in game_results
        with open('mvp_standings_derived.json', 'r') as f:
            standings = json.load(f)
        
        with open('clutch_stats_2025_2025.json', 'r') as f:
            clutch_data = json.load(f)
            # Clutch data is keyed by "2025" list
            clutch_list = clutch_data.get('2025', [])
            df_clutch = pd.DataFrame(clutch_list)
            
    except Exception as e:
        print(f"Error loading data: {e}")
        return

    print(f"Loaded {len(df_games)} player-games.")
    
    # DETERMINE PRIMARY TEAM for each player (Mode of TeamCode)
    # This fixes issues where a player breaks into 2 rows (e.g. De Colo ULK/ASV error)
    player_teams = df_games.groupby(['PlayerCode', 'PlayerName'])['TeamCode'].agg(lambda x: x.mode().iloc[0] if not x.mode().empty else "UNKNOWN").reset_index()
    player_teams.rename(columns={'TeamCode': 'PrimaryTeam'}, inplace=True)
    
    # Merge Primary Team back
    df_games = pd.merge(df_games, player_teams[['PlayerCode', 'PrimaryTeam']], on='PlayerCode', how='left')
    
    # 2. Aggregated Base Stats
    # Group by Player and PRIMARY TEAM
    player_stats = df_games.groupby(['PlayerCode', 'PlayerName', 'PrimaryTeam']).agg({
        'GmSc': 'mean',
        'GameCode': 'count', # Games Played
        'PTS': 'mean',
        'PIR': 'mean' 
    }).reset_index()
    
    # Rename PrimaryTeam to TeamCode for consistency downstream
    player_stats.rename(columns={'GameCode': 'GP', 'PrimaryTeam': 'TeamCode'}, inplace=True)
    
    # Filter small sample size
    player_stats = player_stats[player_stats['GP'] >= 5]
    
    # Efficiency Bonus (TS%) - skipped for now
    
    # 3. Team Impact
    # Add Win % from local standings file
    # We need to map TeamCode to Standings
    
    standings_map = {k: v['WinPct'] for k, v in standings.items()}
    player_stats['TeamWinPct'] = player_stats['TeamCode'].map(standings_map).fillna(0)
    
    # Rank Bonus
    # Sort standings by percentage
    sorted_standings = sorted(standings.items(), key=lambda x: x[1]['WinPct'], reverse=True)
    rank_map = {k: i+1 for i, (k, v) in enumerate(sorted_standings)}
    
    player_stats['TeamRank'] = player_stats['TeamCode'].map(rank_map).fillna(18)
    
    def get_rank_multiplier(rank):
        if rank <= 4: return 1.10
        if rank <= 8: return 1.05
        return 1.0
        
    player_stats['RankMultiplier'] = player_stats['TeamRank'].apply(get_rank_multiplier)

    # 4. Usage/Value Factor (Points Share)
    # Calculate Team Total Points
    team_points = df_games.groupby('TeamCode')['PTS'].sum().to_dict()
    
    def get_points_share(row):
        t_pts = team_points.get(row['TeamCode'], 0)
        if t_pts == 0: return 0
        # Player Total Points (PTS * GP) / Team Total Points (approx)
        # Note: df_games has all games. Team Total is sum of all player points in df_games.
        # Player Share = (Player Avg PTS * Player GP) / Team Total Points
        # Actually, simpler: Player Total Points / Team Total Points in dataset.
        return (row['PTS'] * row['GP']) / t_pts

    player_stats['PointsShare'] = player_stats.apply(get_points_share, axis=1)

    # 5. Clutch Factor
    # ... (Clutch logic remains) ...
    
    # Merge Clutch Data
    # Clean names in df_clutch
    df_clutch['PlayerUpper'] = df_clutch['Player'].str.upper().str.strip()
    player_stats['PlayerUpper'] = player_stats['PlayerName'].str.upper().str.strip()
    
    # Merge
    merged = pd.merge(player_stats, df_clutch[['PlayerUpper', 'ClutchPoints', 'ClutchFGM', 'ClutchFGA']], on='PlayerUpper', how='left')
    merged['ClutchPoints'].fillna(0, inplace=True)
    
    merged['ClutchPPG'] = merged['ClutchPoints'] / merged['GP']
    
    # Normalization for Scores
    def normalize(series):
        return (series - series.min()) / (series.max() - series.min()) * 100
        
    merged['GmSc_Norm'] = normalize(merged['GmSc'])
    merged['Team_Norm'] = normalize(merged['TeamWinPct'])
    merged['Clutch_Norm'] = normalize(merged['ClutchPPG'])
    merged['Share_Norm'] = normalize(merged['PointsShare'])
    
    # 6. Final Formula
    # Weights: Base 60%, Team 20%, Clutch 10%, Share 10%
    
    merged['MVP_Score'] = (
        (merged['GmSc_Norm'] * 0.60) + 
        (merged['Team_Norm'] * 0.20 * merged['RankMultiplier']) + 
        (merged['Clutch_Norm'] * 0.10) +
        (merged['Share_Norm'] * 0.10)
    )
    
    # Sort and Ranking
    merged.sort_values('MVP_Score', ascending=False, inplace=True)
    
    merged['MVP_Rank'] = range(1, len(merged) + 1)
    
    # Select columns
    final_cols = ['MVP_Rank', 'PlayerName', 'TeamCode', 'MVP_Score', 'GmSc', 'TeamWinPct', 'ClutchPoints', 'GP']
    top_20 = merged[final_cols].head(20)
    
    print("\n--- MVP LADDER TOP 20 ---")
    print(top_20.to_string(index=False))
    
    # Save
    merged[final_cols].to_json('mvp_rankings_2025.json', orient='records', indent=4)
    print("\nSaved mvp_rankings_2025.json")

if __name__ == "__main__":
    calculate_mvp_scores()
