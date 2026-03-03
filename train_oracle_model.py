"""
Oracle Logistic Regression Model.
Trains a logistic regression on game features to learn optimal coefficients
and produce properly calibrated win probabilities.

Features: adj_net_diff, elo_diff, home_net, away_net, form_diff, sos_diff
"""

import json
import numpy as np
import os
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss
import pickle


# --- Elo helpers ---
def expected_elo(ra, rb, hca=50):
    return 1 / (1 + 10 ** ((rb - ra - hca) / 400))


def build_features():
    """Build feature matrix from game results incrementally (stats at game time)."""
    
    with open('mvp_game_results.json', 'r') as f:
        all_games = json.load(f)
    
    # Load round map
    round_map = {}
    if os.path.exists('game_code_to_round.json'):
        with open('game_code_to_round.json', 'r') as f:
            round_map = json.load(f)
    
    # Load static adjusted ratings
    adj_net = {}
    sos = {}
    if os.path.exists('adjusted_ratings.json'):
        with open('adjusted_ratings.json', 'r') as f:
            for e in json.load(f):
                adj_net[e['Team']] = e['Adj_Net']
                sos[e['Team']] = e.get('SOS_WinPct', 0.5)
    
    played = sorted(
        [g for g in all_games if g['LocalScore'] > 0],
        key=lambda g: g['GameCode']
    )
    
    global_hca = np.mean([g['LocalScore'] - g['RoadScore'] for g in played])
    
    # Incremental tracking
    teams = {}
    elo = {}
    
    def get(t):
        if t not in teams:
            teams[t] = {
                'PTS': 0, 'PA': 0, 'GP': 0,
                'HPTS': 0, 'HPA': 0, 'HGP': 0,
                'APTS': 0, 'APA': 0, 'AGP': 0,
                'Margins': []
            }
        if t not in elo:
            elo[t] = 1500
        return teams[t]
    
    features = []
    labels = []
    rounds = []
    game_info = []
    
    for game in played:
        local = game['LocalTeam']
        road = game['RoadTeam']
        actual_margin = game['LocalScore'] - game['RoadScore']
        home_won = 1 if actual_margin > 0 else 0
        
        gc = str(game['GameCode'])
        rd = round_map.get(gc, ((int(gc) - 1) // 9) + 1)
        
        l = get(local)
        r = get(road)
        
        # Only use games where we have enough data
        if l['GP'] >= 3 and r['GP'] >= 3:
            # Feature 1: Adj Net difference
            l_adj = adj_net.get(local, (l['PTS']-l['PA'])/l['GP'])
            r_adj = adj_net.get(road, (r['PTS']-r['PA'])/r['GP'])
            adj_diff = l_adj - r_adj
            
            # Feature 2: Elo difference (points scale)
            elo_diff = (elo[local] - elo[road]) / 25
            
            # Feature 3: Home team's home net rating
            home_net = (l['HPTS']-l['HPA'])/l['HGP'] if l['HGP'] > 0 else 0
            
            # Feature 4: Road team's away net rating
            away_net = (r['APTS']-r['APA'])/r['AGP'] if r['AGP'] > 0 else 0
            
            # Feature 5: Form difference (last 5 margin avg)
            l_form = np.mean(l['Margins'][-5:]) if len(l['Margins']) >= 3 else 0
            r_form = np.mean(r['Margins'][-5:]) if len(r['Margins']) >= 3 else 0
            form_diff = l_form - r_form
            
            # Feature 6: SOS difference
            l_sos = sos.get(local, 0.5)
            r_sos = sos.get(road, 0.5)
            sos_diff = l_sos - r_sos
            
            # Feature 7: Per-team HCA  
            l_overall = (l['PTS']-l['PA'])/l['GP']
            team_hca = home_net - l_overall
            
            features.append([adj_diff, elo_diff, home_net, away_net, form_diff, sos_diff, team_hca])
            labels.append(home_won)
            rounds.append(rd)
            game_info.append(f"{local} vs {road} (Rd {rd})")
        
        # Update stats AFTER feature extraction
        actual_score = 1.0 if actual_margin > 0 else 0.0
        exp = expected_elo(elo[local], elo[road])
        elo[local] += 10 * (actual_score - exp)
        elo[road] += 10 * ((1 - actual_score) - (1 - exp))
        
        l['PTS'] += game['LocalScore']; l['PA'] += game['RoadScore']; l['GP'] += 1
        l['HPTS'] += game['LocalScore']; l['HPA'] += game['RoadScore']; l['HGP'] += 1
        l['Margins'].append(actual_margin)
        r['PTS'] += game['RoadScore']; r['PA'] += game['LocalScore']; r['GP'] += 1
        r['APTS'] += game['RoadScore']; r['APA'] += game['LocalScore']; r['AGP'] += 1
        r['Margins'].append(-actual_margin)
    
    return np.array(features), np.array(labels), np.array(rounds), game_info


def train_and_evaluate():
    """Train logistic regression with train/test split by round."""
    
    X, y, rounds, info = build_features()
    
    print(f"Total samples: {len(X)}")
    print(f"Features: adj_diff, elo_diff, home_net, away_net, form_diff, sos_diff, team_hca")
    print(f"Home win rate: {y.mean()*100:.1f}%")
    
    feature_names = ['adj_diff', 'elo_diff', 'home_net', 'away_net', 'form_diff', 'sos_diff', 'team_hca']
    
    # === Split: Train on Rounds 5-25, Validate on 26-29 ===
    train_mask = (rounds >= 5) & (rounds <= 25)
    val_mask = (rounds >= 26) & (rounds <= 29)
    
    X_train, y_train = X[train_mask], y[train_mask]
    X_val, y_val = X[val_mask], y[val_mask]
    
    print(f"\nTrain: {len(X_train)} games (Rounds 5-25)")
    print(f"Val:   {len(X_val)} games (Rounds 26-29)")
    
    # Scale features
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_val_s = scaler.transform(X_val)
    
    # Train logistic regression
    model = LogisticRegression(C=1.0, max_iter=1000)
    model.fit(X_train_s, y_train)
    
    # Coefficients
    print(f"\n{'='*55}")
    print(f"  LOGISTIC REGRESSION COEFFICIENTS")
    print(f"{'='*55}")
    for name, coef in zip(feature_names, model.coef_[0]):
        bar = '#' * int(abs(coef) * 10)
        sign = '+' if coef > 0 else '-'
        print(f"  {name:<12} {coef:>+7.3f}  {sign}{bar}")
    print(f"  {'intercept':<12} {model.intercept_[0]:>+7.3f}")
    
    # Evaluate
    train_pred = model.predict(X_train_s)
    val_pred = model.predict(X_val_s)
    train_prob = model.predict_proba(X_train_s)[:, 1]
    val_prob = model.predict_proba(X_val_s)[:, 1]
    
    train_acc = accuracy_score(y_train, train_pred) * 100
    val_acc = accuracy_score(y_val, val_pred) * 100
    
    # Brier score (lower = better calibration)
    train_brier = brier_score_loss(y_train, train_prob)
    val_brier = brier_score_loss(y_val, val_prob)
    
    print(f"\n{'='*55}")
    print(f"  RESULTS")
    print(f"{'='*55}")
    print(f"  {'Metric':<20} {'Train':>10} {'Validation':>12}")
    print(f"  {'-'*42}")
    print(f"  {'Accuracy':<20} {train_acc:>9.1f}% {val_acc:>11.1f}%")
    print(f"  {'Brier Score':<20} {train_brier:>10.4f} {val_brier:>12.4f}")
    print(f"  {'Log Loss':<20} {log_loss(y_train, train_prob):>10.4f} {log_loss(y_val, val_prob):>12.4f}")
    
    # Baseline comparison: just pick home team
    home_acc_val = y_val.mean() * 100
    print(f"\n  Home win baseline:  {home_acc_val:.1f}%")
    
    # Calibration check
    print(f"\n  --- Calibration Check ---")
    for lo, hi in [(0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.0)]:
        mask = (val_prob >= lo) & (val_prob < hi)
        if mask.sum() > 0:
            actual = y_val[mask].mean() * 100
            predicted = val_prob[mask].mean() * 100
            print(f"  Predicted {lo*100:.0f}-{hi*100:.0f}%: actual={actual:.0f}%, n={mask.sum()}")
    
    # === Leave-One-Round-Out Cross-Validation for robust estimate ===
    print(f"\n{'='*55}")
    print(f"  LEAVE-ONE-ROUND-OUT CROSS-VALIDATION")
    print(f"{'='*55}")
    
    unique_rounds = sorted(set(rounds[(rounds >= 5)]))
    cv_preds = []
    cv_true = []
    cv_probs = []
    
    for test_round in unique_rounds:
        train_m = (rounds != test_round) & (rounds >= 5)
        test_m = (rounds == test_round)
        
        if test_m.sum() == 0:
            continue
        
        Xtr, ytr = X[train_m], y[train_m]
        Xte, yte = X[test_m], y[test_m]
        
        sc = StandardScaler()
        Xtr_s = sc.fit_transform(Xtr)
        Xte_s = sc.transform(Xte)
        
        m = LogisticRegression(C=1.0, max_iter=1000)
        m.fit(Xtr_s, ytr)
        
        preds = m.predict(Xte_s)
        probs = m.predict_proba(Xte_s)[:, 1]
        
        cv_preds.extend(preds)
        cv_true.extend(yte)
        cv_probs.extend(probs)
    
    cv_acc = accuracy_score(cv_true, cv_preds) * 100
    cv_brier = brier_score_loss(cv_true, cv_probs)
    
    print(f"  CV Accuracy: {cv_acc:.1f}% ({sum(np.array(cv_preds)==np.array(cv_true))}/{len(cv_true)})")
    print(f"  CV Brier:    {cv_brier:.4f}")
    
    # Save model
    with open('oracle_lr_model.pkl', 'wb') as f:
        pickle.dump({'model': model, 'scaler': scaler, 'features': feature_names}, f)
    print(f"\nModel saved to oracle_lr_model.pkl")
    
    return model, scaler


if __name__ == '__main__':
    train_and_evaluate()
