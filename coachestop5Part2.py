import pandas as pd
import time
from euroleague_api.play_by_play_data import PlayByPlay
from euroleague_api.game_stats import GameStats

# 1. Setup & Mapping
coach_map = {
    'OLY': 'Georgios Bartzokas', 'PAN': 'Ergin Ataman', 'ULK': 'Saras Jasikevicius',
    'MAD': 'Chus Mateo', 'BAR': 'Joan Penarroya', 'MCO': 'Sasa Obradovic',
    'MIL': 'Ettore Messina', 'TEL': 'Oded Kattash', 'IST': 'Tomislav Mijatovic',
    'ZAL': 'Andrea Trinchieri', 'PAR': 'Zeljko Obradovic', 'RED': 'Ioannis Sfairopoulos',
    'PRS': 'Tiago Splitter', 'MUN': 'Gordon Herbert', 'BAS': 'Pablo Laso',
    'VIR': 'Luca Banchi', 'ASV': 'Pierric Poupet', 'BER': 'Israel Gonzalez',
    'HTA': 'Dimitrios Itoudis', 'DUB': 'Jurica Golemac', 'PAM': 'Pedro Martinez'
}

terminal_actions = ['2FGM', '2FGA', '3FGM', '3FGA', 'FTM', 'FTA', 'TO']

pbp_client = PlayByPlay(competition='E')
game_client = GameStats(competition='E')
games = game_client.get_game_reports_single_season(season=2025)

all_ato_data = []

print("Extracting 2024-2025 tactical data and player-specific targets...")

for _, game in games.iterrows():
    code = game['Gamecode']
    teams = [game['local.club.code'], game['road.club.code']]

    try:
        df = pbp_client.get_game_play_by_play_data(season=2025, gamecode=code)
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

                if action == '3FGM':
                    pts = 3
                elif action in ['2FGM', 'FTM']:
                    pts = 2  # Simplified point logic

            all_ato_data.append({
                'Coach': coach_map.get(calling_team, 'Unknown'),
                'Team': calling_team,
                'Player': player,
                'Executed_Play': executed,
                'Success': success,
                'Points': pts,
                'is_3PT': three
            })
        time.sleep(0.01)
    except Exception:
        continue

# --- AGGREGATION LOGIC ---
ato_df = pd.DataFrame(all_ato_data)


# 1. Coach-Level Report
def get_main_target_stats(df_subset):
    valid = df_subset[df_subset['Executed_Play'] == 1]
    if valid.empty: return pd.Series(["N/A", 0.0])
    counts = valid['Player'].value_counts()
    return pd.Series([counts.idxmax(), counts.max() / len(valid)])


coach_report = ato_df.groupby(['Coach', 'Team']).agg(
    Total_Timeouts=('Success', 'count'),
    Execution_Rate=('Executed_Play', 'mean'),
    Success_Rate_on_Execution=('Success', 'mean'),
    Avg_Points=('Points', 'mean')
).reset_index()

target_stats = coach_report.apply(lambda r: get_main_target_stats(ato_df[ato_df['Coach'] == r['Coach']]), axis=1)
coach_report[['Main_Target', 'Target_Share_Pct']] = target_stats
coach_report.sort_values(by='Success_Rate_on_Execution', ascending=False).round(3).to_csv('coach_tactics_final2025.csv',
                                                                                          index=False)


# 2. Player-Level Deep Dive (Top 5 for Bartzokas & Ataman)
def get_top_players(coach_name):
    coach_data = ato_df[ato_df['Coach'] == coach_name]
    total_executed = coach_data['Executed_Play'].sum()

    player_stats = coach_data[coach_data['Executed_Play'] == 1].groupby('Player').agg(
        Times_Targeted=('Executed_Play', 'count'),
        Success_Rate=('Success', 'mean'),
        Avg_Points=('Points', 'mean')
    ).reset_index()

    player_stats['Target_Share_Pct'] = player_stats['Times_Targeted'] / total_executed
    return player_stats.sort_values(by='Times_Targeted', ascending=False).head(5)


ataman_players = get_top_players('Ergin Ataman')
bartzokas_players = get_top_players('Georgios Bartzokas')

# Combine and Export Player Report
player_deep_dive = pd.concat([ataman_players.assign(Coach='Ergin Ataman'),
                              bartzokas_players.assign(Coach='Georgios Bartzokas')])
player_deep_dive.round(3).to_csv('top_targets_deep_dive2025.csv', index=False)

print("\n--- Top 5 Targets: Ergin Ataman ---")
print(ataman_players.round(3).to_string(index=False))
print("\n--- Top 5 Targets: Georgios Bartzokas ---")
print(bartzokas_players.round(3).to_string(index=False))