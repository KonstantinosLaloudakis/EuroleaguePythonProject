"""
Win Probability Added (WPA) Calculator — 2025-26 Season
Calculates the True Win Probability at every play-by-play event,
and assigns the delta (change) in WP to the player who made the play.
"""

import pandas as pd
import numpy as np
import math

def calc_wp(margin, seconds_remaining):
    if seconds_remaining <= 0:
        return 1.0 if margin > 0 else (0.0 if margin < 0 else 0.5)
        
    # Standard deviation of the score margin shrinks as time runs out
    # 11.5 is the approximate End-Of-Game standard deviation of margin for Euroleague
    sigma = 11.5 * math.sqrt(seconds_remaining / 2400.0)
    if sigma < 0.1: sigma = 0.1
    
    # Logistic approximation of Normal CDF
    # formula: 1 / (1 + exp(-1.702 * x / sigma))
    return 1.0 / (1.0 + math.exp(-1.702 * margin / sigma))

def get_seconds(time_str):
    try:
        m, s = map(int, str(time_str).split(':'))
        return m * 60 + s
    except:
        return 0

def calculate_action_wpa():
    print("Loading pbp_2025.csv...")
    df = pd.read_csv('pbp_2025.csv')
    
    # Sort chronologically
    df = df.sort_values(['Gamecode', 'NUMBEROFPLAY']).reset_index(drop=True)
    
    # Forward fill points
    df['POINTS_A'] = df.groupby('Gamecode')['POINTS_A'].ffill().fillna(0)
    df['POINTS_B'] = df.groupby('Gamecode')['POINTS_B'].ffill().fillna(0)
    
    # Calculate Seconds Remaining in the Game
    df['SecRemainingPeriod'] = df['MARKERTIME'].apply(get_seconds)
    
    def calc_game_seconds(row):
        period = row['PERIOD']
        sec_per = row['SecRemainingPeriod']
        if pd.isna(period):
            return 0
        if period <= 4:
            return (4 - period) * 600 + sec_per
        else:
            # Overtime
            ot_num = period - 4
            return max(0, (1 - ot_num) * 300 + sec_per)  # Simplification for 1st OT
            
    df['SecondsRemaining'] = df.apply(calc_game_seconds, axis=1)
    
    # Determine WP at each row
    df['Margin'] = df['POINTS_A'] - df['POINTS_B']
    df['WP_A'] = df.apply(lambda r: calc_wp(r['Margin'], r['SecondsRemaining']), axis=1)
    
    # Calculate ΔWP
    # Shift within the game
    df['Prev_WP_A'] = df.groupby('Gamecode')['WP_A'].shift(1).fillna(0.5)
    df['Delta_WP_A'] = df['WP_A'] - df['Prev_WP_A']
    
    # Try to identify which Team Code is Local (Team A)
    # We can do this by looking at who scores POINTS_A
    local_team_codes = {}
    for g, group in df.groupby('Gamecode'):
        # Find first row where POINTS_A > 0 and the play changed POINTS_A
        scored_a = group[group['POINTS_A'] > group['POINTS_A'].shift(1).fillna(0)]
        if not scored_a.empty:
            local_team_codes[g] = scored_a.iloc[0]['CODETEAM']
            
    # Assign WPA
    player_wpa = {}
    
    for _, row in df.iterrows():
        player = row['PLAYER']
        team = row['CODETEAM']
        game = row['Gamecode']
        
        if pd.isna(player) or pd.isna(team):
            continue
            
        local_team = local_team_codes.get(game)
        
        # If team == local_team, this player's WPA is positive when Delta_WP_A is positive
        if team == local_team:
            wpa = row['Delta_WP_A']
        else:
            wpa = -row['Delta_WP_A']
            
        # Give WPA as a percentage point (-100 to 100)
        wpa_pct = wpa * 100
        
        if player not in player_wpa:
            player_wpa[player] = {'Team': team, 'Action_WPA': 0.0, 'Plays': 0}
            
        player_wpa[player]['Action_WPA'] += wpa_pct
        player_wpa[player]['Plays'] += 1
        
    res = []
    for p, d in player_wpa.items():
        if d['Plays'] > 50: # Filter for players with enough tracked actions
            res.append({
                'Player': p,
                'Team': d['Team'],
                'Action_WPA': d['Action_WPA'],
                'Plays': d['Plays']
            })
            
    res_df = pd.DataFrame(res).sort_values('Action_WPA', ascending=False).reset_index(drop=True)
    res_df['WPA_Rank'] = res_df.index + 1
    
    print(f"\n{'='*65}")
    print(f"  ACTION WIN PROBABILITY ADDED (WPA) — Euroleague 2025-26")
    print(f"{'='*65}")
    print(f"  {'Rank':<4} {'Player':<25} {'Team':<5} {'Total WPA':>10}")
    print(f"  {'-'*55}")
    for _, row in res_df.head(20).iterrows():
        print(f"  {row['WPA_Rank']:<4} {row['Player']:<25} {row['Team']:<5} {row['Action_WPA']:>9.1f}%")
        
    # Save to JSON
    res_df.to_json('wpa_ratings.json', orient='records', indent=4)
    print("\nSaved Action WPA to wpa_ratings.json")

if __name__ == '__main__':
    calculate_action_wpa()
