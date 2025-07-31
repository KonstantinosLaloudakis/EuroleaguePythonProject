from collections import Counter
from itertools import combinations

from euroleague_api import player_stats, play_by_play_data, shot_data, boxscore_data, game_stats
import pandas as pd
import random
import json
import matplotlib.pyplot as plt
import seaborn as sns


# Function to extract total points for each team in a game
def calculate_team_outcomes(data_df):
    # Filter rows with 'Total' in the Player column
    team_totals = data_df[data_df['Player'] == 'Total'][['Season', 'Gamecode', 'Team', 'Points']]
    # Rename columns for clarity
    team_totals = team_totals.rename(columns={"Points": "TeamPoints"})
    # Merge team totals with themselves to find opponents in the same game
    outcomes = pd.merge(
        team_totals,
        team_totals,
        on=['Season', 'Gamecode'],
        suffixes=('_Team', '_Opponent')
    )
    # Remove rows where Team and Opponent are the same
    outcomes = outcomes[outcomes['Team_Team'] != outcomes['Team_Opponent']]
    # Determine game outcome
    outcomes['GameOutcome'] = outcomes['TeamPoints_Team'] > outcomes['TeamPoints_Opponent']
    outcomes['GameOutcome'] = outcomes['GameOutcome'].map({True: 'Win', False: 'Loss'})
    return outcomes[['Season', 'Gamecode', 'Team_Team', 'GameOutcome']].rename(columns={'Team_Team': 'Team'})

def find_teams_with_low_scoring_wins(valid_data, team_outcomes):
    # Merge team outcomes with player data
    data_with_outcomes = pd.merge(
        valid_data,
        team_outcomes,
        on=['Season', 'Gamecode', 'Team'],
        how='left'
    )

    # Filter for winning teams
    winning_data = data_with_outcomes[data_with_outcomes['GameOutcome'] == 'Win']

    # Identify games where no player scored more than 10 points
    game_scores = winning_data.groupby(['Season', 'Gamecode', 'Team']).apply(
        lambda group: (group['Points'] <= 10).all()
    ).reset_index(name='NoPlayerOver10')

    # Filter for games where the condition is true
    valid_games = game_scores[game_scores['NoPlayerOver10']]

    # Count the number of such wins per team
    team_counts = valid_games.groupby('Team').size().reset_index(name='WinCount')

    # Sort by the number of wins and get the top 20 teams
    top_teams = team_counts.sort_values(by='WinCount', ascending=False).head(20)

    return top_teams

def find_teams_with_low_scoring_wins15(valid_data, team_outcomes):
    # Merge team outcomes with player data
    data_with_outcomes = pd.merge(
        valid_data,
        team_outcomes,
        on=['Season', 'Gamecode', 'Team'],
        how='left'
    )

    # Filter for winning teams
    winning_data = data_with_outcomes[data_with_outcomes['GameOutcome'] == 'Win']

    # Identify games where no player scored more than 10 points
    game_scores = winning_data.groupby(['Season', 'Gamecode', 'Team']).apply(
        lambda group: (group['Points'] <= 15).all()
    ).reset_index(name='NoPlayerOver10')

    # Filter for games where the condition is true
    valid_games = game_scores[game_scores['NoPlayerOver10']]

    # Count the number of such wins per team
    team_counts = valid_games.groupby('Team').size().reset_index(name='WinCount')

    # Sort by the number of wins and get the top 20 teams
    top_teams = team_counts.sort_values(by='WinCount', ascending=False).head(20)

    return top_teams

def calculate_additional_criteria(valid_data, team_outcomes):
    # Merge team outcomes with player data
    data_with_outcomes = pd.merge(
        valid_data,
        team_outcomes,
        on=['Season', 'Gamecode', 'Team'],
        how='left'
    )

    # Define additional queries
    additional_queries = {
        "Most Points While Making Every Shot He Took": valid_data[
            (valid_data['FieldGoalsMade2'] == valid_data['FieldGoalsAttempted2']) &
            (valid_data['FieldGoalsMade3'] == valid_data['FieldGoalsAttempted3']) &
            (valid_data['FreeThrowsMade'] == valid_data['FreeThrowsAttempted'])
        ].sort_values(by='Points', ascending=False),

        "Most Made Free Throws Without Missing One": valid_data[
            valid_data['FreeThrowsMade'] == valid_data['FreeThrowsAttempted']
        ].sort_values(by='FreeThrowsMade', ascending=False),

        "Most Made 2-Point Shots Without Missing One": valid_data[
            valid_data['FieldGoalsMade2'] == valid_data['FieldGoalsAttempted2']
        ].sort_values(by='FieldGoalsMade2', ascending=False),

        "Most Made 3-Point Shots Without Missing One": valid_data[
            valid_data['FieldGoalsMade3'] == valid_data['FieldGoalsAttempted3']
        ].sort_values(by='FieldGoalsMade3', ascending=False),

        "Most Points in a Loss": data_with_outcomes[
            data_with_outcomes['GameOutcome'] == 'Loss'
        ].sort_values(by='Points', ascending=False)
    }
    # Process results for additional queries
    additional_results = {}
    for key, filtered_data in additional_queries.items():
        column = None
        if key == "Most Points While Making Every Shot He Took":
            column = "Points"
        elif key == "Most Made Free Throws Without Missing One":
            column = "FreeThrowsMade"
        elif key == "Most Made 2-Point Shots Without Missing One":
            column = "FieldGoalsMade2"
        elif key == "Most Made 3-Point Shots Without Missing One":
            column = "FieldGoalsMade3"
        elif key == "Most Points in a Loss":
            column = "Points"
        else:
            raise ValueError(f"Unknown query key: {key}")

        top_20 = []
        for _, row in filtered_data.head(20).iterrows():
            game_data = game_data_instance.get_game_data(row['Season'], row['Gamecode'], 'report')
            game_data_df = pd.DataFrame(game_data)
            local_team = game_data_df.iloc[0]['local.club.name']
            away_team = game_data_df.iloc[0]['road.club.name']

            top_20.append({
                "Player": row['Player'],
                "Season": row['Season'],
                "Phase": row['Phase'],
                "Round": row['Round'],
                key.split()[1]: row[column],
                "LocalTeam": local_team,
                "AwayTeam": away_team
            })

        additional_results[key] = top_20

    # Write additional results to JSON
    additional_output_file = "additional_criteria_top_20.json"
    with open(additional_output_file, "w", encoding="utf-8") as json_file:
        json.dump(additional_results, json_file, indent=4, ensure_ascii=False)

    print(f"Additional results saved to {additional_output_file}.")

def calculate_seasonal_criteria(valid_data):
    # Define additional seasonal queries
    seasonal_queries = {
        "5+ Turnover Games in a Season": valid_data[valid_data['Turnovers'] >= 5],
        "10+ Point and 10+ Rebound Games in a Season": valid_data[
            (valid_data['Points'] >= 10) & (valid_data['TotalRebounds'] >= 10)
        ],
        "10+ Point and 10+ Assist Games in a Season": valid_data[
            (valid_data['Points'] >= 10) & (valid_data['Assistances'] >= 10)
        ],
        "5+ Offensive Rebound Games in a Season": valid_data[valid_data['OffensiveRebounds'] >= 5]
    }

    # Process results for seasonal queries
    seasonal_results = {}
    for key, filtered_data in seasonal_queries.items():
        # Group by season and player to count occurrences
        grouped_data = (
            filtered_data.groupby(['Season', 'Player'])
            .size()
            .reset_index(name='GameCount')
            .sort_values(by='GameCount', ascending=False)
        )

        top_20 = []
        for _, row in grouped_data.head(20).iterrows():
            top_20.append({
                "Player": row['Player'],
                "Season": row['Season'],
                "GameCount": row['GameCount']
            })

        seasonal_results[key] = top_20

    # Write seasonal results to JSON
    seasonal_output_file = "seasonal_criteria_top_20.json"
    with open(seasonal_output_file, "w", encoding="utf-8") as json_file:
        json.dump(seasonal_results, json_file, indent=4, ensure_ascii=False)

    print(f"Seasonal results saved to {seasonal_output_file}.")


def calculate_additional_criteria(valid_data, game_data_instance, data_df):
    # 1. Most Turnovers in a Game
    most_turnovers_game = valid_data.sort_values(by='Turnovers', ascending=False).head(1)
    most_turnovers_result = {
        "Player": most_turnovers_game.iloc[0]['Player'],
        "Season": most_turnovers_game.iloc[0]['Season'],
        "Gamecode": most_turnovers_game.iloc[0]['Gamecode'],
        "Turnovers": most_turnovers_game.iloc[0]['Turnovers']
    }

    # 2. Most Games with More Offensive Rebounds than Defensive Rebounds
    more_offensive_rebounds = valid_data[valid_data['OffensiveRebounds'] > valid_data['DefensiveRebounds']]
    offensive_rebound_count = (
        more_offensive_rebounds.groupby('Player')
        .size()
        .reset_index(name='GameCount')
        .sort_values(by='GameCount', ascending=False)
    )

    most_offensive_rebound_games = [
        {"Player": row['Player'], "GameCount": row['GameCount']}
        for _, row in offensive_rebound_count.head(20).iterrows()
    ]

    # 3. Teams with the Most Double-Digit Points Players in a Win
    # Filter rows for games (Player column contains 'Total')
    # team_double_digit_results = []
    # for (season, gamecode), game_group in data_df.groupby(['Season', 'Gamecode']):
    #     game_data = game_data_instance.get_game_data(season, gamecode, 'report')
    #     game_df = pd.DataFrame(game_data)
    #
    #     # Determine winning team
    #     local_team_points = game_df.iloc[0]['local.score']
    #     away_team_points = game_df.iloc[0]['road.score']
    #     if local_team_points > away_team_points:
    #         winning_team = game_df.iloc[0]['local.club.name']
    #     else:
    #         winning_team = game_df.iloc[0]['road.club.name']
    #
    #     # Filter players from the winning team who scored 10+ points
    #     game_players = valid_data[
    #         (valid_data['Season'] == season) & (valid_data['Gamecode'] == gamecode)
    #         ]
    #     double_digit_players = game_players[
    #         (game_players['Team'] == winning_team) & (game_players['Points'] >= 10)
    #         ]
    #
    #     team_double_digit_results.append({
    #         "Season": season,
    #         "Gamecode": gamecode,
    #         "WinningTeam": winning_team,
    #         "DoubleDigitPlayers": double_digit_players.shape[0],
    #         "GameDetails": f"{winning_team} vs {game_df.iloc[0]['road.club.name' if winning_team == game_df.iloc[0]['local.club.name'] else 'local.club.name']}"
    #     })
    #
    # # Find the game with the most double-digit points players
    # most_double_digit_game = max(team_double_digit_results, key=lambda x: x['DoubleDigitPlayers'])

    # Combine results
    additional_results = {
        "Most Turnovers in a Game": most_turnovers_result,
        "Most Games with More Offensive Rebounds than Defensive Rebounds": most_offensive_rebound_games
        # "Teams with Most Double-Digit Points Players in a Win": most_double_digit_game
    }

    # Write to JSON
    output_file = "additional_criteria_results.json"
    with open(output_file, "w", encoding="utf-8") as json_file:
        json.dump(additional_results, json_file, indent=4, ensure_ascii=False)

    print(f"Additional criteria results saved to {output_file}.")

def find_teams_with_most_double_digit_scorers(valid_data, team_outcomes):
    # Merge team outcomes with player data
    data_with_outcomes = pd.merge(
        valid_data,
        team_outcomes,
        on=['Season', 'Gamecode', 'Team'],
        how='left'
    )

    # Filter for winning teams
    winning_data = data_with_outcomes[data_with_outcomes['GameOutcome'] == 'Win']

    # Identify players with double-digit points
    double_digit_scorers = winning_data[winning_data['Points'] >= 10]

    # Count the number of double-digit scorers for each team in each game
    game_scorer_counts = double_digit_scorers.groupby(['Season', 'Gamecode', 'Team']).size().reset_index(name='DoubleDigitCount')

    # Find the game with the most double-digit scorers for each team
    team_max_scorers = game_scorer_counts.sort_values(by='DoubleDigitCount', ascending=False)

    # Add information about the game with the most double-digit scorers
    game_details = []
    for _, row in team_max_scorers.iterrows():
        game_data = game_stats.GameStats().get_game_data(row['Season'], row['Gamecode'], 'report')
        game_data_df = pd.DataFrame(game_data)
        local_team = game_data_df.iloc[0]['local.club.name']
        away_team = game_data_df.iloc[0]['road.club.name']

        game_details.append({
            "Season": row['Season'],
            "Phase": game_data_df.iloc[0]['phaseType.alias'],
            "Round": game_data_df.iloc[0]['roundAlias'],
            "Team": row['Team'],
            "DoubleDigitCount": row['DoubleDigitCount'],
            "LocalTeam": local_team,
            "AwayTeam": away_team
        })

    return game_details


def find_double_digit_scorer_stats(valid_data, team_outcomes):
    # Merge team outcomes with player data
    data_with_outcomes = pd.merge(
        valid_data,
        team_outcomes,
        on=['Season', 'Gamecode', 'Team'],
        how='left'
    )

    # Identify players with double-digit points
    double_digit_scorers = data_with_outcomes[data_with_outcomes['Points'] >= 10]

    # Count the number of double-digit scorers for each team in each game
    game_scorer_counts = double_digit_scorers.groupby(['Season', 'Gamecode', 'Team', 'GameOutcome']).size().reset_index(
        name='DoubleDigitCount')

    # Sort for each category
    categories = {
        "MostDoubleDigitInWins": game_scorer_counts[game_scorer_counts['GameOutcome'] == 'Win'].sort_values(
            by='DoubleDigitCount', ascending=False),
        "LeastDoubleDigitInWins": game_scorer_counts[game_scorer_counts['GameOutcome'] == 'Win'].sort_values(
            by='DoubleDigitCount', ascending=True),
        "MostDoubleDigitInLosses": game_scorer_counts[game_scorer_counts['GameOutcome'] == 'Loss'].sort_values(
            by='DoubleDigitCount', ascending=False),
        "LeastDoubleDigitInLosses": game_scorer_counts[game_scorer_counts['GameOutcome'] == 'Loss'].sort_values(
            by='DoubleDigitCount', ascending=True)
    }

    # Collect game details for each category
    results = {}
    for category, data in categories.items():
        game_details = []
        for _, row in data.iterrows():
            game_data = game_stats.GameStats().get_game_data(row['Season'], row['Gamecode'], 'report')
            game_data_df = pd.DataFrame(game_data)
            local_team = game_data_df.iloc[0]['local.club.name']
            away_team = game_data_df.iloc[0]['road.club.name']

            game_details.append({
                "Season": row['Season'],
                "Phase": game_data_df.iloc[0]['phaseType.alias'],
                "Round": game_data_df.iloc[0]['roundAlias'],
                "Team": row['Team'],
                "DoubleDigitCount": row['DoubleDigitCount'],
                "GameOutcome": row['GameOutcome'],
                "LocalTeam": local_team,
                "AwayTeam": away_team
            })

        results[category] = game_details

    return results

def find_most_minutes_with_zero_points(valid_data):
    # Filter for players who scored 0 points
    zero_point_players = valid_data[valid_data['Points'] == 0]

    zero_point_playerswithoutdnp = zero_point_players[~zero_point_players['Minutes'].str.contains('DNP', na=False)]
    # Sort by minutes played in descending order
    zero_point_players = zero_point_playerswithoutdnp.sort_values(by='Minutes', ascending=False)

    # Extract top results
    top_zero_point_games = []
    for _, row in zero_point_players.head(100).iterrows():
        game_data = game_stats.GameStats().get_game_data(row['Season'], row['Gamecode'], 'report')
        game_data_df = pd.DataFrame(game_data)

        local_team = game_data_df.iloc[0]['local.club.name']
        away_team = game_data_df.iloc[0]['road.club.name']

        top_zero_point_games.append({
            "Season": row['Season'],
            "Player": row['Player'],
            "Phase": game_data_df.iloc[0]['phaseType.alias'],
            "Round": game_data_df.iloc[0]['roundAlias'],
            "MinutesPlayed": row['Minutes'],
            "Team": row['Team'],
            "Gamecode": row['Gamecode'],
            "LocalTeam": local_team,
            "AwayTeam": away_team
        })

    return top_zero_point_games


def convert_minutes_to_float(minutes_str):
    if pd.isna(minutes_str) or minutes_str == "DNP":
        return 0  # Convert DNP to 0 minutes
    try:
        minutes, seconds = map(int, minutes_str.split(':'))
        return minutes + seconds / 60
    except ValueError:
        return 0  # If conversion fails, treat it as 0 minutes


def find_most_points_with_dnp_or_low_minutes(valid_data):
    # Create a new column with float minutes
    valid_data['MinutesFloat'] = valid_data['Minutes'].apply(convert_minutes_to_float)

    # Split into two groups
    dnp_players = valid_data[(valid_data['MinutesFloat'] == 0) & (valid_data['Points'] > 0)]  # DNP (0 minutes) but has points
    low_minutes_players = valid_data[(valid_data['MinutesFloat'] < 5) & (valid_data['MinutesFloat'] > 0) & (valid_data['Points'] > 0)]  # >0 and <2 minutes
    low_minutes_players10 = valid_data[(valid_data['MinutesFloat'] < 10) & (valid_data['MinutesFloat'] > 0) & (valid_data['Points'] > 0)]  # >0 and <2 minutes

    # Sort by points scored in descending order
    dnp_players = dnp_players.sort_values(by='Points', ascending=False)
    low_minutes_players = low_minutes_players.sort_values(by='Points', ascending=False)
    low_minutes_players10 = low_minutes_players10.sort_values(by='Points', ascending=False)

    # Extract details for each category
    def extract_game_details(players_df, category_label):
        game_list = []
        for _, row in players_df.head(100).iterrows():
            game_data = game_stats.GameStats().get_game_data(row['Season'], row['Gamecode'], 'report')
            game_data_df = pd.DataFrame(game_data)

            local_team = game_data_df.iloc[0]['local.club.name']
            away_team = game_data_df.iloc[0]['road.club.name']

            game_list.append({
                "Category": category_label,
                "Season": row['Season'],
                "Player": row['Player'],
                "Phase": game_data_df.iloc[0]['phaseType.alias'],
                "Round": game_data_df.iloc[0]['roundAlias'],
                "MinutesPlayed": row['Minutes'],  # Use original string format
                "Points": row['Points'],
                "Team": row['Team'],
                "Gamecode": row['Gamecode'],
                "LocalTeam": local_team,
                "AwayTeam": away_team
            })
        return game_list

    # Get the top games for both cases
    dnp_games = extract_game_details(dnp_players, "DNP (0 Minutes)")
    low_minutes_games = extract_game_details(low_minutes_players, "<5 Minutes")
    low_minutes_games10 = extract_game_details(low_minutes_players10, "<10 Minutes")

    return {
        "Most Points with DNP (0 Minutes)": dnp_games,
        "Most Points with Less Than 5 Minutes": low_minutes_games,
        "Most Points with Less Than 10 Minutes": low_minutes_games10
    }

def format_name(name):
    print(name)
    if ', ' in name:
        last_name, first_name = name.split(', ')
        return f"{first_name.capitalize()} {last_name.capitalize()}"
    else:
        print(f"Skipping name: {name}")  # Log skipped names for debugging
        return None



# game_data_instance = game_stats.GameStats()
# box_score_data_instance = boxscore_data.BoxScoreData()
# data = box_score_data_instance.get_player_boxscore_stats_multiple_seasons(2007, 2023)
#
# data_df = pd.DataFrame(data)
#
# valid_data = data_df[~data_df['Player'].str.contains('Team|Total', na=False)]
#
#
# # Convert relevant columns to numeric
# numeric_columns = [
#     'Points', 'FreeThrowsMade', 'FreeThrowsAttempted',
#     'FieldGoalsMade2', 'FieldGoalsAttempted2', 'FieldGoalsMade3', 'FieldGoalsAttempted3'
# ]
# for col in numeric_columns:
#     valid_data[col] = pd.to_numeric(valid_data[col], errors='coerce')
#
# # Convert 'Minutes' separately
# valid_data['Minutes'] = valid_data['Minutes'].apply(convert_minutes_to_float)
#
# # Format player names
# valid_data['Player'] = valid_data['Player'].apply(format_name)
# valid_data = valid_data.dropna(subset=['Player'])
#
# # Define new queries
# new_queries = {
#     "Most Points with Only Free Throws": valid_data[
#         (valid_data['FreeThrowsMade'] > 0) &
#         (valid_data['FieldGoalsMade2'] == 0) &
#         (valid_data['FieldGoalsMade3'] == 0)
#     ].sort_values(by='Points', ascending=False),
#
#     "Most Points with Only 2P Shots": valid_data[
#         (valid_data['FieldGoalsMade2'] > 0) &
#         (valid_data['FreeThrowsMade'] == 0) &
#         (valid_data['FieldGoalsMade3'] == 0)
#     ].sort_values(by='Points', ascending=False),
#
#     "Most Points with Only 3P Shots": valid_data[
#         (valid_data['FieldGoalsMade3'] > 0) &
#         (valid_data['FreeThrowsMade'] == 0) &
#         (valid_data['FieldGoalsMade2'] == 0)
#     ].sort_values(by='Points', ascending=False),
# }
#
# # Process results
# results = {}
# for key, filtered_data in new_queries.items():
#     top_20 = []
#     for _, row in filtered_data.head(20).iterrows():
#         game_data = game_data_instance.get_game_data(row['Season'], row['Gamecode'], 'report')
#         game_data_df = pd.DataFrame(game_data)
#         local_team = game_data_df.iloc[0]['local.club.name']
#         away_team = game_data_df.iloc[0]['road.club.name']
#
#         top_20.append({
#             "Player": row['Player'],
#             "Season": row['Season'],
#             "Phase": row['Phase'],
#             "Round": row['Round'],
#             "Points": row['Points'],
#             "LocalTeam": local_team,
#             "AwayTeam": away_team
#         })
#
#     results[key] = top_20
#
# # Write results to JSON file
# output_file = "top_20_special_scoring_games.json"
# with open(output_file, "w", encoding="utf-8") as json_file:
#     json.dump(results, json_file, indent=4, ensure_ascii=False)
#
# print(f"Results saved to {output_file}.")

# Load data
# Load data
game_data_instance = game_stats.GameStats()
box_score_data_instance = boxscore_data.BoxScoreData()
data = box_score_data_instance.get_player_boxscore_stats_multiple_seasons(2024, 2024)
df = pd.DataFrame(data)

# Clean and convert relevant columns
df = df[~df['Player'].str.contains('Team|Total', na=False)]  # Remove team totals
df[['Points']] = df[['Points']].apply(pd.to_numeric, errors='coerce')

# Identify games where at least 3 players from the same team scored 20+ points
high_scorers = df[df['Points'] >= 20].groupby(['Season', 'Gamecode', 'Team'])['Player'].count().reset_index()
games_with_3_scorers = high_scorers[high_scorers['Player'] >= 3]

# Merge to keep only players who scored 20+ in those games
filtered_df = df.merge(games_with_3_scorers, on=['Season', 'Gamecode', 'Team'])
filtered_df = filtered_df[filtered_df['Points'] >= 20]

# Group by game to get player trios
trio_counts = {}

for (season, gamecode, team), group in filtered_df.groupby(['Season', 'Gamecode', 'Team']):
    players = sorted(group['Player_x'].tolist())  # Sort names to avoid duplicate trios
    trios = list(combinations(players, 3))  # Get all trios

    for trio in trios:
        key = (season, team, trio)
        trio_counts[key] = trio_counts.get(key, 0) + 1

# Convert to DataFrame
trio_df = pd.DataFrame([(season, team, trio, count) for (season, team, trio), count in trio_counts.items()],
                        columns=['Season', 'Team', 'Trio', 'Games'])

# Sort by most frequent trios
trio_df = trio_df.sort_values(by='Games', ascending=False)

# Save results
trio_df.to_json("most_frequent_20plus_trios2024.json", indent=4, orient="records")
print("Results saved!")
# team_outcomes = calculate_team_outcomes(data_df)



# output_file = "most_points_with_dnp_or_low_minutes.json"
# with open(output_file, "w", encoding="utf-8") as json_file:
#     json.dump(find_most_points_with_dnp_or_low_minutes(valid_data), json_file, indent=4, ensure_ascii=False)

# output_file = "most_minutes_with_zero_points.json"
# with open(output_file, "w", encoding="utf-8") as json_file:
#     json.dump(find_most_minutes_with_zero_points(valid_data), json_file, indent=4, ensure_ascii=False)


# output_file = "double_digit_scorer_stats.json"
# with open(output_file, "w", encoding="utf-8") as json_file:
#     json.dump(find_double_digit_scorer_stats(valid_data, team_outcomes), json_file, indent=4, ensure_ascii=False)

# output_file = "most_double_digit_scorers_in_wins.json"
# with open(output_file, "w", encoding="utf-8") as json_file:
#     json.dump(find_teams_with_most_double_digit_scorers(valid_data, team_outcomes), json_file, indent=4, ensure_ascii=False)

# calculate_additional_criteria(valid_data, game_data_instance, data_df)
# calculate_seasonal_criteria(valid_data)
# calculate_additional_criteria(valid_data, team_outcomes)
# Calculate team outcomes
# team_outcomes = calculate_team_outcomes(data_df)
#
# # Merge game outcomes back to player data
# valid_data_with_outcomes = pd.merge(
#     valid_data,
#     team_outcomes,
#     on=['Season', 'Gamecode', 'Team'],
#     how='left'
# )
#
# # Filter for games where players scored 20+ points
# twenty_plus_points = valid_data_with_outcomes[valid_data_with_outcomes['Points'] >= 20]
#
# # Group and count games by Player and GameOutcome
# game_counts = twenty_plus_points.groupby(['Player', 'GameOutcome']).size().reset_index(name='GameCount')
#
# # Separate counts for Wins and Losses
# wins = game_counts[game_counts['GameOutcome'] == 'Win'].sort_values(by='GameCount', ascending=False).head(20)
# losses = game_counts[game_counts['GameOutcome'] == 'Loss'].sort_values(by='GameCount', ascending=False).head(20)
#
# # Prepare results for JSON output
# results = {
#     "Most 20+ Point Games in Wins": wins.to_dict(orient='records'),
#     "Most 20+ Point Games in Losses": losses.to_dict(orient='records')
# }
#
# # Write results to JSON file
# output_file = "20_plus_point_games.json"
# with open(output_file, "w", encoding="utf-8") as json_file:
#     json.dump(results, json_file, indent=4, ensure_ascii=False)
#
# print(f"Results saved to {output_file}.")
#
#
# # Find the teams
# low_scoring_wins = find_teams_with_low_scoring_wins(valid_data, team_outcomes)
# low_scoring_wins15 = find_teams_with_low_scoring_wins15(valid_data, team_outcomes)
# # Prepare results for JSON output
# results = {
#     "Teams with Most Wins (No Player > 10 Points)": low_scoring_wins.to_dict(orient='records'),
#     "Teams with Most Wins (No Player > 15 Points)": low_scoring_wins15.to_dict(orient='records')
# }
#
# # Write results to JSON file
# output_file = "low_scoring_wins.json"
# with open(output_file, "w", encoding="utf-8") as json_file:
#     json.dump(results, json_file, indent=4, ensure_ascii=False)
#
# print(f"Results saved to {output_file}.")

# def format_name(name):
#     print(name)
#     if ', ' in name:
#         last_name, first_name = name.split(', ')
#         return f"{first_name.capitalize()} {last_name.capitalize()}"
#     else:
#         print(f"Skipping name: {name}")  # Log skipped names for debugging
#         return None
#
# # Function to convert 'MM:SS' to total minutes as a float
# def convert_minutes_to_float(minutes_str):
#     if pd.isna(minutes_str):
#         return 0
#     try:
#         minutes, seconds = map(int, minutes_str.split(':'))
#         return minutes + seconds / 60
#     except ValueError:
#         return 0
#
# game_data_instance = game_stats.GameStats()
# box_score_data_instance = boxscore_data.BoxScoreData()
# data = box_score_data_instance.get_player_boxscore_stats_multiple_seasons(2007, 2023)
#
# data_df = pd.DataFrame(data)
#
# # Remove unwanted rows with 'Team' or 'Total' in the 'Player' column
# valid_data = data_df[~data_df['Player'].str.contains('Team|Total', na=False)]
#
# # Convert relevant columns to numeric
# numeric_columns = [
#     'Points', 'Assistances', 'TotalRebounds', 'Turnovers', 'FreeThrowsMade',
#     'FreeThrowsAttempted', 'FieldGoalsMade2', 'FieldGoalsAttempted2', 'FieldGoalsMade3', 'FieldGoalsAttempted3'
# ]
# for col in numeric_columns:
#     valid_data[col] = pd.to_numeric(valid_data[col], errors='coerce')
#
# # Convert 'Minutes' separately
# valid_data['Minutes'] = valid_data['Minutes'].apply(convert_minutes_to_float)
#
# # Format player names
# valid_data['Player'] = valid_data['Player'].apply(format_name)
# valid_data = valid_data.dropna(subset=['Player'])
#
# # Define additional queries
# extra_queries = {
#     "Most Rebounds without Scoring a Point": valid_data[valid_data['Points'] == 0].sort_values(by='TotalRebounds', ascending=False),
#     "Most Missed Free Throws without Making One": valid_data[valid_data['FreeThrowsMade'] == 0].sort_values(by='FreeThrowsAttempted', ascending=False),
#     "Most Missed 2P Shots without Making One": valid_data[valid_data['FieldGoalsMade2'] == 0].sort_values(by='FieldGoalsAttempted2', ascending=False),
#     "Most Missed 3P Shots without Making One": valid_data[valid_data['FieldGoalsMade3'] == 0].sort_values(by='FieldGoalsAttempted3', ascending=False),
#     "Most Points without a Turnover": valid_data[valid_data['Turnovers'] == 0].sort_values(by='Points', ascending=False),
#     "Most Assists without a Turnover": valid_data[valid_data['Turnovers'] == 0].sort_values(by='Assistances', ascending=False),
#     "Most Points without a Free Throw Made": valid_data[valid_data['FreeThrowsMade'] == 0].sort_values(by='Points', ascending=False),
#     "Most Points without a 2P Shot Made": valid_data[valid_data['FieldGoalsMade2'] == 0].sort_values(by='Points', ascending=False),
#     "Most Points without a 3P Shot Made": valid_data[valid_data['FieldGoalsMade3'] == 0].sort_values(by='Points', ascending=False)
# }
#
# # Process results for extra queries
# extra_results = {}
# for key, filtered_data in extra_queries.items():
#     if key == "Most Rebounds without Scoring a Point":
#         column = "TotalRebounds"
#     elif key == "Most Missed Free Throws without Making One":
#         column = "FreeThrowsAttempted"
#     elif key == "Most Missed 2P Shots without Making One":
#         column = "FieldGoalsAttempted2"
#     elif key == "Most Missed 3P Shots without Making One":
#         column = "FieldGoalsAttempted3"
#     elif key == "Most Points without a Turnover":
#         column = "Points"
#     elif key == "Most Assists without a Turnover":
#         column = "Assistances"
#     elif key == "Most Points without a Free Throw Made":
#         column = "Points"
#     elif key == "Most Points without a 2P Shot Made":
#         column = "Points"
#     elif key == "Most Points without a 3P Shot Made":
#         column = "Points"
#     else:
#         raise ValueError(f"Unknown query key: {key}")
#
#     top_20 = []
#     for _, row in filtered_data.head(20).iterrows():
#         game_data = game_data_instance.get_game_data(row['Season'], row['Gamecode'], 'report')
#         game_data_df = pd.DataFrame(game_data)
#         local_team = game_data_df.iloc[0]['local.club.name']
#         away_team = game_data_df.iloc[0]['road.club.name']
#
#         top_20.append({
#             "Player": row['Player'],
#             "Season": row['Season'],
#             "Phase": row['Phase'],
#             "Round": row['Round'],
#             key.split()[1]: row[column],
#             "LocalTeam": local_team,
#             "AwayTeam": away_team
#         })
#
#     extra_results[key] = top_20
#
# # Write extra results to another JSON file
# extra_output_file = "extra_top_20_stats.json"
# with open(extra_output_file, "w", encoding="utf-8") as json_file:
#     json.dump(extra_results, json_file, indent=4, ensure_ascii=False)
#
# print(f"Extra results saved to {extra_output_file}.")

# Define queries
# queries = {
#     "Most Assists with 0 Points": valid_data[valid_data['Points'] == 0].sort_values(by='Assistances', ascending=False),
#     "Most Turnovers without Scoring": valid_data[valid_data['Points'] == 0].sort_values(by='Turnovers', ascending=False),
#     "Most Offensive Rebounds without a Defensive One": valid_data[valid_data['DefensiveRebounds'] == 0].sort_values(by='OffensiveRebounds', ascending=False),
#     "Most Drawn Fouls in a Game": valid_data.sort_values(by='FoulsReceived', ascending=False),
#     "Worst PIR": valid_data.sort_values(by='Valuation', ascending=True),
#     "Most Plus-Minus": valid_data.sort_values(by='Plusminus', ascending=False),
#     "Least Plus-Minus": valid_data.sort_values(by='Plusminus', ascending=True)
# }
#
# # Process results
# results = {}
# for key, filtered_data in queries.items():
#     if key == "Most Assists with 0 Points":
#         column = "Assistances"
#     elif key == "Most Turnovers without Scoring":
#         column = "Turnovers"
#     elif key == "Most Offensive Rebounds without a Defensive One":
#         column = "OffensiveRebounds"
#     elif key == "Most Drawn Fouls in a Game":
#         column = "FoulsReceived"
#     elif key == "Worst PIR":
#         column = "Valuation"
#     elif key == "Most Plus-Minus":
#         column = "Plusminus"
#     elif key == "Least Plus-Minus":
#         column = "Plusminus"
#     else:
#         raise ValueError(f"Unknown query key: {key}")
#     top_20 = []
#     for _, row in filtered_data.head(20).iterrows():
#         game_data = game_data_instance.get_game_data(row['Season'], row['Gamecode'], 'report')
#         game_data_df = pd.DataFrame(game_data)
#         local_team = game_data_df.iloc[0]['local.club.name']
#         away_team = game_data_df.iloc[0]['road.club.name']
#
#         top_20.append({
#             "Player": row['Player'],
#             "Season": row['Season'],
#             "Phase": row['Phase'],
#             "Round": row['Round'],
#             key.split()[1]: row[column],
#             "LocalTeam": local_team,
#             "AwayTeam": away_team
#         })
#
#     results[key] = top_20
#
# # Write results to a JSON file
# output_file = "top_20_stats.json"
# with open(output_file, "w", encoding="utf-8") as json_file:
#     json.dump(results, json_file, indent=4, ensure_ascii=False)
#
# print(f"Results saved to {output_file}.")

# Step 2: Clean the data and filter for 20+ point games
# Remove unwanted rows with 'Team' or 'Total' in the 'Player' column
# valid_data = data_df[~data_df['Player'].str.contains('Team|Total', na=False)]
#
# # Convert relevant columns to numeric
# numeric_columns = ['Points', 'Assistances', 'TotalRebounds', 'Turnovers', 'OffensiveRebounds', 'BlocksFavour', 'BlocksAgainst']
# for col in numeric_columns:
#     valid_data[col] = pd.to_numeric(valid_data[col], errors='coerce')
#
# # Convert 'MinutesPlayed' to a numeric column
# valid_data['Minutes'] = valid_data['Minutes'].apply(convert_minutes_to_float)
#
# # Step 3: Define criteria
# criteria = {
#     "10+ Points and Rebounds": valid_data[(valid_data['Points'] >= 10) & (valid_data['TotalRebounds'] >= 10)],
#     "10+ Points and Assists": valid_data[(valid_data['Points'] >= 10) & (valid_data['Assistances'] >= 10)],
#     "10+ Assists and Rebounds": valid_data[(valid_data['Assistances'] >= 10) & (valid_data['TotalRebounds'] >= 10)],
#     "5+ Turnovers": valid_data[valid_data['Turnovers'] >= 5],
#     "5+ Offensive Rebounds": valid_data[valid_data['OffensiveRebounds'] >= 5],
#     "20+ Points in Under 20 Minutes": valid_data[(valid_data['Points'] >= 20) & (valid_data['Minutes'] < 20)],
#     "5+ Blocks in Favour": valid_data[valid_data['BlocksFavour'] >= 5],
#     "5+ Blocks Against": valid_data[valid_data['BlocksAgainst'] >= 5]
# }
#
# # Step 4: Process results for each criterion
# results = {}
# for key, filtered_data in criteria.items():
#     player_counts = (
#         filtered_data.groupby('Player')
#         .size()
#         .reset_index(name='TotalGames')
#         .sort_values(by='TotalGames', ascending=False)
#     )
#     results[key] = player_counts.to_dict(orient='records')
#
# # Write results to a JSON file
# output_file = "player_stats_by_criteria.json"
# with open(output_file, "w", encoding="utf-8") as json_file:
#     json.dump(results, json_file, indent=4, ensure_ascii=False)
#
# print(f"Results saved to {output_file}.")
# Step 1: Fetch all accumulated player stats
# player_stats_instance = player_stats.PlayerStats()
# stats_data = player_stats_instance.get_player_stats(
#     endpoint='traditional',
#     statistic_mode='Accumulated'
# )
#
# # Step 2: Create a DataFrame and extract unique team codes and names
# stats_df = pd.DataFrame(stats_data)
#
# if 'player.team.code' not in stats_df.columns or 'player.team.name' not in stats_df.columns:
#     raise ValueError("The DataFrame does not have required team code or name columns.")
#
# stats_df['team_codes'] = stats_df['player.team.code']
# stats_df['team_names'] = stats_df['player.team.name']
#
# # Map team codes to full names
# team_code_to_name = {}
# for codes, names in zip(stats_df['team_codes'].dropna(), stats_df['team_names'].dropna()):
#     code_list = codes.split(';')
#     name_list = names.split(';')
#     team_code_to_name.update(dict(zip(code_list, name_list)))
#
# # Get unique team codes
# unique_teams = set(team_code_to_name.keys())
#
# # Step 3: Generate all unique team pairs
# team_pairs = list(combinations(unique_teams, 2))
#
# # Step 4: Find common players for each team pair
# results = []
# for team_code_1, team_code_2 in team_pairs:
#     common_players = stats_df[
#         stats_df['team_codes'].notna() &
#         stats_df['team_codes'].str.contains(team_code_1) &
#         stats_df['team_codes'].str.contains(team_code_2)
#     ]
#
#     # Extract player names
#     raw_player_names = common_players['player.name'].tolist()
#     formatted_player_names = [
#         format_name(name) for name in raw_player_names if format_name(name) is not None
#     ]
#
#     # Save pair only if there are common players
#     if formatted_player_names:
#         results.append({
#             "team1": team_code_to_name[team_code_1],
#             "team2": team_code_to_name[team_code_2],
#             "players": formatted_player_names
#         })
#
# # Step 5: Write results to a JSON file
# output_file = "team_combos_with_full_names.json"
# with open(output_file, "w", encoding="utf-8") as json_file:
#     json.dump(results, json_file, indent=4, ensure_ascii=False)
#



# Step 2: Fetch player stats for all seasons
# stats_data_guard_assist = player_stats_instance.get_player_stats(
#     endpoint='traditional',
#     statistic_mode='Accumulated'
# )
# print(stats_data_guard_assist.head())
# print(stats_data_guard_assist.info())


# formatted_names = stats_data_guard_assist['player.name'].apply(format_name).tolist()
#
# # Step 3: Save to a JSON file
# output_file = "player_names4.json"
# with open(output_file, 'w') as f:
#     json.dump(formatted_names, f, indent=4)
#
# print(f"Player names saved to {output_file}")

# stats_data_center_assist = player_stats_instance.get_player_stats_leaders(stat_category='Assistances',top_n=2000, statistic_mode='Accumulated', position='Centers')
# stats_data_guard_block = player_stats_instance.get_player_stats_leaders(stat_category='BlocksFavour',top_n=2000, statistic_mode='Accumulated', position='Guards')
# stats_data_center_block = player_stats_instance.get_player_stats_leaders(stat_category='BlocksFavour',top_n=2000, statistic_mode='Accumulated', position='Centers')
#
# stats_data_guard_steal = player_stats_instance.get_player_stats_leaders(stat_category='Steals',top_n=2000, statistic_mode='Accumulated', position='Guards')
# stats_data_center_steal = player_stats_instance.get_player_stats_leaders(stat_category='Steals',top_n=2000, statistic_mode='Accumulated', position='Centers')
# stats_data_guard_threePointersMade = player_stats_instance.get_player_stats_leaders(stat_category='FieldGoalsMade3',top_n=2000, statistic_mode='Accumulated', position='Guards')
# stats_data_center_threePointersMade = player_stats_instance.get_player_stats_leaders(stat_category='FieldGoalsMade3',top_n=2000, statistic_mode='Accumulated', position='Centers')
# stats_data_guard_rebound = player_stats_instance.get_player_stats_leaders(stat_category='TotalRebounds',top_n=2000, statistic_mode='Accumulated', position='Guards')
# stats_data_center_rebound = player_stats_instance.get_player_stats_leaders(stat_category='TotalRebounds',top_n=2000, statistic_mode='Accumulated', position='Centers')
# stats_data_guard_turnover = player_stats_instance.get_player_stats_leaders(stat_category='Turnovers',top_n=2000, statistic_mode='Accumulated', position='Guards')
# stats_data_center_turnover = player_stats_instance.get_player_stats_leaders(stat_category='Turnovers',top_n=2000, statistic_mode='Accumulated', position='Centers')
# stats_data_guard_freeThrowPercentage = player_stats_instance.get_player_stats_leaders(stat_category='FreeThrowsPercent',top_n=2000, statistic_mode='Accumulated', position='Guards')
# stats_data_center_freeThrowPercentage = player_stats_instance.get_player_stats_leaders(stat_category='FreeThrowsPercent',top_n=2000, statistic_mode='Accumulated', position='Centers')
# stats_data_guard_doubleDouble = player_stats_instance.get_player_stats_leaders(stat_category='DoubleDoubles',top_n=2000, statistic_mode='Accumulated', position='Guards')
# stats_data_center_doubleDouble = player_stats_instance.get_player_stats_leaders(stat_category='DoubleDoubles',top_n=2000, statistic_mode='Accumulated', position='Centers')
# stats_data_guard_fieldGoalPercentage = player_stats_instance.get_player_stats_leaders(stat_category='FieldGoalsPercent',top_n=2000, statistic_mode='Accumulated', position='Guards')
# stats_data_center_fieldGoalPercentage = player_stats_instance.get_player_stats_leaders(stat_category='FieldGoalsPercent',top_n=2000, statistic_mode='Accumulated', position='Centers')
# stats_data_guard_assist = player_stats_instance.get_player_stats_leaders_range_seasons(start_season=2000, end_season=2023, stat_category='Assistances', top_n=2000, statistic_mode='Accumulated')
# stats_data_center_assist = player_stats_instance.get_player_stats_leaders_range_seasons(start_season=2000, end_season=2023, stat_category='Assistances', top_n=2000, statistic_mode='Accumulated', position='Centers')
# stats_data_guard_block = player_stats_instance.get_player_stats_leaders_range_seasons(start_season=2000, end_season=2023, stat_category='BlocksFavour', top_n=2000, statistic_mode='Accumulated', position='Guards')
# stats_data_center_block = player_stats_instance.get_player_stats_leaders_range_seasons(start_season=2000, end_season=2023, stat_category='BlocksFavour', top_n=2000, statistic_mode='Accumulated', position='Centers')

# Step 2: Load stats into a DataFrame (adjust column names based on your needs)
# stats_df_guards_assist = pd.DataFrame(stats_data_guard_assist)
# stats_df_centers_assist = pd.DataFrame(stats_data_center_assist)
# stats_df_guards_block = pd.DataFrame(stats_data_guard_block)
# stats_df_centers_block = pd.DataFrame(stats_data_center_block)
#
# stats_df_guards_steal = pd.DataFrame(stats_data_guard_steal)
# stats_df_centers_steal = pd.DataFrame(stats_data_center_steal)
# stats_df_guards_threePointersMade = pd.DataFrame(stats_data_guard_threePointersMade)
# stats_df_centers_threePointersMade = pd.DataFrame(stats_data_center_threePointersMade)
# stats_df_guards_rebound = pd.DataFrame(stats_data_guard_rebound)
# stats_df_centers_rebound = pd.DataFrame(stats_data_center_rebound)
# stats_df_guards_turnover = pd.DataFrame(stats_data_guard_turnover)
# stats_df_centers_turnover = pd.DataFrame(stats_data_center_turnover)
# stats_df_guards_freeThrowPercentage = pd.DataFrame(stats_data_guard_freeThrowPercentage)
# stats_df_centers_freeThrowPercentage = pd.DataFrame(stats_data_center_freeThrowPercentage)
# stats_df_guards_doubleDouble = pd.DataFrame(stats_data_guard_doubleDouble)
# stats_df_centers_doubleDouble = pd.DataFrame(stats_data_center_doubleDouble)
# stats_df_guards_fieldGoalPercentage = pd.DataFrame(stats_data_guard_fieldGoalPercentage)
# stats_df_centers_fieldGoalPercentage = pd.DataFrame(stats_data_center_fieldGoalPercentage)
# Set thresholds for tricky pair criteria

# game_data = play_by_play_instance.get_lineups_data(2009, 188)
# data_df_game = pd.DataFrame(game_data)

# game_data = play_by_play_instance.get_game_play_by_play_data_multiple_seasons(2007, 2023)
# data_df_game = pd.DataFrame(game_data)
#
# spanoulis_assists = data_df_game[data_df_game['PLAYTYPE'] == 'AS'][data_df_game['PLAYER'] == 'NAVARRO, JUAN CARLOS']
# diamantidis_assists = data_df_game[data_df_game['PLAYTYPE'] == 'AS'][data_df_game['PLAYER'].isin(['RODRIGUEZ, SERGIO'])]
# scoring_playtypes = ['LAYUPMD', '2FGM', 'DUNK', '3FGM', 'FTM']


# Function to find the scorer for each assist
# def find_scorer(row):
#     assist_index = row.name  # Current row's index
#
#     # Check the next row
#     if assist_index < len(data_df_game) - 1:  # Ensure there is a next row
#         next_row = data_df_game.loc[assist_index + 1]
#         if next_row['TEAM'] == row['TEAM'] and next_row['PLAYTYPE'] in scoring_playtypes:
#             return next_row['PLAYER']
#
#     # Check the previous row
#     if assist_index > 0:  # Ensure there is a previous row
#         prev_row = data_df_game.loc[assist_index - 1]
#         if prev_row['TEAM'] == row['TEAM'] and prev_row['PLAYTYPE'] in scoring_playtypes:
#             return prev_row['PLAYER']
#
#         # Check the next row
#         if assist_index < len(data_df_game) - 2:  # Ensure there is a next row
#             next_row = data_df_game.loc[assist_index + 2]
#             if next_row['TEAM'] == row['TEAM'] and next_row['PLAYTYPE'] in scoring_playtypes:
#                 return next_row['PLAYER']
#
#     if assist_index > 1:  # Ensure there is a previous row
#         prev_row = data_df_game.loc[assist_index - 2]
#         if prev_row['TEAM'] == row['TEAM'] and prev_row['PLAYTYPE'] in scoring_playtypes:
#             return prev_row['PLAYER']
#
#         # Check the next row
#         if assist_index < len(data_df_game) - 3:  # Ensure there is a next row
#             next_row = data_df_game.loc[assist_index + 3]
#             if next_row['TEAM'] == row['TEAM'] and next_row['PLAYTYPE'] in scoring_playtypes:
#                 return next_row['PLAYER']
#
#
#     if assist_index > 2:  # Ensure there is a previous row
#         prev_row = data_df_game.loc[assist_index - 3]
#         if prev_row['TEAM'] == row['TEAM'] and prev_row['PLAYTYPE'] in scoring_playtypes:
#             return prev_row['PLAYER']
#
#
#     return None  # No scorer found
#
#
# # Apply the function to find the scorer for each assist
# spanoulis_assists['SCORER'] = spanoulis_assists.apply(find_scorer, axis=1)
# diamantidis_assists['SCORER'] = diamantidis_assists.apply(find_scorer, axis=1)
#
# spanoulis_assists_count = spanoulis_assists.groupby('SCORER').size().reset_index(name='ASSIST_COUNT')
# diamantidis_assists_count = diamantidis_assists.groupby('SCORER').size().reset_index(name='ASSIST_COUNT')
#
# # Sort the scorers by assist count in descending order
# spanoulis_sorted_assists = spanoulis_assists_count.sort_values(by='ASSIST_COUNT', ascending=False)
# diamantidis_sorted_assists = diamantidis_assists_count.sort_values(by='ASSIST_COUNT', ascending=False)
#
#
# # Write data to a different document
# with pd.ExcelWriter('assist_data_3.xlsx') as writer:
#     spanoulis_assists.to_excel(writer, sheet_name='Spanoulis_Assists', index=False)
#     diamantidis_assists.to_excel(writer, sheet_name='Diamantidis_Assists', index=False)
#     spanoulis_sorted_assists.to_excel(writer, sheet_name='Spanoulis_Sorted_Assists', index=False)
#     diamantidis_sorted_assists.to_excel(writer, sheet_name='Diamantidis_Sorted_Assists', index=False)
# shot_data_stats = shot_data_instance.get_game_shot_data_single_season(2023)
# data_df_shot = pd.DataFrame(shot_data_stats)
#
# points_per_minute = data_df_shot.groupby(['MINUTE'])['POINTS'].sum().reset_index()
#
# # 3. Optionally, rename the columns for clarity
# points_per_minute.columns = ['minute', 'points_scored']
#
# top_5_minutes = points_per_minute.sort_values(by='points_scored', ascending=False).head(5)

# shot_data_stats_multiple = shot_data_instance.get_game_shot_data_multiple_seasons(2016, 2023)
# data_df_shot_multiple = pd.DataFrame(shot_data_stats_multiple)
#
# points_per_minute = data_df_shot_multiple.groupby(['Season','MINUTE'])['POINTS'].sum().reset_index()
#
# # 3. Optionally, rename the columns for clarity
# points_per_minute.columns = ['season', 'minute', 'points_scored']
#
# plt.figure(figsize=(12, 6))
# palette = sns.color_palette("viridis", n_colors=7)
#
# # Plot with the custom color palette
# sns.lineplot(data=points_per_minute, x='minute', y='points_scored', hue='season', marker="o", palette=palette)
#
# # Add labels and title
# plt.xlabel("Minute of the Game")
# plt.ylabel("Points Scored")
# plt.title("Points Scored per Minute across Seasons")
# plt.legend(title="Season", bbox_to_anchor=(1.05, 1), loc='upper left')  # Places legend outside plot
# plt.tight_layout()  # Adjust layout to fit legend if moved
#
# # Save or display the plot
# plt.savefig("points_per_minute_across_seasons.png", format='png', dpi=300)
# plt.show()
# Step 3: Define a function to find pairs with high minutes difference but similar stats
# def find_tricky_pairs():
#     pairs = []
#     for _, guard in stats_df_guards_assist.iterrows():
#         for _, center in stats_df_centers_assist.iterrows():
#
#             if center['total'] > guard['total']:
#                 pairs.append(
#                     (center['playerName'], guard['playerName'], center['total'], guard['total'], 'assists'))
#
#     for _, guard in stats_df_guards_block.iterrows():
#         for _, center in stats_df_centers_block.iterrows():
#             if guard['total'] > center['total']:
#                 pairs.append((guard['playerName'], center['playerName'], guard['total'], center['total'], 'blocks'))
#
#     return pairs
#
# def find_tricky_pairs_steals():
#     pairs = []
#     for _, guard in stats_df_guards_steal.iterrows():
#         for _, center in stats_df_centers_steal.iterrows():
#
#             if center['total'] > guard['total']:
#                 pairs.append(
#                     (center['playerName'], guard['playerName'], center['total'], guard['total'], 'steals'))
#
#     return pairs
#
# def find_tricky_pairs_threePointersMade():
#     pairs = []
#     for _, guard in stats_df_guards_threePointersMade.iterrows():
#         for _, center in stats_df_centers_threePointersMade.iterrows():
#
#             if center['total'] > guard['total']:
#                 pairs.append(
#                     (center['playerName'], guard['playerName'], center['total'], guard['total'], 'three pointers made'))
#
#     return pairs
#
# def find_tricky_pairs_freeThrowPercentage():
#     pairs = []
#     for _, guard in stats_df_guards_freeThrowPercentage.iterrows():
#         for _, center in stats_df_centers_freeThrowPercentage.iterrows():
#
#             if center['percentage'] > guard['percentage']:
#                 pairs.append(
#                     (center['playerName'], guard['playerName'], center['percentage'], guard['percentage'], 'free-throw percentage'))
#
#     return pairs
#
# def find_tricky_pairs_fieldGoalPercentage():
#     pairs = []
#     for _, guard in stats_df_guards_fieldGoalPercentage.iterrows():
#         for _, center in stats_df_centers_fieldGoalPercentage.iterrows():
#
#             if guard['percentage'] > center['percentage']:
#                 pairs.append(
#                     (guard['playerName'], center['playerName'], guard['percentage'], center['percentage'], 'field goal percentage'))
#
#     return pairs
#
# def find_tricky_pairs_turnovers():
#     pairs = []
#     for _, guard in stats_df_guards_turnover.iterrows():
#         for _, center in stats_df_centers_turnover.iterrows():
#
#             if guard['total'] < center['total']:
#                 pairs.append(
#                     (guard['playerName'], center['playerName'], guard['total'], center['total'], 'turnovers'))
#
#     return pairs
#
#
# def find_tricky_pairs_rebounds():
#     pairs = []
#     for _, guard in stats_df_guards_rebound.iterrows():
#         for _, center in stats_df_centers_rebound.iterrows():
#
#             if guard['total'] > center['total']:
#                 pairs.append(
#                     (guard['playerName'], center['playerName'], guard['total'], center['total'], 'rebounds'))
#
#     return pairs
#
# def find_tricky_pairs_doubleDoubles():
#     pairs = []
#     for _, guard in stats_df_guards_doubleDouble.iterrows():
#         for _, center in stats_df_centers_doubleDouble.iterrows():
#
#             if guard['total'] > center['total']:
#                 pairs.append(
#                     (guard['playerName'], center['playerName'], guard['total'], center['total'], 'double-doubles'))
#
#     return pairs
#
#
# def find_non_tricky_pairs():
#     pairs = []
#     for _, guard in stats_df_guards_assist.iterrows():
#         for _, center in stats_df_centers_assist.iterrows():
#
#             if 25 >= guard['total'] - center['total'] > 0:
#                 pairs.append(
#                     (guard['playerName'], center['playerName'], guard['total'], center['total'], 'assists'))
#
#     for _, guard in stats_df_guards_block.iterrows():
#         for _, center in stats_df_centers_block.iterrows():
#             if  25 >= center['total'] - guard['total'] > 0:
#                 pairs.append((center['playerName'], guard['playerName'], center['total'], guard['total'], 'blocks'))
#
#     return pairs

def format_name(name):
    parts = name.split(', ')
    if len(parts) == 2:
        first_name, last_name = parts[1], parts[0]
        return f"{first_name.capitalize()} {last_name.capitalize()}"
    return name.capitalize()  # Handles names without a comma

# Helper function to format percentage values
def format_percentage(value):
    return f"{round(value * 100, 1)}%"


# Step 6: Write pairs to JSON with the specified format
def write_pairs_to_json(pairs, filename="non_tricky_pairs.json", fewerOrMore="more"):
    data = []
    for pair in pairs:
        player1, player2, value1, value2, stat = pair
        # Check if values need to be formatted as percentages
        if isinstance(value1, float) and 0 <= value1 < 1:
            value1 = format_percentage(value1)
        else:
            value1 = int(value1)

        if isinstance(value2, float) and 0 <= value2 < 1:
            value2 = format_percentage(value2)
        else:
            value2 = int(value2)
        entry = {
            "question": f"Who has {fewerOrMore} {stat} during their Euroleague career?",
            "correctAnswer": format_name(player1),
            "wrongAnswer": format_name(player2),
            "info": f"{format_name(player1)} has {value1} {stat}, while {format_name(player2)} has {value2} {stat}."
        }
        data.append(entry)

    # Write to JSON file
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

# Step 4: Get pairs and print one example
# tricky_pairs_steals = find_tricky_pairs_steals()
# tricky_pairs_rebounds = find_tricky_pairs_rebounds()
# tricky_pairs_turnovers = find_tricky_pairs_turnovers()
# tricky_pairs_doubleDoubles = find_tricky_pairs_doubleDoubles()
# tricky_pairs_threePointersMade = find_tricky_pairs_threePointersMade()
# tricky_pairs_freeThrowPercentage = find_tricky_pairs_freeThrowPercentage()
# tricky_pairs_fieldGoalPercentage = find_tricky_pairs_fieldGoalPercentage()
# if tricky_pairs_steals:
#     # Save pairs to JSON file
#     write_pairs_to_json(tricky_pairs_steals, "tricky_pairs_steals.json")
# if tricky_pairs_threePointersMade:
#     # Save pairs to JSON file
#     write_pairs_to_json(tricky_pairs_threePointersMade, "tricky_pairs_threePointersMade.json")
# if tricky_pairs_freeThrowPercentage:
#     # Save pairs to JSON file
#     write_pairs_to_json(tricky_pairs_freeThrowPercentage, "tricky_pairs_freeThrowPercentage.json", "better")
# if tricky_pairs_fieldGoalPercentage:
#     # Save pairs to JSON file
#     write_pairs_to_json(tricky_pairs_fieldGoalPercentage, "tricky_pairs_fieldGoalPercentage.json", "better")
# if tricky_pairs_rebounds:
#     # Save pairs to JSON file
#     write_pairs_to_json(tricky_pairs_rebounds, "tricky_pairs_rebounds.json")
# if tricky_pairs_turnovers:
#     # Save pairs to JSON file
#     write_pairs_to_json(tricky_pairs_turnovers, "tricky_pairs_turnovers.json", "fewer")
# if tricky_pairs_doubleDoubles:
#     # Save pairs to JSON file
#     write_pairs_to_json(tricky_pairs_doubleDoubles, "tricky_pairs_doubleDoubles.json")






