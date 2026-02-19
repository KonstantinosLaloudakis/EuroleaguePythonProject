import pandas as pd
import json
import numpy as np

def verify_oracle():
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
        
        # Upset Score (Signed deviation relative to prediction)
        # If Pred +10 (Home big fav) and Actual -10 (Away big win), Diff = -20
        # If Pred -5 (Away fav) and Actual +5 (Home win), Diff = +10
        # We want "Ranking Deviation".
        # Let's simply track "Margin Deviation" = Actual - Predicted
        deviation = actual_margin - predicted_margin
        
        # An "Upset" is when the deviation is large and goes AGAINST the prediction
        # i.e., Pred > 0 but Actual < 0 (Home Upset) or Pred < 0 but Actual > 0 (Away Upset)
        is_upset = (predicted_margin > 0 and actual_margin < 0) or (predicted_margin < 0 and actual_margin > 0)
        
        game_info = {
            'GameCode': row['GameCode'],
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
        print(f"{i+1}. {g['Matchup']} | Pred: {g['PredictedWinner']} +{abs(g['PredictedMargin'])} | Actual: {g['Winner']} +{abs(g['ActualMargin'])} | Swing: {g['Error']} pts")

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

    # 5. Visualization (Added)
    import matplotlib.pyplot as plt
    
    # A. Accuracy by Round
    # Assuming 9 games per round, sorted by GameCode
    df_ver = pd.DataFrame(upsets)
    df_ver['Round'] = ((df_ver['GameCode'] - 1) // 9) + 1
    
    round_acc = df_ver.groupby('Round').apply(lambda x: (x['PredictedWinner'] == x['Winner']).mean() * 100)
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10))
    
    # Plot 1: Accuracy Trend
    ax1.plot(round_acc.index, round_acc.values, marker='o', linestyle='-', color='#1d428a', linewidth=2)
    ax1.axhline(y=accuracy, color='green', linestyle='--', label=f'Avg Accuracy ({accuracy:.1f}%)')
    ax1.set_title("Oracle Accuracy by Round", fontsize=14, fontweight='bold')
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
