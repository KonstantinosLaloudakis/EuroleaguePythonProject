import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
import json
from teeter_totter import fetch_season_data, load_team_names, get_seconds_from_time

def visualize_game_flow(season, game_code):
    """
    Visualizes the score differential over time for a specific game.
    """
    print(f"Visualizing Season {season}, Game {game_code}...")
    
    # Fetch data
    df = fetch_season_data(season)
    if df.empty:
        print("Season data not found.")
        return

    # Filter for game
    game_df = df[df['Gamecode'] == game_code].copy()
    if game_df.empty:
        print("Game data not found.")
        return

    # Sort
    if 'MARKERTIME' in game_df.columns:
         game_df['SecondsRemaining'] = game_df['MARKERTIME'].apply(get_seconds_from_time)
         game_df = game_df.sort_values(by=['PERIOD', 'SecondsRemaining'], ascending=[True, False])
    
    # Fill Scores
    game_df['POINTS_A'] = pd.to_numeric(game_df['POINTS_A'], errors='coerce').ffill().fillna(0)
    game_df['POINTS_B'] = pd.to_numeric(game_df['POINTS_B'], errors='coerce').ffill().fillna(0)
    
    # Calculate Margin (Home - Away)
    game_df['Margin'] = game_df['POINTS_A'] - game_df['POINTS_B']
    
    # Create a continuous time axis
    # Each period is 10 minutes (600 seconds)
    def get_game_time(row):
        period = row['PERIOD']
        seconds_remaining = row['SecondsRemaining']
        
        period_map = {'1': 0, '2': 10, '3': 20, '4': 30, 'E1': 40, 'E2': 45, 'E3': 50}
        start_minute = period_map.get(str(period), 0)
        
        # In a period, time goes from 10:00 (600s) to 00:00 (0s)
        # Elapsed time in period = 600 - seconds_remaining
        if str(period).startswith('E'):
             # Overtime is usually 5 mins
             elapsed_in_period = 300 - seconds_remaining
        else:
             elapsed_in_period = 600 - seconds_remaining
             
        return start_minute + (elapsed_in_period / 60)

    game_df['GameTimeMinute'] = game_df.apply(get_game_time, axis=1)
    
    # Get Team Names
    team_mapping = load_team_names()
    
    team_a_code = game_df['CODETEAM'].unique()[0] # Fallback
    team_b_code = "Opponent"

    # Try to find specific team codes
    score_a_events = game_df[game_df['POINTS_A'].diff() > 0]
    if not score_a_events.empty:
        team_a_code = score_a_events.iloc[0]['CODETEAM']
    
    score_b_events = game_df[game_df['POINTS_B'].diff() > 0]
    if not score_b_events.empty:
        team_b_code = score_b_events.iloc[0]['CODETEAM']
        
    team_a_name = team_mapping.get(team_a_code, team_a_code)
    team_b_name = team_mapping.get(team_b_code, team_b_code)
    
    final_score = f"{int(game_df.iloc[-1]['POINTS_A'])}-{int(game_df.iloc[-1]['POINTS_B'])}"

    # Plot
    plt.figure(figsize=(14, 8))
    
    # Fill area between 0 and curve
    plt.fill_between(game_df['GameTimeMinute'], game_df['Margin'], 0, where=(game_df['Margin'] >= 0), interpolate=True, color='red', alpha=0.3, label=team_a_name)
    plt.fill_between(game_df['GameTimeMinute'], game_df['Margin'], 0, where=(game_df['Margin'] <= 0), interpolate=True, color='blue', alpha=0.3, label=team_b_name)
    
    plt.plot(game_df['GameTimeMinute'], game_df['Margin'], color='black', linewidth=1)
    
    plt.axhline(0, color='black', linestyle='--', linewidth=0.8)
    
    # Add vertical lines for quarters
    for q in [10, 20, 30, 40]:
        plt.axvline(q, color='gray', linestyle=':', alpha=0.5)
        
    plt.title(f"The 'Teeter-Totter' Game Flow\n{team_a_name} vs {team_b_name} ({season})\nFinal: {final_score}", fontsize=16)
    plt.xlabel("Game Minute", fontsize=12)
    plt.ylabel(f"Score Lead ({team_a_name} + / {team_b_name} -)", fontsize=12)
    plt.legend(loc='upper right')
    plt.grid(True, alpha=0.3)
    
    output_file = f"game_flow_{season}_{game_code}.png"
    plt.savefig(output_file)
    print(f"Saved {output_file}")

if __name__ == "__main__":
    # Target the #1 Volatile Game: Crvena Zvezda vs Maccabi (2025) -> Gamecode 268
    # Based on teeter_totter.json
    visualize_game_flow(2025, 268)
