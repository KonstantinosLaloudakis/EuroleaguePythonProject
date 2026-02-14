import pandas as pd
from euroleague_api import play_by_play_data
import os
import json
import matplotlib.pyplot as plt
import seaborn as sns

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
        # Optimize types to save memory/time
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

def analyze_comebacks(df):
    """
    Identifies the largest comebacks.
    A comeback is defined as a win by a team that trailed by X points.
    """
    comebacks = []
    
    # Sort chronologically (Global sort might be slow, doing it per game is better but we need grouping first)
    # We do NOT pre-calculate points globally because we need ffill within groups.
    
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

        # Determine Winner
        # We look at the LAST row's score
        final_state = game_df.iloc[-1]
        score_a_final = final_state['POINTS_A']
        score_b_final = final_state['POINTS_B']
        
        # Determine Teams
        teams = game_df['CODETEAM'].unique()
        teams = [t for t in teams if pd.notna(t) and t != '']
        
        if score_a_final > score_b_final:
            winner_is_a = True
            final_margin = score_a_final - score_b_final
        elif score_b_final > score_a_final:
            winner_is_a = False
            final_margin = score_b_final - score_a_final
        else:
            # Tie?
            continue
            
        # Calculate Margin relative to Winner
        if winner_is_a:
            game_df['WinnerMargin'] = game_df['POINTS_A'] - game_df['POINTS_B']
            winner_code = teams[0] if len(teams) > 0 else "UNK" # Assumption: teams[0] is A? No, need to be careful.
            # Safety check on teams order. CODETEAM usually maps to A/B but let's just find the team with the winning score.
            # Actually, the dataframe has 'CODETEAM'. Let's verify which is A and B.
            # 'CODETEAM' column is usually the team doing the action.
            # A better way is to get the team codes from the 'TEAM' column if available or metadata.
            # Let's simple use the 'CODETEAM' from the PlayByPlay.
            # But wait, A and B depends on who is home/away.
            # Let's just store "Home" and "Away" codes if we can find them.
            # Actually, `analyze_comebacks` iterates a single game.
            # We can find the codes from specific events.
            # Let's just return "Home" and "Away" for now and try to extract codes from the unique teams list.
            # The API returns data where 'CODETEAM' is the team code.
            
            # Let's try to identify Team A and Team B codes.
            # Usually the first team in 'CODETEAM' unique list is Home? Not guaranteed.
            # Let's look for a row where POINTS_A increases (Team A scored) and see the CODETEAM.
            
            team_a_code = "TeamA"
            team_b_code = "TeamB"
            
            # Find a scoring play for A
            score_a_events = game_df[game_df['POINTS_A'].diff() > 0]
            if not score_a_events.empty:
                team_a_code = score_a_events.iloc[0]['CODETEAM']
                
            # Find a scoring play for B
            score_b_events = game_df[game_df['POINTS_B'].diff() > 0]
            if not score_b_events.empty:
                team_b_code = score_b_events.iloc[0]['CODETEAM']
            
            winner_code = team_a_code if winner_is_a else team_b_code
            loser_code = team_b_code if winner_is_a else team_a_code

        else:
            game_df['WinnerMargin'] = game_df['POINTS_B'] - game_df['POINTS_A']
            
            # Same logic to find codes
            team_a_code = "TeamA"
            team_b_code = "TeamB"
            
            # Find a scoring play for A
            score_a_events = game_df[game_df['POINTS_A'].diff() > 0]
            if not score_a_events.empty:
                team_a_code = score_a_events.iloc[0]['CODETEAM']
            
            # Find a scoring play for B
            score_b_events = game_df[game_df['POINTS_B'].diff() > 0]
            if not score_b_events.empty:
                team_b_code = score_b_events.iloc[0]['CODETEAM']
                
            winner_code = team_b_code
            loser_code = team_a_code
            
        # Find minimum margin (deepest deficit)
        min_margin_row = game_df.loc[game_df['WinnerMargin'].idxmin()]
        min_margin = min_margin_row['WinnerMargin']
        
        if min_margin < 0:
            max_deficit = abs(min_margin)
            
            # Format Time string
            time_str = f"Q{min_margin_row['PERIOD']} - {min_margin_row['MARKERTIME']}"
            score_at_deficit = f"{int(min_margin_row['POINTS_A'])}-{int(min_margin_row['POINTS_B'])}"
            
            comebacks.append({
                'Season': int(season),
                'Gamecode': int(game_code),
                'Winner': "Home" if winner_is_a else "Away",
                'WinnerCode': winner_code,
                'LoserCode': loser_code,
                'MaxDeficit': int(max_deficit),
                'DeficitTime': time_str,
                'DeficitScore': score_at_deficit,
                'FinalScore': f"{int(score_a_final)}-{int(score_b_final)}"
            })
            
    return pd.DataFrame(comebacks)

def parse_column_string(col_str):
    """Parses a dataframe-like string into a dict {index: value}"""
    result = {}
    lines = col_str.strip().split('\n')
    for line in lines:
        parts = line.strip().split(None, 1)
        if len(parts) >= 2:
            idx_str = parts[0]
            val = parts[1]
            try:
                idx = int(idx_str)
                result[idx] = val
            except ValueError:
                continue
    return result

def load_team_names():
    try:
        with open("teamNames.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            
        codes_map = parse_column_string(data['team1'])
        names_map = parse_column_string(data['team2'])
        
        mapping = {}
        common_indices = set(codes_map.keys()) & set(names_map.keys())
        
        # Use setdefault to keep the FIRST mapping (lower index)
        for idx in sorted(common_indices):
            code_entry = codes_map[idx].strip()
            name_entry = names_map[idx].strip()
            
            sub_codes = code_entry.split(';')
            for sc in sub_codes:
                sc = sc.strip()
                if sc:
                    mapping.setdefault(sc, name_entry)
                    
        return mapping
    except FileNotFoundError:
        return {}

def main():
    start_season = 2007
    end_season = 2025
    
    print(f"Analyzing comebacks from {start_season} to {end_season}...")
    df = fetch_data(start_season, end_season)
    
    if df.empty:
        print("No data found.")
        return

    comebacks_df = analyze_comebacks(df)
    
    if not comebacks_df.empty:
        # Load Team Names
        team_mapping = load_team_names()
        
        # Apply Mapping
        def get_team_name(code):
            # Clean code if it has extra spaces or if it's nan
            if pd.isna(code): return "Unknown"
            code = str(code).strip()
            return team_mapping.get(code, code)

        comebacks_df['WinnerName'] = comebacks_df['WinnerCode'].apply(get_team_name)
        comebacks_df['LoserName'] = comebacks_df['LoserCode'].apply(get_team_name)

        # Filter for minimum 15 points deficit
        filtered_comebacks = comebacks_df[comebacks_df['MaxDeficit'] >= 15].copy()
        
        # Sort by deficit
        sorted_comebacks = filtered_comebacks.sort_values('MaxDeficit', ascending=False)
        
        print(f"\nFound {len(sorted_comebacks)} comebacks with >= 15 points deficit.")
        print("\nTop 10 Comebacks:")
        print(sorted_comebacks[['Season', 'Gamecode', 'WinnerName', 'MaxDeficit', 'DeficitTime', 'FinalScore']].head(10))
        
        # Save ALL qualifying comebacks to JSON
        filename = "comeback_kings.json"
        sorted_comebacks.to_json(filename, orient='records', indent=4)
        print(f"Saved {filename} with {len(sorted_comebacks)} entries.")
        
        # Visualize Top 10-15
        try:
            plt.figure(figsize=(14, 10))
            
            # Prepare data for plotting
            plot_data = sorted_comebacks.head(15).copy()
            
            # Create a label WITHOUT Gamecode
            # e.g. "Real Madrid vs Olympiacos (2012)\nOvercame 28 pts (Down 40-68 @ Q3 - 05:00)\nFinal: 85-80"
            plot_data['Label'] = (
                plot_data['WinnerName'] + " vs " + plot_data['LoserName'] + " (" + plot_data['Season'].astype(str) + ")\n" +
                "Overcame " + plot_data['MaxDeficit'].astype(str) + " pts (Down " + plot_data['DeficitScore'] + " @ " + plot_data['DeficitTime'] + ")\n" +
                "Final: " + plot_data['FinalScore']
            )
            
            sns.barplot(data=plot_data, x='MaxDeficit', y='Label', palette='magma')
            plt.title(f"Greatest Comebacks in Euroleague History (2007-2024)\nLargest Deficit Overcome by the Winning Team (Min 15 pts)", fontsize=16)
            plt.xlabel("Max Point Deficit", fontsize=12)
            plt.ylabel("Matchup", fontsize=12)
            plt.tight_layout()
            plt.savefig("comeback_kings.png")
            print("Saved comeback_kings.png")
        except Exception as e:
            print(f"Error plotting: {e}")

if __name__ == "__main__":
    main()
