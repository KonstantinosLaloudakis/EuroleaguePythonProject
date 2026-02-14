import pandas as pd
import os
import json
import matplotlib.pyplot as plt
import seaborn as sns
from teeter_totter import fetch_season_data, load_team_names, get_seconds_from_time

def analyze_microwave(df):
    """
    Finds the fastest time duration for a player to score >= 10 points.
    """
    microwave_performances = []
    
    # Filter for scoring plays only
    # We need plays where a player scored points.
    # Columns usually: POINTS (for the play), PLAYER_ID, PLAYER (name)
    
    # Check if 'POINTS_A' and 'POINTS_B' columns exist
    if 'POINTS_A' not in df.columns or 'POINTS_B' not in df.columns or 'PLAYER_ID' not in df.columns:
        print("Required columns (POINTS_A, POINTS_B, PLAYER_ID) not found.")
        return pd.DataFrame()

    # Pre-process data
    # We need to calculate points scored on each play.
    processed_games = []
    
    for (season, game_code), game_df in df.groupby(['Season', 'Gamecode']):
        game_df = game_df.copy()
        
        # Sort by Time
        if 'MARKERTIME' in game_df.columns:
             game_df['SecondsRemaining'] = game_df['MARKERTIME'].apply(get_seconds_from_time)
             # Convert to continuous game time
             def get_game_seconds(row):
                period = str(row['PERIOD'])
                seconds_remaining = row['SecondsRemaining']
                period_map = {'1': 0, '2': 600, '3': 1200, '4': 1800, 'E1': 2400, 'E2': 2700, 'E3': 3000}
                start_seconds = period_map.get(period, 0)
                if period.startswith('E'):
                     elapsed = 300 - seconds_remaining
                else:
                     elapsed = 600 - seconds_remaining
                return start_seconds + elapsed
                
             game_df['GameSeconds'] = game_df.apply(get_game_seconds, axis=1)
             # Sort by Time and Score to ensure monotonic progression
             game_df = game_df.sort_values(by=['GameSeconds', 'POINTS_A', 'POINTS_B'])
        else:
            continue

        # Fill Scores
        game_df['POINTS_A'] = pd.to_numeric(game_df['POINTS_A'], errors='coerce').ffill().fillna(0)
        game_df['POINTS_B'] = pd.to_numeric(game_df['POINTS_B'], errors='coerce').ffill().fillna(0)
        
        # Calculate Points Scored on this play
        # Difference from previous row
        game_df['ScoreA_Diff'] = game_df['POINTS_A'].diff().fillna(0)
        game_df['ScoreB_Diff'] = game_df['POINTS_B'].diff().fillna(0)
        
        # Total points scored on this play (usually by one team)
        game_df['PointsScored'] = game_df['ScoreA_Diff'] + game_df['ScoreB_Diff']
        
        # Filter for scoring plays
        # Points > 0 and Points < 5 (sanity check, no 10-point plays)
        scoring_plays = game_df[(game_df['PointsScored'] > 0) & (game_df['PointsScored'] <= 4)].copy()
        
        # Filter for valid Player ID
        # Exclude empty or null player IDs
        scoring_plays = scoring_plays[scoring_plays['PLAYER_ID'].notna() & (scoring_plays['PLAYER_ID'] != "")]
        
        if not scoring_plays.empty:
            processed_games.append(scoring_plays)

    if not processed_games:
        return pd.DataFrame()
        
    scoring_df = pd.concat(processed_games)

    # Group by Game and Player
    grouped = scoring_df.groupby(['Season', 'Gamecode', 'PLAYER_ID'])
    
    MinPointsThreshold = 10
    
    count = 0
    total_groups = len(grouped)
    
    for (season, game_code, player_id), group in grouped:
        # group is sorted by time
        points = group['PointsScored'].values
        times = group['GameSeconds'].values
        player_name = group['PLAYER'].iloc[0]
        team_code = group['CODETEAM'].iloc[0]

        if season == 2024 and game_code == 5 and player_id == 'P001288':
             with open('debug_lucic.txt', 'w') as f:
                 f.write(f"DEBUG LUCIC Game 5: {player_name}\n")
                 f.write("Time(s) | Points | PlayInfo\n")
                 for p, t, info in zip(points, times, group['PLAYINFO'].fillna('')):
                     f.write(f"{t} | {p} | {info}\n")
        
        n = len(points)
        if n < 3: # Need at least a few baskets to hit 10 pts typically
            continue
            
        # Sliding Window
        # Find min duration for sum(points[i:j]) >= 10
        min_duration = float('inf')
        
        # Two pointer approach
        left = 0
        current_sum = 0
        
        for right in range(n):
            current_sum += points[right]
            
            while current_sum >= MinPointsThreshold:
                # We have valid window [left, right]
                # Duration = Time[right] - Time[left]
                # Wait: Is it Time[right] - Time[left]? 
                # Calculating "Fastest 10 points". 
                # If I score at 5:00 (2pts), 5:10 (3pts), 5:20 (5pts). Total 10.
                # Duration is 5:20 - 5:00 = 20 seconds.
                # BUT, technically the 2pts at 5:00 happened "at" 5:00. 
                # It's the span covered by the scoring events.
                
                duration = times[right] - times[left]
                # Duration must be positive (to avoid data glitches where time is identical)
                if duration > 0 and duration < min_duration:
                    min_duration = duration
                    best_window = (left, right)
                    
                # Shrink from left
                current_sum -= points[left]
                left += 1
        
        if min_duration != float('inf'):
            # Get opponent
            # The game_df has all teams, but this group might only have one.
            # We need to find the opponent from the game context or just by looking at unique teams in the full game_df?
            # Passed 'df' to analyze_microwave is the full season set.
            # But here we are iterating grouped.
            # Let's rely on the fact that we can infer it or we stored it?
            # Actually, calculating it here is tricky without the full game df.
            # But wait, we iterate `for (season, game_code, player_id), group`.
            # We don't have easy access to the opponent code *inside* this loop efficiently without pass-through.
            # SIMPLER: The 'group' contains the player's team.
            # We can lookup opponent later or pass it in?
            # Actually, let's just use a placeholder here and fill it in before saving?
            # Or better: We can find the opponent code because 'game_code' is unique for a season.
            # Let's look up opponent in the main loop or post-process.
            
            start_idx, end_idx = best_window
            start_seconds = times[start_idx]
            end_seconds = times[end_idx]
            
            microwave_performances.append({
                'Season': int(season),
                'Gamecode': int(game_code),
                'PlayerID': player_id,
                'PlayerName': player_name,
                'TeamCode': team_code,
                'DurationSeconds': min_duration,
                'PointsThreshold': MinPointsThreshold,
                'StartSeconds': start_seconds,
                'EndSeconds': end_seconds
            })
            
    return pd.DataFrame(microwave_performances)

def format_game_time(total_seconds):
    """Converts continuous game seconds back to QX - MM:SS format."""
    total_seconds = int(total_seconds)
    if total_seconds < 600:
        period = "Q1"
        remaining = 600 - total_seconds
    elif total_seconds < 1200:
        period = "Q2"
        remaining = 1200 - total_seconds
    elif total_seconds < 1800:
        period = "Q3"
        remaining = 1800 - total_seconds
    elif total_seconds < 2400:
        period = "Q4"
        remaining = 2400 - total_seconds
    else:
        # Overtime
        ot_num = (total_seconds - 2400) // 300 + 1
        period = f"OT{ot_num}"
        remaining = 300 - ((total_seconds - 2400) % 300)
    
    # Format MM:SS
    minutes = remaining // 60
    seconds = remaining % 60
    return f"{period} {minutes:02d}:{seconds:02d}"

def get_opponent(row, full_df):
    """Finds the opponent for a given game and team."""
    # This is slow if done row by row on full df.
    # Better to build a game-map of teams first.
    return "Unknown"

def main():
    start_season = 2007
    end_season = 2025
    
    print(f"Analyzing 'The Microwave' performances from {start_season} to {end_season}...")
    df = fetch_season_data(2025) # Just test with one first? No, let's go full range.
    # Re-using fetch_data from comeback_kings or teeter_totter logic?
    # Let's import fetch_data from teeter_totter.
    from teeter_totter import fetch_data
    
    df = fetch_data(start_season, end_season)
    
    if df.empty:
        print("No data found.")
        return

    microwave_df = analyze_microwave(df)
    
    if not microwave_df.empty:
        # Load Team Names
        team_mapping = load_team_names()
        microwave_df['TeamName'] = microwave_df['TeamCode'].apply(lambda x: team_mapping.get(x, x))
        
        # Build Game-Opponent Map efficiently
        # Group full df by Season, Gamecode, CODETEAM
        # But 'df' is available here.
        game_teams = df.groupby(['Season', 'Gamecode'])['CODETEAM'].unique()
        
        def find_opponent_name(row):
            try:
                teams = game_teams.loc[(row['Season'], row['Gamecode'])]
                # teams is a numpy array of team codes
                for t in teams:
                    if t != row['TeamCode'] and isinstance(t, str):
                        return team_mapping.get(t, t)
            except KeyError:
                pass
            return "Opponent"

        microwave_df['OpponentName'] = microwave_df.apply(find_opponent_name, axis=1)
        
        # Format Times
        microwave_df['StartTimeStr'] = microwave_df['StartSeconds'].apply(format_game_time)
        microwave_df['EndTimeStr'] = microwave_df['EndSeconds'].apply(format_game_time)
        
        # Sort by Duration (Ascending)
        top_microwave = microwave_df.sort_values('DurationSeconds', ascending=True).head(20)
        
        print(f"\nTop 10 Fastest {top_microwave.iloc[0]['PointsThreshold']} Points:")
        print(top_microwave[['PlayerName', 'TeamName', 'OpponentName', 'DurationSeconds', 'StartTimeStr', 'EndTimeStr']].head(10))
        
        # Save
        filename = "microwave.json"
        top_microwave.to_json(filename, orient='records', indent=4)
        print(f"Saved {filename}")
        
        # Visualize
        try:
            plt.figure(figsize=(14, 10))
            
            plot_data = top_microwave.head(10).copy()
            
            # Label
            plot_data['Label'] = (
                plot_data['PlayerName'] + "\n" +
                plot_data['TeamName'] + " vs " + plot_data['OpponentName'] + "\n" +
                "Season " + plot_data['Season'].astype(str) + " (" + plot_data['StartTimeStr'] + " - " + plot_data['EndTimeStr'] + ")"
            )
            
            sns.barplot(data=plot_data, x='DurationSeconds', y='Label', palette='hot')
            plt.title(f"The Microwave: Fastest Time to Score 10 Points ({start_season}-{end_season})", fontsize=16)
            plt.xlabel("Duration (Seconds)", fontsize=12)
            plt.ylabel("Player Performance", fontsize=12)
            plt.tight_layout()
            plt.savefig("microwave.png")
            print("Saved microwave.png")
        except Exception as e:
            print(f"Error plotting: {e}")

if __name__ == "__main__":
    main()
