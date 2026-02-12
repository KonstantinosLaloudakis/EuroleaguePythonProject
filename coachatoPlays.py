from euroleague_api.play_by_play_data import PlayByPlay
from euroleague_api.game_stats import GameStats
import pandas as pd
import time

coach_map = {
    'OLY': 'Georgios Bartzokas', 'PAN': 'Ergin Ataman', 'ULK': 'Saras Jasikevicius',
    'MAD': 'Chus Mateo', 'BAR': 'Joan Penarroya', 'MCO': 'Sasa Obradovic',
    'MIL': 'Ettore Messina', 'TEL': 'Oded Kattash', 'IST': 'Tomislav Mijatovic',
    'ZAL': 'Andrea Trinchieri', 'PAR': 'Zeljko Obradovic', 'RED': 'Ioannis Sfairopoulos',
    'PRS': 'Tiago Splitter', 'MUN': 'Gordon Herbert', 'BAS': 'Pablo Laso',
    'VIR': 'Luca Banchi', 'ASV': 'Pierric Poupet', 'BER': 'Israel Gonzalez'
}

terminal_actions = ['2FGM', '2FGA', '3FGM', '3FGA', 'FTM', 'FTA', 'TO']

pbp_client = PlayByPlay(competition='E')
game_client = GameStats(competition='E')
games = game_client.get_game_reports_single_season(season=2024)

all_ato_data = []

print("Analyzing 2024-2025 season tactical data...")

for _, game in games.iterrows():
    code = game['Gamecode']
    teams = [game['local.club.code'], game['road.club.code']]

    try:
        df = pbp_client.get_game_play_by_play_data(season=2024, gamecode=code)
        timeouts = df[(df['PLAYTYPE'] == 'TOUT') & (df['CODETEAM'].isin(teams))].index

        for idx in timeouts:
            calling_team = df.loc[idx, 'CODETEAM']
            subsequent = df.loc[idx + 1: idx + 12]

            team_outcomes = subsequent[
                (subsequent['CODETEAM'] == calling_team) & (subsequent['PLAYTYPE'].isin(terminal_actions))]

            success, pts, to, three, executed = 0, 0, 0, 0, 0
            player = "N/A"

            if not team_outcomes.empty:
                executed = 1
                outcome = team_outcomes.iloc[0]
                action = outcome['PLAYTYPE']
                player = outcome.get('PLAYER', 'Unknown')

                success = 1 if action in ['2FGM', '3FGM', 'FTM'] else 0
                to = 1 if action == 'TO' else 0
                three = 1 if action in ['3FGM', '3FGA'] else 0

                if action == '3FGM': pts = 3
                elif action == '2FGM': pts = 2
                elif action == 'FTM': pts = 1

            all_ato_data.append({
                'Coach': coach_map.get(calling_team, 'Unknown'),
                'Team': calling_team,
                'Player': player,
                'Executed_Play': executed,
                'Success': success,
                'Points': pts,
                'is_TO': to,
                'is_3PT': three
            })
        time.sleep(0.01)
    except Exception:
        continue

# --- ADVANCED AGGREGATION LOGIC ---
ato_df = pd.DataFrame(all_ato_data)

def get_target_stats(df_subset):
    valid_plays = df_subset[df_subset['Executed_Play'] == 1]
    if not valid_plays.empty:
        counts = valid_plays['Player'].value_counts()
        main_player = counts.idxmax()
        total_executed = len(valid_plays)
        share_pct = (counts.max() / total_executed)
        return pd.Series([main_player, share_pct])
    return pd.Series(["N/A", 0.0])

# 1. Base Aggregation
final_report = ato_df.groupby(['Coach', 'Team']).agg(
    True_Total_Timeouts=('Success', 'count'),
    Execution_Rate=('Executed_Play', 'mean'),
    Success_Rate_on_Execution=('Success', 'mean'),
    Avg_Points_Per_ATO=('Points', 'mean'),
    Turnover_Rate=('is_TO', 'mean'),
    Three_Point_Rate=('is_3PT', 'mean') # Bonus Stat: Strategy Indicator
).reset_index()

# 2. Add Concentration Stats
target_data = final_report.apply(
    lambda row: get_target_stats(ato_df[(ato_df['Coach'] == row['Coach']) & (ato_df['Team'] == row['Team'])]),
    axis=1
)
target_data.columns = ['Main_Target', 'Target_Share_Pct']
final_report = pd.concat([final_report, target_data], axis=1)

# Sorting and rounding to exactly 3 decimals
final_report = final_report.sort_values(by='Success_Rate_on_Execution', ascending=False)
report_rounded = final_report.round(3)

# Print results
print("\n--- 2024-2025 Coach Tactics Report (Final) ---")
print(report_rounded.to_string(index=False))

# Export files
report_rounded.to_csv('euroleague_tactics_v3.csv', index=False)

try:
    import tabulate
    with open('coach_report2.md', 'w') as f:
        f.write(report_rounded.to_markdown(index=False))
    print("\nFiles saved: euroleague_tactics_v3.csv and coach_report.md")
except ImportError:
    print("\nNote: 'tabulate' not found. Run 'pip install tabulate' to generate the .md file.")