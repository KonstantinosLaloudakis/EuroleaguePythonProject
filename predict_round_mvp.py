"""
Round MVP Predictor for Euroleague.

Uses current-season per-game player stats (mvp_parsed_games.json) combined
with oracle win probabilities to rank Round MVP candidates.

Logic:
  - Compute each player's avg PIR, avg PTS, games played this season
  - Apply a win probability multiplier: players on teams likely to win
    get a boost (winners consistently produce higher PIR)
  - Rank all players across the round's games by expected PIR
  - Filter for meaningful contributors (min games + min avg minutes via PIR floor)
"""

import json
import os
import pandas as pd


MIN_GAMES = 5          # ignore players with fewer appearances
MIN_AVG_PIR = 5.0      # ignore marginal contributors
WIN_BOOST = 0.30       # max PIR multiplier boost at 100% win probability
                       # player at 80% win prob → 1 + 0.3*(0.8-0.5) = +9%
                       # player at 20% win prob → 1 + 0.3*(0.2-0.5) = -9%


def _load_player_season_stats():
    """
    Build per-player season averages from mvp_parsed_games.json.
    Returns a DataFrame with columns: PlayerCode, PlayerName, TeamCode,
    GP, AvgPIR, AvgPTS, StdPIR (volatility).
    """
    path = 'mvp_parsed_games.json'
    if not os.path.exists(path):
        print(f"[MVP Predictor] {path} not found — cannot predict Round MVP.")
        return pd.DataFrame()

    with open(path) as f:
        data = json.load(f)

    df = pd.DataFrame(data)

    # Primary team = most frequent team code (handles mid-season transfers)
    primary_team = (
        df.groupby('PlayerCode')['TeamCode']
        .agg(lambda x: x.mode().iloc[0])
        .rename('PrimaryTeam')
    )

    agg = df.groupby(['PlayerCode', 'PlayerName']).agg(
        GP=('GameCode', 'count'),
        AvgPIR=('PIR', 'mean'),
        StdPIR=('PIR', 'std'),
        AvgPTS=('PTS', 'mean'),
        MaxPIR=('PIR', 'max'),
    ).reset_index()

    agg = agg.merge(primary_team, on='PlayerCode', how='left')
    agg['StdPIR'] = agg['StdPIR'].fillna(0)
    return agg


def predict_round_mvp(predictions, top_n=10):
    """
    Predict Round MVP candidates.

    Parameters
    ----------
    predictions : list of dicts
        Oracle prediction records (as produced by mvp_oracle.py).
        Each dict must have: 'Local', 'Road', 'HomeWinProb'.
    top_n : int
        Number of candidates to return.

    Returns
    -------
    list of dicts, sorted by ExpectedPIR descending.
    """
    if not predictions:
        return []

    # Build team → win probability map
    team_win_prob = {}
    for p in predictions:
        team_win_prob[p['Local']] = p['HomeWinProb'] / 100.0
        team_win_prob[p['Road']] = 1.0 - p['HomeWinProb'] / 100.0

    playing_teams = set(team_win_prob.keys())

    stats = _load_player_season_stats()
    if stats.empty:
        return []

    # Keep only players on teams playing this round
    stats = stats[stats['PrimaryTeam'].isin(playing_teams)].copy()

    # Apply filters
    stats = stats[stats['GP'] >= MIN_GAMES]
    stats = stats[stats['AvgPIR'] >= MIN_AVG_PIR]

    if stats.empty:
        return []

    # Win probability multiplier
    stats['WinProb'] = stats['PrimaryTeam'].map(team_win_prob)
    stats['WinMult'] = 1.0 + WIN_BOOST * (stats['WinProb'] - 0.5)
    stats['ExpectedPIR'] = stats['AvgPIR'] * stats['WinMult']

    # Sort and build output
    top = stats.nlargest(top_n, 'ExpectedPIR')

    results = []
    for _, row in top.iterrows():
        results.append({
            'Player': row['PlayerName'],
            'Team': row['PrimaryTeam'],
            'GP': int(row['GP']),
            'AvgPIR': round(row['AvgPIR'], 1),
            'MaxPIR': round(row['MaxPIR'], 1),
            'AvgPTS': round(row['AvgPTS'], 1),
            'WinProb': round(row['WinProb'] * 100, 1),
            'ExpectedPIR': round(row['ExpectedPIR'], 1),
        })

    return results


def print_mvp_leaderboard(candidates, target_round):
    print(f"\n{'='*65}")
    print(f"  ROUND {target_round} MVP CANDIDATES")
    print(f"{'='*65}")
    print(f"  {'#':<3} {'Player':<25} {'Team':<5} {'AvgPIR':>7} {'MaxPIR':>7} {'WinProb':>8} {'ExpPIR':>7}")
    print(f"  {'-'*60}")
    for i, c in enumerate(candidates, 1):
        print(
            f"  {i:<3} {c['Player']:<25} {c['Team']:<5}"
            f" {c['AvgPIR']:>7.1f} {c['MaxPIR']:>7.1f}"
            f" {c['WinProb']:>7.0f}%  {c['ExpectedPIR']:>6.1f}"
        )
    print()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--json', required=True, help='Path to oracle forecast JSON')
    parser.add_argument('--round', type=int, default=0)
    parser.add_argument('--top', type=int, default=10)
    args = parser.parse_args()

    with open(args.json) as f:
        preds = json.load(f)

    candidates = predict_round_mvp(preds, top_n=args.top)
    print_mvp_leaderboard(candidates, args.round)
