"""
Weighted Impact Rating (WIR) Calculator.
Replaces Euroleague's flawed PIR metric with an efficiency-adjusted, 
per-minute normalized impact score.
"""

import pandas as pd
import numpy as np

def mmss_to_minutes(mmss):
    """Convert 'MM:SS' string to decimal minutes."""
    if pd.isna(mmss):
        return 0.0
    try:
        parts = str(mmss).split(':')
        if len(parts) == 2:
            return int(parts[0]) + int(parts[1]) / 60.0
        return float(mmss)
    except:
        return 0.0


def calculate_wir():
    # Load player stats (these are already PerGame averages from the API)
    df = pd.read_csv('player_stats_E2025.csv')
    
    # Filter players with at least 10 games played and 10 mins/game
    df['mins_played'] = df['minutesPlayed'].apply(mmss_to_minutes)
    df = df[(df['gamesPlayed'] >= 10) & (df['mins_played'] >= 10.0)].copy()
    
    # Calculate WIR per game
    pts = df['pointsScored']
    ast = df['assists']
    orb = df['offensiveRebounds']
    drb = df['defensiveRebounds']
    stl = df['steals']
    blk = df['blocks']
    tov = df['turnovers']
    fga = df['twoPointersAttempted'] + df['threePointersAttempted']
    fgm = df['twoPointersMade'] + df['threePointersMade']
    fg_miss = fga - fgm
    ft_miss = df['freeThrowsAttempted'] - df['freeThrowsMade']
    
    # WIR Formula (Efficiency-weighted)
    df['WIR'] = (
        (pts * 0.8) + 
        (ast * 1.5) + 
        (orb * 1.2) + 
        (drb * 0.4) + 
        (stl * 1.8) + 
        (blk * 1.2) - 
        (tov * 1.5) - 
        (fg_miss * 0.5) - 
        (ft_miss * 0.5)
    )
    
    # Per 40 minutes normalization
    df['WIR_40'] = (df['WIR'] / df['mins_played']) * 40
    df['PIR_40'] = (df['pir'] / df['mins_played']) * 40
    
    # Calculate True Shooting Percentage for context
    ts_att = fga + 0.44 * df['freeThrowsAttempted']
    df['TS%'] = np.where(ts_att > 0, (pts / (2 * ts_att)) * 100, 0)
    
    # Sort and rank
    df = df.sort_values('WIR_40', ascending=False).reset_index(drop=True)
    df['WIR_Rank'] = df.index + 1
    
    df_pir_sorted = df.sort_values('PIR_40', ascending=False).reset_index(drop=True)
    pir_ranks = {row['player.code']: idx + 1 for idx, row in df_pir_sorted.iterrows()}
    df['PIR_Rank'] = df['player.code'].map(pir_ranks)
    df['Rank_Diff'] = df['PIR_Rank'] - df['WIR_Rank']  # Positive = WIR rates them higher than PIR
    
    # === PRINT RESULTS ===
    print(f"\n{'='*90}")
    print(f"  WEIGHTED IMPACT RATING (WIR) vs PIR per 40 mins — Euroleague 2025-26")
    print(f"{'='*90}")
    print(f"  {'Rank':<4} {'Player':<20} {'Team':<5} {'WIR/40':>8} {'PIR/40':>8} {'TS%':>6}  {'PIR Rank':>8}  {'Diff':>6}")
    print(f"  {'-'*76}")
    
    for _, row in df.head(15).iterrows():
        diff_str = f"+{row['Rank_Diff']}" if row['Rank_Diff'] > 0 else str(row['Rank_Diff'])
        print(f"  {row['WIR_Rank']:<4} {row['player.name']:<20} {row['player.team.code']:<5} "
              f"{row['WIR_40']:>8.1f} {row['PIR_40']:>8.1f} {row['TS%']:>5.1f}%  #{int(row['PIR_Rank']):<7} {diff_str:>6}")
    
    print(f"\n  --- BIGGEST RISERS (Overlooked by PIR, loved by WIR) ---")
    risers = df.sort_values('Rank_Diff', ascending=False).head(5)
    for _, row in risers.iterrows():
        print(f"  {row['player.name']:<20} ({row['player.team.code']}) | WIR Rank: #{int(row['WIR_Rank'])} | PIR Rank: #{int(row['PIR_Rank'])} | WIR/40: {row['WIR_40']:.1f}")

    print(f"\n  --- BIGGEST FALLERS (Overrated by PIR volume/inefficiency) ---")
    fallers = df.sort_values('Rank_Diff', ascending=True).head(5)
    for _, row in fallers.iterrows():
        print(f"  {row['player.name']:<20} ({row['player.team.code']}) | WIR Rank: #{int(row['WIR_Rank'])} | PIR Rank: #{int(row['PIR_Rank'])} | WIR/40: {row['WIR_40']:.1f}")
        
    # Save results
    cols_to_save = ['player.name', 'player.team.name', 'gamesPlayed', 'mins_played', 
                    'pointsScored', 'assists', 'totalRebounds', 'TS%', 
                    'pir', 'PIR_40', 'WIR', 'WIR_40', 'WIR_Rank', 'PIR_Rank', 'Rank_Diff']
    
    df[cols_to_save].to_json('wir_ratings.json', orient='records', indent=4)
    print(f"\n  Saved full rankings to wir_ratings.json")


if __name__ == '__main__':
    calculate_wir()
