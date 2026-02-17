import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
import time
from euroleague_api.EuroLeagueData import EuroLeagueData

# --- Configuration ---
START_SEASON = 2024
END_SEASON = 2025
SEASONS = range(START_SEASON, END_SEASON + 1)
CACHE_DIR = "data_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# Team name mapping for consistent display
TEAM_NAME_OVERRIDES = {
    "PAN": "Panathinaikos",
    "OLY": "Olympiacos",
    "RMB": "Real Madrid",
    "BAR": "Barcelona",
    "FBB": "Fenerbahce",
    "MCO": "Monaco",
    "TEL": "Maccabi", # Old code for Maccabi
    "MTA": "Maccabi",
    "EFS": "Anadolu Efes",
    "IST": "Anadolu Efes", # frequent changes
    "PAR": "Partizan",
    "CZV": "Crvena Zvezda",
    "RED": "Crvena Zvezda", # recent change
    "ZAL": "Zalgiris",
    "MIL": "Armani Milan",
    "EA7": "Armani Milan", # sponsored
    "VIR": "Virtus Bologna",
    "BAS": "Baskonia",
    "VAL": "Valencia",
    "BAY": "Bayern Munich",
    "MUN": "Bayern Munich", # alt code
    "BER": "ALBA Berlin",
    "ASV": "ASVEL",
    "PRS": "Paris",
    "DUB": "Dubai BC",
    "MAD": "Real Madrid",
    "ULK": "Fenerbahce",
    "HTA": "Hapoel Tel Aviv",
    "PAM": "Valencia",
}

def get_full_team_name(code):
    return TEAM_NAME_OVERRIDES.get(code, code)

class TheGauntlet:
    def __init__(self):
        self.api = EuroLeagueData()

    def get_season_games(self, season):
        """
        Fetches or loads game metadata for a season.
        Returns a DataFrame with game results.
        """
        cache_file = os.path.join(CACHE_DIR, f"games_{season}.csv")
        
        if os.path.exists(cache_file):
            print(f"Loading cached games for {season}...")
            df = pd.read_csv(cache_file)
        else:
            print(f"Fetching games for {season} from API...")
            try:
                df = self.api.get_game_metadata_season(season)
                df.to_csv(cache_file, index=False)
                time.sleep(1) # Be nice to API
            except Exception as e:
                print(f"Error fetching season {season}: {e}")
                return pd.DataFrame()
        
        # Ensure played games only
        if 'played' in df.columns:
            df = df[df['played'] == True].copy()
            
        return df

    def process_season_data(self, season):
        """
        Processes season data to create a team-by-round margin matrix.
        """
        df = self.get_season_games(season)
        if df.empty:
            return None

        # Structure to hold [Team, Round] -> Margin
        # We need a list of all teams and rounds
        teams = set(df['homecode'].unique()) | set(df['awaycode'].unique())
        rounds = sorted(df['gameday'].unique())
        
        # Initialize dictionary to store margins
        # format: data[(team, round)] = margin (positive = win, negative = loss)
        margins = {}
        opponents = {}
        
        for _, row in df.iterrows():
            round_num = row['gameday']
            home_team = row['homecode']
            away_team = row['awaycode']
            home_score = row['homescore']
            away_score = row['awayscore']
            
            margin = home_score - away_score
            
            # Record for home team
            margins[(home_team, round_num)] = margin
            opponents[(home_team, round_num)] = away_team
            
            # Record for away team (margin is inverted)
            margins[(away_team, round_num)] = -margin
            opponents[(away_team, round_num)] = home_team

        return margins, opponents, sorted(list(teams)), rounds, df

    def generate_heatmap(self, season):
        """
        Generates The Gauntlet heatmap for a season.
        """
        margins, opponents, teams, rounds, df = self.process_season_data(season)
        if not margins:
            print(f"No data for {season}")
            return

        # Sort teams by total margin (point differential) to put best teams on top
        team_diffs = {team: sum(margins.get((team, r), 0) for r in rounds) for team in teams}
        sorted_teams = sorted(teams, key=lambda t: team_diffs[t], reverse=True)

        # Create DataFrame for plotting
        plot_data = []
        for team in sorted_teams:
            row = []
            for r in rounds:
                row.append(margins.get((team, r), np.nan)) # Use NaN for buy weeks/missing
            plot_data.append(row)
            
        df_plot = pd.DataFrame(plot_data, index=[get_full_team_name(t) for t in sorted_teams], columns=rounds)

        # Plotting
        plt.figure(figsize=(20, 12))
        
        # Custom diverging colormap: Red (Loss) -> White (Close) -> Green (Win)
        cmap = sns.diverging_palette(10, 130, as_cmap=True, center="light")
        
        # Draw heatmap
        ax = sns.heatmap(df_plot, cmap=cmap, center=0, annot=True, fmt=".0f", 
                         cbar_kws={'label': 'Point Differential'}, 
                         linewidths=1, linecolor='white')
        
        plt.title(f"THE GAUNTLET: Euroleague {season}-{season+1} Margin of Victory", fontsize=20, weight='bold')
        plt.xlabel("Round", fontsize=14)
        plt.ylabel("Team (Ranked by Total +/-)", fontsize=14)
        
        # Rotate x labels for readability
        plt.xticks(rotation=0)
        
        plt.tight_layout()
        filename = f"the_gauntlet_{season}.png"
        plt.savefig(filename, dpi=300)
        print(f"Generated {filename}")
        plt.close()

        # --- Additional Analysis: "The Grinder" & "The Steamroller" ---
        print(f"\n--- Euroleague {season} Superlatives ---")
        
        flat_margins = []
        for team in teams:
            team_margins = [margins.get((team, r), 0) for r in rounds if (team, r) in margins]
            flat_margins.extend([(team, m) for m in team_margins])

        # The Steamroller: Wins by 15+
        steamrollers = sorted([x for x in flat_margins if x[1] >= 15], key=lambda x: x[1], reverse=True)
        print(f"Top Steamrollers (15+ win): {len(steamrollers)} games")
        
        # The Grinder: Games decided by <= 5
        grinders = [x for x in flat_margins if abs(x[1]) <= 5]
        grinder_counts = pd.Series([x[0] for x in grinders]).value_counts().head(3)
        print("The Grinders (Most games ≤ 5 pts):")
        print(grinder_counts)

        # --- New Visualizations ---
        self.generate_cumulative_diff_chart(teams, rounds, margins, season)
        self.generate_home_away_scatter(teams, rounds, margins, df, season)

    def generate_cumulative_diff_chart(self, teams, rounds, margins, season):
        """
        Generates 'The Mountain': Cumulative Point Differential over the season.
        """
        plt.figure(figsize=(16, 10))
        
        # Calculate cumulative margins
        final_diffs = []
        
        for team in teams:
            cum_score = 0
            history = []
            for r in rounds:
                margin = margins.get((team, r), 0)
                # Handle NaNs effectively (treat as 0 for cumulative, or skip?)
                # Treating as 0 is safer for continuity
                if pd.isna(margin): 
                    margin = 0
                cum_score += margin
                history.append(cum_score)
            
            final_diffs.append((team, cum_score))
            
            # Highlight top 4 and bottom 2
            # We'll determine colors after we sort everything, but for now plop lines
            # Mapping color later
            
        # Sort to find top/bottom for highlighting
        final_diffs.sort(key=lambda x: x[1], reverse=True)
        top_teams = {x[0] for x in final_diffs[:4]}
        bottom_teams = {x[0] for x in final_diffs[-2:]}
        
        for team in teams:
            cum_score = 0
            history = []
            for r in rounds:
                margin = margins.get((team, r), 0)
                if pd.isna(margin): margin = 0
                cum_score += margin
                history.append(cum_score)

            full_name = get_full_team_name(team)
            
            if team in top_teams:
                plt.plot(rounds, history, linewidth=3, label=f"{full_name} ({int(history[-1])})")
            elif team in bottom_teams:
                plt.plot(rounds, history, linewidth=3, linestyle='--', label=f"{full_name} ({int(history[-1])})")
            else:
                plt.plot(rounds, history, color='grey', alpha=0.3, linewidth=1)
                
                # Label end of line for mid-teams if not too crowded? 
                # Maybe just skip to avoid clutter
        
        plt.title(f"THE MOUNTAIN: Cumulative Point Differential ({season})", fontsize=20, weight='bold')
        plt.xlabel("Round", fontsize=14)
        plt.ylabel("Cumulative +/-", fontsize=14)
        plt.axhline(0, color='black', linewidth=1, linestyle='-')
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        filename = f"the_mountain_{season}.png"
        plt.savefig(filename, dpi=300)
        print(f"Generated {filename}")
        plt.close()

    def generate_home_away_scatter(self, teams, rounds, margins, df, season):
        """
        Generates 'The Fortress': Average Home Margin vs Average Away Margin.
        """
        home_margins = {t: [] for t in teams}
        away_margins = {t: [] for t in teams}

        for _, row in df.iterrows():
            home = row['homecode']
            away = row['awaycode']
            margin = row['homescore'] - row['awayscore']
            
            home_margins[home].append(margin)
            away_margins[away].append(-margin)
            
        avg_home = {t: np.mean(v) if v else 0 for t, v in home_margins.items()}
        avg_away = {t: np.mean(v) if v else 0 for t, v in away_margins.items()}

        plt.figure(figsize=(12, 12))
        ax = plt.gca()
        
        # Plot points
        x_vals = []
        y_vals = []
        labels = []
        
        for team in teams:
            x = avg_home[team]
            y = avg_away[team]
            x_vals.append(x)
            y_vals.append(y)
            labels.append(team)
            
            plt.scatter(x, y, s=100, alpha=0.7)
            plt.text(x+0.2, y+0.2, get_full_team_name(team), fontsize=9)

        # Add quadrants
        plt.axhline(0, color='black', linestyle='-', linewidth=1)
        plt.axvline(0, color='black', linestyle='-', linewidth=1)
        
        # Quadrant Labels
        max_limit = max(max(abs(min(x_vals)), max(x_vals)), max(abs(min(y_vals)), max(y_vals))) + 2
        limit = max_limit
        
        plt.xlim(-limit, limit)
        plt.ylim(-limit, limit)
        
        plt.text(limit-2, limit-2, "CONTENDERS\n(Good Home & Away)", ha='right', va='top', fontweight='bold', color='green', alpha=0.5)
        plt.text(-limit+2, limit-2, "ROAD WARRIORS\n(Good Away, Bad Home)", ha='left', va='top', fontweight='bold', color='orange', alpha=0.5)
        plt.text(limit-2, -limit+2, "HOME HEROES\n(Good Home, Bad Away)", ha='right', va='bottom', fontweight='bold', color='blue', alpha=0.5)
        plt.text(-limit+2, -limit+2, "LOTTERY\n(Bad Home & Away)", ha='left', va='bottom', fontweight='bold', color='red', alpha=0.5)

        plt.title(f"THE FORTRESS: Home vs. Away Net Rating ({season})", fontsize=20, weight='bold')
        plt.xlabel("Average Home Margin", fontsize=14)
        plt.ylabel("Average Away Margin", fontsize=14)
        plt.grid(True, linestyle='--', alpha=0.3)
        plt.tight_layout()
        
        filename = f"the_fortress_{season}.png"
        plt.savefig(filename, dpi=300)
        print(f"Generated {filename}")
        plt.close()

if __name__ == "__main__":
    gauntlet = TheGauntlet()
    for season in SEASONS:
        gauntlet.generate_heatmap(season)
