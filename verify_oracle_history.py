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

    played = df[(df['LocalScore'] > 0) & (df['RoadScore'] > 0)].copy()
    if played.empty:
        print("No played games found.")
        return

    # 2. Calculate Stats
    avg_local = played['LocalScore'].mean()
    avg_road = played['RoadScore'].mean()
    hca = avg_local - avg_road
    print(f"Global HCA: +{hca:.2f}")

    teams = {}
    for _, row in played.iterrows():
        local, road = row['LocalTeam'], row['RoadTeam']
        l_pts, r_pts = row['LocalScore'], row['RoadScore']
        
        for t in (local, road):
            if t not in teams:
                teams[t] = {
                    'PTS': 0, 'PA': 0, 'GP': 0,
                    'HomePTS': 0, 'HomePA': 0, 'HomeGP': 0,
                    'AwayPTS': 0, 'AwayPA': 0, 'AwayGP': 0,
                    'GameMargins': []
                }
        
        teams[local]['PTS'] += l_pts
        teams[local]['PA'] += r_pts
        teams[local]['GP'] += 1
        teams[local]['HomePTS'] += l_pts
        teams[local]['HomePA'] += r_pts
        teams[local]['HomeGP'] += 1
        teams[local]['GameMargins'].append(l_pts - r_pts)
        
        teams[road]['PTS'] += r_pts
        teams[road]['PA'] += l_pts
        teams[road]['GP'] += 1
        teams[road]['AwayPTS'] += r_pts
        teams[road]['AwayPA'] += l_pts
        teams[road]['AwayGP'] += 1
        teams[road]['GameMargins'].append(r_pts - l_pts)

    # Build team stats
    team_stats = {}
    for t, s in teams.items():
        if s['GP'] > 0:
            home_net = (s['HomePTS'] - s['HomePA']) / s['HomeGP'] if s['HomeGP'] > 0 else 0
            away_net = (s['AwayPTS'] - s['AwayPA']) / s['AwayGP'] if s['AwayGP'] > 0 else 0
            form_margins = s['GameMargins'][-5:] if len(s['GameMargins']) >= 5 else s['GameMargins']
            form = sum(form_margins) / len(form_margins) if form_margins else 0
            team_stats[t] = {
                'Net': (s['PTS'] - s['PA']) / s['GP'],
                'HomeNet': home_net,
                'AwayNet': away_net,
                'Form': form
            }
        else:
            team_stats[t] = {'Net': 0, 'HomeNet': 0, 'AwayNet': 0, 'Form': 0}

    # Load KenPom Adjusted Ratings
    adj_net_lookup = {}
    import os
    round_suffix = os.environ.get('EUROLEAGUE_ROUND_SUFFIX', '')
    in_file = f'adjusted_ratings{round_suffix}.json'
    if not os.path.exists(in_file):
        in_file = 'adjusted_ratings.json'
    if os.path.exists(in_file):
        import json as json2
        with open(in_file, 'r') as f:
            adj_data = json2.load(f)
        for entry in adj_data:
            adj_net_lookup[entry['Team']] = entry['Adj_Net']
        print(f"Loaded KenPom Adjusted Net Ratings for {len(adj_net_lookup)} teams.")

    # 3. A/B Test: Old Oracle vs New Oracle
    old_correct = 0
    new_correct = 0
    total = 0
    old_margin_errors = []
    new_margin_errors = []
    upsets = []

    for _, row in played.iterrows():
        game_code = str(row['GameCode'])
        
        if game_code in round_map:
            round_num = round_map[game_code]
        else:
            round_num = ((int(game_code) - 1) // 9) + 1
            
        local = row['LocalTeam']
        road = row['RoadTeam']
        actual_margin = row['LocalScore'] - row['RoadScore']
        actual_winner = row['Winner']

        l_stat = team_stats.get(local, {'Net': 0, 'HomeNet': 0, 'AwayNet': 0, 'Form': 0})
        r_stat = team_stats.get(road, {'Net': 0, 'HomeNet': 0, 'AwayNet': 0, 'Form': 0})

        # === OLD MODEL: Raw Net + HCA ===
        old_margin = (l_stat['Net'] - r_stat['Net']) + hca
        old_winner = local if old_margin > 0 else road
        
        # === NEW MODEL: 3-Factor ===
        l_adj = adj_net_lookup.get(local, l_stat['Net'])
        r_adj = adj_net_lookup.get(road, r_stat['Net'])
        l_loc = l_stat['HomeNet']
        r_loc = r_stat['AwayNet']
        l_form = l_stat['Form']
        r_form = r_stat['Form']
        
        l_power = (l_adj * 0.85) + (l_loc * 0.10) + (l_form * 0.05)
        r_power = (r_adj * 0.85) + (r_loc * 0.10) + (r_form * 0.05)
        
        # Per-team HCA blend
        l_overall = l_stat['Net']
        team_hca = l_stat['HomeNet'] - l_overall
        hca_alpha = 0.3
        blended_hca = (hca * (1 - hca_alpha) + team_hca * hca_alpha) * 0.5
        
        new_margin = (l_power - r_power) + blended_hca
        new_winner = local if new_margin > 0 else road
        
        # Accuracy
        if old_winner == actual_winner: old_correct += 1
        if new_winner == actual_winner: new_correct += 1
        
        old_margin_errors.append(abs(old_margin - actual_margin))
        new_margin_errors.append(abs(new_margin - actual_margin))
        
        is_upset = (new_winner != actual_winner)
        
        game_info = {
            'GameCode': row['GameCode'],
            'Round': round_num,
            'Matchup': f"{local} vs {road}",
            'OldMargin': round(old_margin, 2),
            'NewMargin': round(new_margin, 2),
            'ActualMargin': float(actual_margin),
            'OldCorrect': old_winner == actual_winner,
            'NewCorrect': new_winner == actual_winner,
            'IsUpset': bool(is_upset),
            'Winner': actual_winner,
            'PredictedWinner': new_winner
        }
        upsets.append(game_info)
        total += 1

    # 4. Results: A/B Comparison
    old_acc = (old_correct / total) * 100
    new_acc = (new_correct / total) * 100
    old_mae = np.mean(old_margin_errors)
    new_mae = np.mean(new_margin_errors)
    
    print(f"\n{'='*55}")
    print(f"  A/B COMPARISON: Old Oracle vs New Oracle (3-Factor)")
    print(f"{'='*55}")
    print(f"  Total Games: {total}")
    print(f"")
    print(f"  {'Metric':<20} {'Old Oracle':>12} {'New Oracle':>12} {'Delta':>8}")
    print(f"  {'-'*52}")
    print(f"  {'Accuracy':<20} {old_acc:>11.1f}% {new_acc:>11.1f}% {new_acc-old_acc:>+7.1f}%")
    print(f"  {'MAE (pts)':<20} {old_mae:>12.2f} {new_mae:>12.2f} {new_mae-old_mae:>+8.2f}")
    print(f"  {'Correct Picks':<20} {old_correct:>12} {new_correct:>12} {new_correct-old_correct:>+8}")
    print(f"{'='*55}")
    
    # Games where models disagree
    disagree = [g for g in upsets if g['OldCorrect'] != g['NewCorrect']]
    new_wins = [g for g in disagree if g['NewCorrect'] and not g['OldCorrect']]
    old_wins = [g for g in disagree if g['OldCorrect'] and not g['NewCorrect']]
    
    print(f"\n  Models disagreed on: {len(disagree)} games")
    print(f"  New model correct (old wrong): {len(new_wins)}")
    print(f"  Old model correct (new wrong): {len(old_wins)}")

    # Top 5 upsets
    failed_preds = [g for g in upsets if g['IsUpset']]
    top_upsets = sorted(failed_preds, key=lambda x: abs(x['NewMargin']), reverse=True)[:5]

    print("\n--- TOP 5 BIGGEST UPSETS (NEW MODEL) ---")
    for i, g in enumerate(top_upsets):
        print(f"{i+1}. {g['Matchup']} (Rd {g['Round']}) | Pred: {g['PredictedWinner']} +{abs(g['NewMargin']):.1f} | Actual: {g['Winner']} +{abs(g['ActualMargin'])}")

    # Save Report
    report = {
        'OldAccuracy': old_acc,
        'NewAccuracy': new_acc,
        'OldMAE': old_mae,
        'NewMAE': new_mae,
        'TotalGames': total,
        'TopUpsets': top_upsets
    }
    
    with open('oracle_verification_report.json', 'w') as f:
        json.dump(report, f, indent=4)
    print("\nReport saved to oracle_verification_report.json")

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
    
    # A. Accuracy by Round (both models)
    df_ver = pd.DataFrame(upsets)
    
    round_counts = df_ver['Round'].value_counts().sort_index()
    
    old_round_acc = df_ver.groupby('Round').apply(lambda x: x['OldCorrect'].mean() * 100)
    new_round_acc = df_ver.groupby('Round').apply(lambda x: x['NewCorrect'].mean() * 100)
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10))
    
    # Plot 1: Accuracy Trend (both models)
    ax1.plot(old_round_acc.index, old_round_acc.values, marker='s', linestyle='--', color='#94a3b8', linewidth=1.5, label=f'Old Oracle ({old_acc:.1f}%)', alpha=0.6)
    ax1.plot(new_round_acc.index, new_round_acc.values, marker='o', linestyle='-', color='#1d428a', linewidth=2, label=f'New Oracle ({new_acc:.1f}%)')
    ax1.axhline(y=new_acc, color='green', linestyle='--', alpha=0.4)
    ax1.set_title("Oracle Accuracy by Round (Old vs New)", fontsize=14, fontweight='bold')
    ax1.set_ylabel("Accuracy (%)")
    ax1.set_xlabel("Round")
    ax1.set_ylim(0, 100)
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Plot 2: Top 5 Upsets (Bar Chart)
    upset_labels = [f"{g['Matchup']}\n(Margin: {abs(g['NewMargin']):.1f}pts)" for g in top_upsets]
    upset_values = [abs(g['NewMargin']) for g in top_upsets]
    
    colors = ['#ff4b4b', '#ff7676', '#ff9e9e', '#ffc2c2', '#ffe6e6']
    ax2.barh(upset_labels, upset_values, color=colors)
    ax2.invert_yaxis()
    ax2.set_title("Top 5 'Chaos Games' (Biggest New Oracle Misses)", fontsize=14, fontweight='bold')
    ax2.set_xlabel("Predicted Margin (Points)")
    
    plt.tight_layout()
    outfile = "oracle_performance_analysis.png"
    plt.savefig(outfile, dpi=150)
    print(f"Visualization saved to {outfile}")

if __name__ == "__main__":
    verify_oracle()
