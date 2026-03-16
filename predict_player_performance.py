"""
Player Performance Forecaster for Euroleague.

Predicts per-player PIR and PTS for an upcoming round using:
  1. Season average baseline (from current-season game logs)
  2. Opponent defensive quality  (PIR allowed per team vs league average)
  3. Recent form                 (last-5-game rolling average vs season avg)
  4. Home / away effect          (computed from historical splits this season)
  5. Win probability boost       (from oracle forecast — winning teams play freely)

Usage:
    python predict_player_performance.py --round 32
    python predict_player_performance.py --oracle oracle_forecast_round_32_ml.json
"""

import json
import os
import argparse
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np


# ── Tuning knobs ──────────────────────────────────────────────────────────────
MIN_GAMES       = 5      # minimum season appearances to be considered
FORM_GAMES      = 5      # number of recent games for form calculation
FORM_WEIGHT     = 0.30   # how much recent form pulls prediction (0 = ignore form)
WIN_BOOST       = 0.15   # max PIR multiplier from win probability
DEF_WEIGHT      = 0.50   # how much opponent defence adjusts prediction
# ─────────────────────────────────────────────────────────────────────────────


def _load_game_logs():
    """Load per-player per-game logs, enriched with home/away flag."""
    path = 'mvp_parsed_games.json'
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} not found.")

    logs = pd.DataFrame(json.load(open(path)))

    # Attach home/away flag via game results
    results_path = 'mvp_game_results.json'
    if os.path.exists(results_path):
        results = pd.read_json(results_path)[['GameCode', 'LocalTeam']]
        logs = logs.merge(results, on='GameCode', how='left')
        logs['IsHome'] = logs['TeamCode'] == logs['LocalTeam']
    else:
        logs['IsHome'] = True  # safe fallback

    return logs


def _build_player_profiles(logs):
    """
    Build per-player season profile:
      - season averages (PIR, PTS)
      - home/away splits
      - recent-form ratio
      - primary team
    """
    # Primary team = most frequent
    primary = (
        logs.groupby(['PlayerCode', 'PlayerName'])['TeamCode']
        .agg(lambda x: x.mode().iloc[0])
        .rename('Team')
        .reset_index()
    )

    # Season averages
    agg = (
        logs.groupby(['PlayerCode', 'PlayerName'])
        .agg(
            GP      = ('GameCode', 'count'),
            AvgPIR  = ('PIR',      'mean'),
            AvgPTS  = ('PTS',      'mean'),
            # Home splits
            HomePIR = ('PIR',      lambda x: x[logs.loc[x.index, 'IsHome']].mean()),
            AwayPIR = ('PIR',      lambda x: x[~logs.loc[x.index, 'IsHome']].mean()),
        )
        .reset_index()
    )

    # Recent form: avg PIR in last FORM_GAMES vs season average
    def form_ratio(group):
        recent = group.sort_values('GameCode').tail(FORM_GAMES)['PIR'].mean()
        season = group['PIR'].mean()
        if season == 0 or pd.isna(season) or pd.isna(recent):
            return 1.0
        # Dampen towards 1: weight * (recent/season) + (1-weight)
        raw = recent / season
        return FORM_WEIGHT * raw + (1 - FORM_WEIGHT)

    form = (
        logs.groupby(['PlayerCode', 'PlayerName'])
        .apply(form_ratio, include_groups=False)
        .reset_index()
        .rename(columns={0: 'FormFactor'})
    )

    profiles = agg.merge(primary, on=['PlayerCode', 'PlayerName'])
    profiles = profiles.merge(form, on=['PlayerCode', 'PlayerName'])
    profiles = profiles[profiles['GP'] >= MIN_GAMES].copy()

    # Fill NaN home/away splits with season average
    profiles['HomePIR'] = profiles['HomePIR'].fillna(profiles['AvgPIR'])
    profiles['AwayPIR'] = profiles['AwayPIR'].fillna(profiles['AvgPIR'])

    return profiles


def _build_defensive_ratings(logs):
    """
    Compute per-team defensive PIR allowed (normalised to league average).
    DefFactor > 1 → team allows more PIR than average (easier matchup)
    DefFactor < 1 → team allows less PIR than average (tougher matchup)
    """
    results_path = 'mvp_game_results.json'
    if not os.path.exists(results_path):
        return {}

    results = pd.read_json(results_path)[['GameCode', 'LocalTeam', 'RoadTeam']]
    # Drop LocalTeam from logs to avoid collision (it was added for IsHome flag)
    logs_slim = logs[['GameCode', 'TeamCode', 'PIR']].copy()
    enriched = logs_slim.merge(results, on='GameCode', how='left')
    enriched['Opponent'] = np.where(
        enriched['TeamCode'] == enriched['LocalTeam'],
        enriched['RoadTeam'],
        enriched['LocalTeam']
    )

    # Average PIR allowed per opponent
    opp_pir = enriched.groupby('Opponent')['PIR'].mean()
    league_avg = opp_pir.mean()

    if league_avg == 0:
        return {}

    def_factor = (opp_pir / league_avg).to_dict()
    return def_factor


def _load_upcoming_games(target_round, oracle_path=None):
    """
    Return list of (home_team, away_team, home_win_prob) for the target round.
    Priority: oracle JSON → official XML schedule.
    """
    # 1. Try oracle JSON
    if oracle_path and os.path.exists(oracle_path):
        with open(oracle_path) as f:
            data = json.load(f)
        preds = data.get('predictions', data) if isinstance(data, dict) else data
        games = []
        for p in preds:
            games.append({
                'Home': p['Local'],
                'Away': p['Road'],
                'HomeWinProb': p.get('HomeWinProb', 50.0) / 100.0,
            })
        print(f"Loaded {len(games)} games from oracle JSON.")
        return games

    # 2. Fall back to XML schedule
    name_to_code = {
        'ALBA BERLIN': 'BER', 'ANADOLU EFES ISTANBUL': 'IST', 'AS MONACO': 'MCO',
        'BASKONIA VITORIA-GASTEIZ': 'BAS', 'KOSNER BASKONIA VITORIA-GASTEIZ': 'BAS',
        'CRVENA ZVEZDA MERIDIANBET BELGRADE': 'RED', 'EA7 EMPORIO ARMANI MILAN': 'MIL',
        'FC BARCELONA': 'BAR', 'FC BAYERN MUNICH': 'MUN',
        'FENERBAHCE BEKO ISTANBUL': 'ULK', 'LDLC ASVEL VILLEURBANNE': 'ASV',
        'MACCABI PLAYTIKA TEL AVIV': 'TEL', 'MACCABI RAPYD TEL AVIV': 'TEL',
        'OLYMPIACOS PIRAEUS': 'OLY', 'PANATHINAIKOS AKTOR ATHENS': 'PAN',
        'PARTIZAN MOZZART BET BELGRADE': 'PAR', 'PARIS BASKETBALL': 'PRS',
        'REAL MADRID': 'MAD', 'VALENCIA BASKET': 'PAM',
        'VIRTUS SEGAFREDO BOLOGNA': 'VIR', 'VIRTUS BOLOGNA': 'VIR',
        'ZALGIRIS KAUNAS': 'ZAL', 'DUBAI BASKETBALL': 'DUB', 'HAPOEL IBI TEL AVIV': 'HTA',
    }
    xml_path = 'official_schedule_2025.xml'
    if not os.path.exists(xml_path):
        return []
    tree = ET.parse(xml_path)
    games = []
    for item in tree.getroot().findall('item'):
        if item.find('gameday').text != str(target_round):
            continue
        home = name_to_code.get(item.find('hometeam').text, 'UNK')
        away = name_to_code.get(item.find('awayteam').text, 'UNK')
        if home != 'UNK' and away != 'UNK':
            games.append({'Home': home, 'Away': away, 'HomeWinProb': 0.55})
    print(f"Loaded {len(games)} games from XML schedule (no win probabilities).")
    return games


def predict_round(target_round=None, oracle_path=None, top_n=15):
    """
    Predict player performance for an upcoming round.

    Returns a list of prediction dicts sorted by PredictedPIR descending.
    """
    logs     = _load_game_logs()
    profiles = _build_player_profiles(logs)
    def_ratings = _build_defensive_ratings(logs)

    print(f"Built profiles for {len(profiles)} players.")
    print(f"Defensive ratings computed for {len(def_ratings)} teams.")

    games = _load_upcoming_games(target_round, oracle_path)
    if not games:
        print("No upcoming games found.")
        return []

    league_avg_pir = profiles['AvgPIR'].mean()
    predictions = []

    for game in games:
        home_code = game['Home']
        away_code = game['Away']
        home_win_prob = game['HomeWinProb']
        away_win_prob = 1.0 - home_win_prob

        # Defensive factors for each team
        home_def = DEF_WEIGHT * def_ratings.get(home_code, 1.0) + (1 - DEF_WEIGHT)
        away_def = DEF_WEIGHT * def_ratings.get(away_code, 1.0) + (1 - DEF_WEIGHT)

        for _, player in profiles[profiles['Team'].isin([home_code, away_code])].iterrows():
            is_home  = player['Team'] == home_code
            win_prob = home_win_prob if is_home else away_win_prob
            opp_def  = away_def if is_home else home_def  # facing the opponent's defence

            # Baseline: home/away split or season average
            baseline_pir = player['HomePIR'] if is_home else player['AwayPIR']
            baseline_pts = player['AvgPTS']   # PTS splits not available, use season avg

            # Apply adjustments
            def_factor     = opp_def
            form_factor    = player['FormFactor']
            win_factor     = 1.0 + WIN_BOOST * (win_prob - 0.5)

            pred_pir = baseline_pir * def_factor * form_factor * win_factor
            pred_pts = baseline_pts * def_factor * form_factor * win_factor

            predictions.append({
                'Player':        player['PlayerName'],
                'Team':          player['Team'],
                'Opponent':      away_code if is_home else home_code,
                'IsHome':        is_home,
                'GP':            int(player['GP']),
                'AvgPIR':        round(player['AvgPIR'], 1),
                'AvgPTS':        round(player['AvgPTS'], 1),
                'FormFactor':    round(form_factor, 3),
                'DefFactor':     round(def_factor, 3),
                'WinProb':       round(win_prob * 100, 1),
                'PredictedPIR':  round(pred_pir, 1),
                'PredictedPTS':  round(pred_pts, 1),
            })

    predictions.sort(key=lambda x: x['PredictedPIR'], reverse=True)
    return predictions


def print_leaderboard(predictions, target_round, top_n=15):
    print(f"\n{'='*80}")
    print(f"  ROUND {target_round} PLAYER PERFORMANCE FORECAST — TOP {top_n}")
    print(f"{'='*80}")
    print(f"  {'#':<3} {'Player':<25} {'Tm':<4} {'vs':<4} {'H/A':<4} "
          f"{'AvgPIR':>7} {'Form':>6} {'Def':>6} {'WinP':>6} {'PredPIR':>8} {'PredPTS':>8}")
    print(f"  {'-'*75}")
    for i, p in enumerate(predictions[:top_n], 1):
        ha = 'H' if p['IsHome'] else 'A'
        print(
            f"  {i:<3} {p['Player']:<25} {p['Team']:<4} {p['Opponent']:<4} {ha:<4}"
            f" {p['AvgPIR']:>7.1f} {p['FormFactor']:>6.2f} {p['DefFactor']:>6.2f}"
            f" {p['WinProb']:>5.0f}%  {p['PredictedPIR']:>7.1f}  {p['PredictedPTS']:>7.1f}"
        )
    print()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--round',  type=int, default=32)
    parser.add_argument('--oracle', type=str, default=None,
                        help='Path to oracle forecast JSON for win probabilities')
    parser.add_argument('--top',    type=int, default=15)
    args = parser.parse_args()

    round_suffix = os.environ.get('EUROLEAGUE_ROUND_SUFFIX', '')
    if args.oracle is None:
        args.oracle = f'oracle_forecast_round_{args.round}{round_suffix}.json'

    preds = predict_round(target_round=args.round, oracle_path=args.oracle, top_n=args.top)

    if preds:
        print_leaderboard(preds, args.round, top_n=args.top)

        out = f'player_forecast_round_{args.round}{round_suffix}.json'
        with open(out, 'w') as f:
            json.dump(preds, f, indent=2)
        print(f"Saved {out}")
