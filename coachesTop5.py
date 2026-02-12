import pandas as pd
import time
from euroleague_api.play_by_play_data import PlayByPlay
from euroleague_api.game_stats import GameStats

# 1. Setup & Mapping
coach_map = {'OLY': 'Georgios Bartzokas', 'PAN': 'Ergin Ataman'}  # Filtered for your request
terminal_actions = ['2FGM', '2FGA', '3FGM', '3FGA', 'FTM', 'FTA', 'TO']

pbp_client = PlayByPlay(competition='E')
game_client = GameStats(competition='E')
games = game_client.get_game_reports_single_season(season=2024)

all_ato_data = []

print("Running deep-dive on Bartzokas and Ataman tactical execution...")

for _, game in games.iterrows():
    code = game['Gamecode']
    teams = [game['local.club.code'], game['road.club.code']]

    # We only care about games involving OLY or PAN to save time
    if not any(t in coach_map.keys() for t in teams): continue

    try:
        df = pbp_client.get_game_play_by_play_data(season=2024, gamecode=code)
        # Filter for timeouts from our target teams
        timeouts = df[(df['PLAYTYPE'] == 'TOUT') & (df['CODETEAM'].isin(coach_map.keys()))].index

        for idx in timeouts:
            calling_team = df.loc[idx, 'CODETEAM']
            subsequent = df.loc[idx + 1: idx + 12]
            team_outcomes = subsequent[
                (subsequent['CODETEAM'] == calling_team) & (subsequent['PLAYTYPE'].isin(terminal_actions))]

            if not team_outcomes.empty:
                outcome = team_outcomes.iloc[0]
                action = outcome['PLAYTYPE']
                player = outcome.get('PLAYER', 'Unknown')
                success = 1 if action in ['2FGM', '3FGM', 'FTM'] else 0

                all_ato_data.append({
                    'Coach': coach_map[calling_team],
                    'Player': player,
                    'Success': success,
                    'is_Executed': 1
                })
        time.sleep(0.01)
    except Exception:
        continue

# --- PLAYER-LEVEL AGGREGATION ---
df_players = pd.DataFrame(all_ato_data)


def get_coach_top_5(coach_name, data):
    coach_data = data[data['Coach'] == coach_name]
    total_ato_executed = len(coach_data)

    player_stats = coach_data.groupby('Player').agg(
        Times_Targeted=('is_Executed', 'count'),
        Success_Rate=('Success', 'mean')
    ).reset_index()

    player_stats['Target_Share %'] = (player_stats['Times_Targeted'] / total_ato_executed) * 100
    return player_stats.sort_values(by='Times_Targeted', ascending=False).head(5)


# Generate results
ataman_top_5 = get_coach_top_5('Ergin Ataman', df_players)
bartzokas_top_5 = get_coach_top_5('Georgios Bartzokas', df_players)

print("\n--- ERGIN ATAMAN (PAN) TOP 5 ATO TARGETS ---")
print(ataman_top_5.round(3).to_string(index=False))

print("\n--- GEORGIOS BARTZOKAS (OLY) TOP 5 ATO TARGETS ---")
print(bartzokas_top_5.round(3).to_string(index=False))