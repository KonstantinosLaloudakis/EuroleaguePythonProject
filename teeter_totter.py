import pandas as pd
from euroleague_api import play_by_play_data
import os
import json
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

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
        return pd.read_csv(cache_file, dtype={'Season': int, 'Gamecode': int, 'PERIOD': str})
    
    print(f"Fetching data for season {season} from API...")
    pbp = play_by_play_data.PlayByPlay()
    try:
        df = pbp.get_game_play_by_play_data_multiple_seasons(season, season)
        if not df.empty:
            df = pd.DataFrame(df)
            df.to_csv(cache_file, index=False)
            print(f"Saved data for season {season} to cache.")
        return df
    except Exception as e:
        print(f"Error fetching data for season {season}: {e}")
        return pd.DataFrame()

def fetch_data(start_season, end_season):
    """Fetches play-by-play data for a range of seasons."""
    all_data = []
    for season in range(start_season, end_season + 1):
        season_df = fetch_season_data(season)
        if not season_df.empty:
            all_data.append(season_df)
    
    if all_data:
        return pd.concat(all_data, ignore_index=True)
    else:
        return pd.DataFrame()

def load_team_names():
    mapping_file = 'team_code_mapping.json'
    if os.path.exists(mapping_file):
        with open(mapping_file, 'r') as f:
            return json.load(f)
    return {}

def analyze_volatility(df):
    """
    Identifies games with the most lead changes and ties.
    """
    volatility_stats = []
    
    # Group by game
    for (season, game_code), game_df in df.groupby(['Season', 'Gamecode']):
        if game_df.empty:
            continue
            
        game_df = game_df.copy()
        
        # Sort first
        if 'MARKERTIME' in game_df.columns:
             game_df['SecondsRemaining'] = game_df['MARKERTIME'].apply(get_seconds_from_time)
             game_df = game_df.sort_values(by=['PERIOD', 'SecondsRemaining'], ascending=[True, False])
        else:
            continue

        # Correctly Fill Scores
        game_df['POINTS_A'] = pd.to_numeric(game_df['POINTS_A'], errors='coerce').ffill().fillna(0)
        game_df['POINTS_B'] = pd.to_numeric(game_df['POINTS_B'], errors='coerce').ffill().fillna(0)
        
        # Calculate Margin
        game_df['Margin'] = game_df['POINTS_A'] - game_df['POINTS_B']
        
        # Determine Leader (-1: B, 0: Tie, 1: A)
        game_df['Leader'] = np.sign(game_df['Margin'])
        
        # Count Ties
        # Only count when the game *becomes* tied (transition from non-tie to tie)
        # Shift leader to compare with previous state
        prev_leader = game_df['Leader'].shift(1).fillna(0) # Assume start at 0 (tied)
        
        # A tie event is where Leader is 0 AND PrevLeader was NOT 0 (it became tied)
        # Exception: The start of the game (0-0) is technically a tie but usually not interesting.
        # If we fillna(0), the first row (0=0) won't count.
        # But if we want to count "tying shots", we look for transition.
        ties_count = ((game_df['Leader'] == 0) & (prev_leader != 0)).sum()
        
        # Count Lead Changes
        # Filter out Ties to see pure lead swaps (A -> Tie -> B counts as A->B)
        non_tie_states = game_df[game_df['Leader'] != 0]['Leader']
        
        if len(non_tie_states) > 0:
            # A lead change is when the sign changes (diff is non-zero)
            # The first entry is not a change
            lead_changes_count = (non_tie_states.diff().fillna(0) != 0).sum()
        else:
            lead_changes_count = 0
            
        # Get Teams
        teams = game_df['CODETEAM'].unique()
        # Clean teams list
        teams = [t for t in teams if pd.notna(t) and t != '']
        
        # Try to identify Home/Away codes specifically from scoring
        team_a_code = "TeamA"
        team_b_code = "TeamB"
        
        score_a_events = game_df[game_df['POINTS_A'].diff() > 0]
        if not score_a_events.empty:
            team_a_code = score_a_events.iloc[0]['CODETEAM']
            
        score_b_events = game_df[game_df['POINTS_B'].diff() > 0]
        if not score_b_events.empty:
            team_b_code = score_b_events.iloc[0]['CODETEAM']
            
        final_score_str = f"{int(game_df.iloc[-1]['POINTS_A'])}-{int(game_df.iloc[-1]['POINTS_B'])}"
        
        volatility_stats.append({
            'Season': int(season),
            'Gamecode': int(game_code),
            'TeamA': team_a_code,
            'TeamB': team_b_code,
            'LeadChanges': int(lead_changes_count),
            'Ties': int(ties_count),
            'FinalScore': final_score_str
        })
            
    return pd.DataFrame(volatility_stats)

def main():
    start_season = 2007
    end_season = 2025
    
    print(f"Analyzing game volatility from {start_season} to {end_season}...")
    df = fetch_data(start_season, end_season)
    
    if df.empty:
        print("No data found.")
        return

    volatility_df = analyze_volatility(df)
    
    if not volatility_df.empty:
        # Load Team Names
        team_mapping = load_team_names()
        
        def get_team_name(code):
            if pd.isna(code): return "Unknown"
            code = str(code).strip()
            return team_mapping.get(code, code)

        volatility_df['TeamAName'] = volatility_df['TeamA'].apply(get_team_name)
        volatility_df['TeamBName'] = volatility_df['TeamB'].apply(get_team_name)

        # Sort by Lead Changes
        top_volatile = volatility_df.sort_values('LeadChanges', ascending=False).head(20)
        
        print("\nTop 10 Most Volatile Games (Most Lead Changes):")
        print(top_volatile[['Season', 'Gamecode', 'TeamAName', 'TeamBName', 'LeadChanges', 'Ties', 'FinalScore']].head(10))
        
        # Save
        filename = "teeter_totter.json"
        top_volatile.to_json(filename, orient='records', indent=4)
        print(f"Saved {filename}")
        
        # Visualize
        try:
            plt.figure(figsize=(14, 10))
            
            # Prepare data
            plot_data = top_volatile.head(10).copy()
            
            plot_data['Label'] = (
                plot_data['TeamAName'] + " vs " + plot_data['TeamBName'] + "\n" +
                "Season " + plot_data['Season'].astype(str) + 
                "\n[Changes: " + plot_data['LeadChanges'].astype(str) + ", Ties: " + plot_data['Ties'].astype(str) + "]" +
                "\nFinal: " + plot_data['FinalScore']
            )
            
            sns.barplot(data=plot_data, x='LeadChanges', y='Label', palette='coolwarm')
            plt.title(f"The Teeter-Totter: Most Lead Changes in a Game ({start_season}-{end_season})", fontsize=16)
            plt.xlabel("Number of Lead Changes", fontsize=12)
            plt.ylabel("Matchup", fontsize=12)
            plt.tight_layout()
            plt.savefig("teeter_totter.png")
            print("Saved teeter_totter.png")
        except Exception as e:
            print(f"Error plotting: {e}")

if __name__ == "__main__":
    main()
