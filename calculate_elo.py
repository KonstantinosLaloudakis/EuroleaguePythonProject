"""
Euroleague Rolling Elo Rating System.
Computes game-by-game Elo ratings that update after each result.
Produces elo_ratings.json for use by mvp_oracle.py.
"""

import json
import numpy as np
import os


# --- Elo Parameters (optimized via backtest) ---
K_FACTOR = 10        # Conservative K for single-season stability
ELO_HCA = 50         # Elo points for home court advantage
STARTING_ELO = 1500  # All teams start here


def expected_score(rating_a, rating_b, hca=0):
    """Expected win probability for team A."""
    return 1 / (1 + 10 ** ((rating_b - rating_a - hca) / 400))


def compute_elo_ratings():
    """Compute rolling Elo ratings from game results."""
    
    with open('mvp_game_results.json', 'r') as f:
        all_games = json.load(f)
    
    # Only played games, sorted chronologically
    played = sorted(
        [g for g in all_games if g['LocalScore'] > 0],
        key=lambda g: g['GameCode']
    )
    
    if not played:
        print("No played games found.")
        return {}
    
    # Initialize Elo ratings
    elo = {}
    history = []  # Track Elo after each round for visualization
    
    for game in played:
        local = game['LocalTeam']
        road = game['RoadTeam']
        
        if local not in elo:
            elo[local] = STARTING_ELO
        if road not in elo:
            elo[road] = STARTING_ELO
        
        actual_margin = game['LocalScore'] - game['RoadScore']
        actual_score_local = 1.0 if actual_margin > 0 else 0.0
        
        # Expected outcome
        exp_local = expected_score(elo[local], elo[road], ELO_HCA)
        
        # Update Elo (no margin-of-victory multiplier — backtested as better)
        elo[local] += K_FACTOR * (actual_score_local - exp_local)
        elo[road] += K_FACTOR * ((1 - actual_score_local) - (1 - exp_local))
        
        history.append({
            'GameCode': game['GameCode'],
            'EloSnapshot': dict(elo)
        })
    
    # Sort by Elo rating
    sorted_elo = sorted(elo.items(), key=lambda x: x[1], reverse=True)
    
    # Print final standings
    print(f"\n{'='*45}")
    print(f"  EUROLEAGUE ELO RATINGS ({len(played)} games)")
    print(f"{'='*45}")
    
    for i, (team, rating) in enumerate(sorted_elo):
        # Calculate win probability vs average team
        wp = expected_score(rating, STARTING_ELO) * 100
        delta = rating - STARTING_ELO
        print(f"  {i+1:>2}. {team:<5} {rating:>6.0f} ({delta:>+5.0f})  WP vs avg: {wp:.0f}%")
    
    # Save to file
    output = []
    for team, rating in sorted_elo:
        output.append({
            'Team': team,
            'Elo': round(rating, 1),
            'Delta': round(rating - STARTING_ELO, 1)
        })
    
    round_suffix = os.environ.get('EUROLEAGUE_ROUND_SUFFIX', '')
    outfile = f'elo_ratings{round_suffix}.json'
    
    with open(outfile, 'w') as f:
        json.dump(output, f, indent=4)
    print(f"\nSaved {outfile}")
    
    return elo


if __name__ == '__main__':
    compute_elo_ratings()
