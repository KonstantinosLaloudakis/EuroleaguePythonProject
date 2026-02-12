import pandas as pd
from euroleague_api import play_by_play_data
import matplotlib.pyplot as plt
import seaborn as sns
import os

def get_seconds_from_time(time_str):
    """Converts MM:SS time string to total seconds."""
    try:
        minutes, seconds = map(int, str(time_str).split(':'))
        return minutes * 60 + seconds
    except (ValueError, AttributeError):
        return 0

def fetch_season_data(season, force_update=False):
    """
    Fetches data for a single season, using local cache if available.
    """
    cache_dir = "data"
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
        
    cache_file = os.path.join(cache_dir, f"pbp_{season}.csv")
    
    if not force_update and os.path.exists(cache_file):
        print(f"Loading data for season {season} from cache...")
        return pd.read_csv(cache_file)
    
    print(f"Fetching data for season {season} from API...")
    pbp = play_by_play_data.PlayByPlay()
    try:
        df = pbp.get_game_play_by_play_data_multiple_seasons(season, season)
        if not df.empty:
            df.to_csv(cache_file, index=False)
            print(f"Saved data for season {season} to cache.")
        return df
    except Exception as e:
        print(f"Error fetching data for season {season}: {e}")
        return pd.DataFrame()

def fetch_data(start_season, end_season, force_update=False):
    """Fetches play-by-play data for a range of seasons."""
    all_data = []
    for season in range(start_season, end_season + 1):
        season_df = fetch_season_data(season, force_update)
        if not season_df.empty:
            all_data.append(season_df)
    
    if all_data:
        return pd.concat(all_data, ignore_index=True)
    else:
        return pd.DataFrame()

def analyze_heat_check(df, threshold=8):
    """
    Identifies 'The Heat Check': Most consecutive points scored by a single player for their team.
    (Consecutive Team Points)
    Only keeps streaks of `threshold` points or more.
    """
    print(f"Analyzing Heat Checks (Threshold: {threshold})...")
    heat_checks = []

    # Process each game separately
    for (season, game_code), game_df in df.groupby(['Season', 'Gamecode']):
        # Sort by Period, Time (descending usually in PBP but we want chronological for processing loops often)
        # Euroleague PBP 'Time' is usually time REMAINING. So 10:00 is start. 00:00 is end.
        # So sorting by Period (asc) and Time (desc) gives chronological order.
        if 'MARKERTIME' in game_df.columns:
             game_df['SecondsRemaining'] = game_df['MARKERTIME'].apply(get_seconds_from_time)
        else:
            continue
            
        game_df = game_df.sort_values(by=['PERIOD', 'SecondsRemaining'], ascending=[True, False])

        # Identify teams and opponent
        teams = game_df['CODETEAM'].unique()
        # Filter out NaN or None if any (sometimes happens in raw data)
        teams = [t for t in teams if pd.notna(t)]
        
        opponent_map = {}
        if len(teams) == 2:
            opponent_map[teams[0]] = teams[1]
            opponent_map[teams[1]] = teams[0]
        else:
            # Fallback or edge case
            for t in teams:
                opponent_map[t] = "UNKNOWN"

        # Trackers for Home (A) and Away (B)
        # We need to correctly identify which team scored. 
        # CODETEAM is the team code.
        
        # We need to track streaks PER TEAM.
        # team_streaks = { 'TEAM_CODE_A': {'Player': ..., 'Points': ...}, 'TEAM_CODE_B': ... }
        team_streaks = {}

        for _, row in game_df.iterrows():
            play_type = row.get('PLAYTYPE')
            player = row.get('PLAYER')
            team = row.get('CODETEAM')
            points = 0

            # Determine points
            if play_type == '2FGM':
                points = 2
            elif play_type == '3FGM':
                points = 3
            elif play_type == 'FTM':
                points = 1
            
            if points > 0:
                if team not in team_streaks:
                    team_streaks[team] = {'Player': None, 'Points': 0}
                
                streak_data = team_streaks[team]
                
                if streak_data['Player'] == player:
                    streak_data['Points'] += points
                else:
                    # Streak broken by teammate?
                    # Yes. Verify if previous streak exists and save it.
                    if streak_data['Points'] >= threshold:
                        heat_checks.append({
                            'Season': row.get('Season'),
                            'Gamecode': game_code,
                            'Player': streak_data['Player'],
                            'Team': team,
                            'Opponent': opponent_map.get(team, "UNKNOWN"),
                            'StreakPoints': streak_data['Points']
                        })
                    
                    # Start new streak
                    streak_data['Player'] = player
                    streak_data['Points'] = points
        
        # End of game, save last streaks
        for team, streak_data in team_streaks.items():
             if streak_data['Points'] >= threshold:
                heat_checks.append({
                    'Season': game_df.iloc[0].get('Season'),
                    'Gamecode': game_code,
                    'Player': streak_data['Player'],
                    'Team': team,
                    'Opponent': opponent_map.get(team, "UNKNOWN"),
                    'StreakPoints': streak_data['Points']
                })

    return pd.DataFrame(heat_checks)

def analyze_quarter_master(df, threshold=8):
    """
    Identifies 'Quarter Master': Most points in a single quarter.
    Only keeps quarters with `threshold` points or more.
    """
    print(f"Analyzing Quarter Masters (Threshold: {threshold})...")
    
    # Filter for scoring plays
    scoring_plays = df[df['PLAYTYPE'].isin(['2FGM', '3FGM', 'FTM'])].copy()
    
    scoring_plays['Points'] = 0
    scoring_plays.loc[scoring_plays['PLAYTYPE'] == '2FGM', 'Points'] = 2
    scoring_plays.loc[scoring_plays['PLAYTYPE'] == '3FGM', 'Points'] = 3
    scoring_plays.loc[scoring_plays['PLAYTYPE'] == 'FTM', 'Points'] = 1
    
    # Group by Season, Game, Period, Player
    # Ensure PERIOD is clean
    scoring_plays = scoring_plays[scoring_plays['PERIOD'].astype(str).str.isdigit()] # Basic cleaning
    
    quarter_stats = scoring_plays.groupby(['Season', 'Gamecode', 'PERIOD', 'PLAYER', 'CODETEAM'])['Points'].sum().reset_index()
    
    # Filter by threshold
    quarter_stats = quarter_stats[quarter_stats['Points'] >= threshold].copy()

    # Add Opponent
    # Build a mapping of (Season, Game, Team) -> Opponent
    # This is a bit computationally expensive if we iterate, so let's use pandas merge
    game_teams = df[['Season', 'Gamecode', 'CODETEAM']].drop_duplicates()
    
    # Self-join to find opponents
    # We want to match (Season, Gamecode) but different CODETEAM
    opponents = pd.merge(game_teams, game_teams, on=['Season', 'Gamecode'], suffixes=('', '_opp'))
    opponents = opponents[opponents['CODETEAM'] != opponents['CODETEAM_opp']]
    
    # Merge opponent info back to stats
    quarter_stats = pd.merge(quarter_stats, opponents, on=['Season', 'Gamecode', 'CODETEAM'], how='left')
    
    # Rename for clarity
    quarter_stats.rename(columns={'CODETEAM_opp': 'Opponent'}, inplace=True)
    
    return quarter_stats

def visualize_results(heat_checks_df, quarter_master_df, season_label):
    """Creates visualizations for the results."""
    
    # 1. Heat Checks Visualization
    if not heat_checks_df.empty:
        plt.figure(figsize=(12, 6))
        top_heat_checks = heat_checks_df.sort_values('StreakPoints', ascending=False).head(10)
        
        # Add Season info to labels if multiple seasons
        if 'Season' in top_heat_checks.columns:
             top_heat_checks['PlayerLabel'] = top_heat_checks['Player'] + " (" + top_heat_checks['Season'].astype(str) + ")"
        else:
             top_heat_checks['PlayerLabel'] = top_heat_checks['Player']

        sns.barplot(data=top_heat_checks, x='StreakPoints', y='PlayerLabel', hue='Team', dodge=False)
        plt.title(f"Top 10 'Heat Checks' (Consecutive Team Points) - {season_label}")
        plt.xlabel("Consecutive Points")
        plt.ylabel("Player (Season)")
        plt.tight_layout()
        plt.savefig(f'heat_checks_{season_label}.png')
        print(f"Saved heat_checks_{season_label}.png")
    
    # 2. Quarter Master Visualization
    if not quarter_master_df.empty:
        plt.figure(figsize=(12, 6))
        top_quarters = quarter_master_df.sort_values('Points', ascending=False).head(10).copy()
        
        # Create label for Y axis (Player + Q# + Season)
        top_quarters['Label'] = top_quarters['PLAYER'] + " (Q" + top_quarters['PERIOD'].astype(str) + ", " + top_quarters['Season'].astype(str) + ")"
        
        sns.barplot(data=top_quarters, x='Points', y='Label', hue='CODETEAM', dodge=False)
        plt.title(f"Top 10 'Quarter Masters' (Points in a Single Quarter) - {season_label}")
        plt.xlabel("Points in Quarter")
        plt.ylabel("Player (Quarter, Season)")
        plt.tight_layout()
        plt.savefig(f'quarter_masters_{season_label}.png')
        print(f"Saved quarter_masters_{season_label}.png")

import json

def save_results(heat_checks_df, quarter_master_df, season_label):
    """Saves the results to JSON files."""
    if not heat_checks_df.empty:
        filename = f'heat_checks_{season_label}.json'
        # Sort for better readability in JSON
        heat_checks_df.sort_values('StreakPoints', ascending=False).to_json(filename, orient='records', indent=4, force_ascii=False)
        print(f"Saved {filename}")

    if not quarter_master_df.empty:
        filename = f'quarter_masters_{season_label}.json'
        # Sort for better readability in JSON
        quarter_master_df.sort_values('Points', ascending=False).to_json(filename, orient='records', indent=4, force_ascii=False)
        print(f"Saved {filename}")

def main():
    start_season = 2007
    end_season = 2024
    
    season_label = f"{start_season}_{end_season}" if start_season != end_season else f"{start_season}"
    
    df = fetch_data(start_season, end_season)
    
    if df.empty:
        print("No data found.")
        return

    # -- Heat Check --
    heat_df = analyze_heat_check(df)
    if not heat_df.empty:
        print("\nTop 5 Heat Checks:")
        print(heat_df.sort_values('StreakPoints', ascending=False).head(5)[['Player', 'Team', 'StreakPoints', 'Gamecode', 'Season']])
    
    # -- Quarter Master --
    qm_df = analyze_quarter_master(df)
    if not qm_df.empty:
        print("\nTop 5 Quarter Masters:")
        print(qm_df.sort_values('Points', ascending=False).head(5)[['PLAYER', 'CODETEAM', 'PERIOD', 'Points', 'Gamecode', 'Season']])

    # -- Visualize & Save --
    if not heat_df.empty and not qm_df.empty:
        visualize_results(heat_df, qm_df, season_label)
        save_results(heat_df, qm_df, season_label)

if __name__ == "__main__":
    main()
