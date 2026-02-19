import pandas as pd
import json
import numpy as np

def verify_oracle():
    # 0. Load Round Map
    try:
        with open('game_code_to_round.json', 'r') as f:
            round_map = json.load(f)
        print(f"Loaded Round Map for {len(round_map)} games.")
    except FileNotFoundError:
        print("Error: game_code_to_round.json not found. Run parse_schedule_xml.py first.")
        return

    # 1. Load Data
    try:
        df = pd.read_json('mvp_game_results.json')
    except Exception as e:
        print(f"Error loading mvp_game_results.json: {e}")
        return

    # Filter for played games
    played = df[(df['LocalScore'] > 0) & (df['RoadScore'] > 0)].copy()
    if played.empty:
        print("No played games found.")
        return

    # 2. Calculate Global Stats (HCA & Ratings)
    # Note: Using End-of-Season ratings to predict past games (Hindsight Analysis)
    # This checks if the formula ITSELF is valid given true team strengths.
    avg_local = played['LocalScore'].mean()
    avg_road = played['RoadScore'].mean()
    hca = avg_local - avg_road
    print(f"Global HCA: +{hca:.2f}")

    teams = {}
    for _, row in played.iterrows():
        local, road = row['LocalTeam'], row['RoadTeam']
        l_pts, r_pts = row['LocalScore'], row['RoadScore']
        
        if local not in teams: teams[local] = {'PTS': 0, 'PA': 0, 'GP': 0}
        if road not in teams: teams[road] = {'PTS': 0, 'PA': 0, 'GP': 0}
        
        teams[local]['PTS'] += l_pts
        teams[local]['PA'] += r_pts
        teams[local]['GP'] += 1
        
        teams[road]['PTS'] += r_pts
        teams[road]['PA'] += l_pts
        teams[road]['GP'] += 1

    team_stats = {}
    for t, s in teams.items():
        if s['GP'] > 0:
            team_stats[t] = {
                'Net': (s['PTS'] - s['PA']) / s['GP']
            }
        else:
            team_stats[t] = {'Net': 0}

    # 3. Simulate Predictions
    correct = 0
    total = 0
    margin_errors = []
    upsets = []

    for _, row in played.iterrows():
        game_code = str(row['GameCode'])
        
        # Determine Round
        if game_code in round_map:
            round_num = round_map[game_code]
        else:
            # Fallback (should not happen if map is complete)
            round_num = ((int(game_code) - 1) // 9) + 1
            
        local = row['LocalTeam']
        road = row['RoadTeam']
        actual_margin = row['LocalScore'] - row['RoadScore']
        actual_winner = row['Winner']

        # Oracle Logic
        l_net = team_stats.get(local, {'Net': 0})['Net']
        r_net = team_stats.get(road, {'Net': 0})['Net']
        
        predicted_margin = (l_net - r_net) + hca
        predicted_winner = local if predicted_margin > 0 else road
        
        # Accuracy
        if predicted_winner == actual_winner:
            correct += 1
        
        # Error
        error = abs(predicted_margin - actual_margin)
        margin_errors.append(error)
        
        deviation = actual_margin - predicted_margin
        
        # Upset: Pred Winner lost
        is_upset = (predicted_winner != actual_winner)
        
        game_info = {
            'GameCode': row['GameCode'],
            'Round': round_num,
            'Matchup': f"{local} vs {road}",
            'PredictedMargin': round(predicted_margin, 2),
            'ActualMargin': float(actual_margin),
            'Deviation': round(deviation, 2),
            'Error': round(error, 2),
            'IsUpset': bool(is_upset),
            'Winner': actual_winner,
            'PredictedWinner': predicted_winner
        }
        upsets.append(game_info)
        total += 1

    # 4. Results
    accuracy = (correct / total) * 100
    mae = np.mean(margin_errors)
    
    print(f"Total Games Verified: {total}")
    print(f"Oracle Accuracy: {accuracy:.1f}% ({correct}/{total})")
    print(f"Mean Margin Error: {mae:.2f} pts")
    
    # Sort by Error (Biggest Surprises)
    failed_preds = [g for g in upsets if g['IsUpset']]
    top_upsets = sorted(failed_preds, key=lambda x: x['Error'], reverse=True)[:5]

    print("\n--- TOP 5 BIGGEST UPSETS (CHAOS GAMES) ---")
    for i, g in enumerate(top_upsets):
        print(f"{i+1}. {g['Matchup']} (Rd {g['Round']}) | Pred: {g['PredictedWinner']} +{abs(g['PredictedMargin'])} | Actual: {g['Winner']} +{abs(g['ActualMargin'])} | Swing: {g['Error']} pts")

    # Save Report
    report = {
        'Accuracy': accuracy,
        'TotalGames': total,
        'MAE': mae,
        'TopUpsets': top_upsets
    }
    
    with open('oracle_verification_report.json', 'w') as f:
        json.dump(report, f, indent=4)
    print("\nReport saved to oracle_verification_report.json")

    # Save Full Game History (User Request)
    with open('oracle_games_history.json', 'w') as f:
        json.dump(upsets, f, indent=4)
    print("Full history saved to oracle_games_history.json")

    # 5. Predicted Rankings (User Request)
    # Aggregating predicted wins
    pred_standings = {t: {'PredW': 0, 'PredL': 0, 'ActW': 0, 'ActL': 0} for t in team_stats.keys()}
    
    for g in upsets:
        pw = g['PredictedWinner']
        aw = g['Winner']
        
        # Infer loser (Matchup is "Local vs Road")
        # simple parse
        teams_in_game = g['Matchup'].split(' vs ')
        if len(teams_in_game) != 2: continue # Should not happen
        
        t1, t2 = teams_in_game
        pl = t2 if pw == t1 else t1
        al = t2 if aw == t1 else t1
        
        if pw in pred_standings: pred_standings[pw]['PredW'] += 1
        if pl in pred_standings: pred_standings[pl]['PredL'] += 1
        
        if aw in pred_standings: pred_standings[aw]['ActW'] += 1
        if al in pred_standings: pred_standings[al]['ActL'] += 1

    # Convert to list and sort
    ranking_list = []
    for t, s in pred_standings.items():
        ranking_list.append({
            'Team': t,
            'PredictedW': s['PredW'],
            'PredictedL': s['PredL'],
            'ActualW': s['ActW'],
            'ActualL': s['ActL'],
            'Delta': s['ActW'] - s['PredW'] # Positive = Team overperformed Oracle
        })
    
    # Sort by Predicted Wins
    ranking_list.sort(key=lambda x: x['PredictedW'], reverse=True)
    
    # Save
    with open('oracle_predicted_standings.json', 'w') as f:
        json.dump(ranking_list, f, indent=4)
    print("Predicted Standings saved to oracle_predicted_standings.json")

    # 6. Visualization
    import matplotlib.pyplot as plt
    
    # A. Accuracy by Round
    df_ver = pd.DataFrame(upsets)
    
    # Group by Round (using Official Round)
    round_counts = df_ver['Round'].value_counts().sort_index()
    print("\n--- Games Verified Per Round ---")
    print(round_counts)
    
    round_acc = df_ver.groupby('Round').apply(lambda x: (x['PredictedWinner'] == x['Winner']).mean() * 100)
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10))
    
    # Plot 1: Accuracy Trend
    ax1.plot(round_acc.index, round_acc.values, marker='o', linestyle='-', color='#1d428a', linewidth=2)
    ax1.axhline(y=accuracy, color='green', linestyle='--', label=f'Avg Accuracy ({accuracy:.1f}%)')
    ax1.set_title("Oracle Accuracy by Round (Official Schedule)", fontsize=14, fontweight='bold')
    ax1.set_ylabel("Accuracy (%)")
    ax1.set_xlabel("Round")
    ax1.set_ylim(0, 100)
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Plot 2: Top 5 Upsets (Bar Chart)
    upset_labels = [f"{g['Matchup']}\n(Swing: {g['Error']}pts)" for g in top_upsets]
    upset_values = [g['Error'] for g in top_upsets]
    
    colors = ['#ff4b4b', '#ff7676', '#ff9e9e', '#ffc2c2', '#ffe6e6']
    ax2.barh(upset_labels, upset_values, color=colors)
    ax2.invert_yaxis() # Top upset at top
    ax2.set_title("Top 5 'Chaos Games' (Biggest Prediction Misses)", fontsize=14, fontweight='bold')
    ax2.set_xlabel("Margin Swing (Points)")
    
    plt.tight_layout()
    outfile = "oracle_performance_analysis.png"
    plt.savefig(outfile, dpi=150)
    print(f"Visualization saved to {outfile}")

if __name__ == "__main__":
    verify_oracle()
