import json
import pandas as pd

def parse_mvp_data_2024():
    input_file = 'mvp_all_game_stats_2024.json'
    output_file = 'mvp_parsed_games_2024.json'
    standings_file = 'mvp_standings_derived_2024.json'
    
    print(f"Parsing 2024 games from {input_file}...")
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            games = json.load(f)
    except FileNotFoundError:
        print(f"File not found: {input_file}")
        return

    player_stats_list = []
    game_results = []
    
    for game in games:
        game_code = game.get('Gamecode')
        
        local_players = game.get('local.players', [])
        road_players = game.get('road.players', [])
        
        local_team_standings = "UNKNOWN"
        if local_players:
             local_team_standings = local_players[0].get('player', {}).get('club', {}).get('code', 'UNKNOWN')
             
        road_team_standings = "UNKNOWN"
        if road_players:
             road_team_standings = road_players[0].get('player', {}).get('club', {}).get('code', 'UNKNOWN')

        local_points = 0
        road_points = 0
        
        # Process Local Players
        for p_entry in local_players:
            stats = p_entry.get('stats', {})
            info = p_entry.get('player', {})
            p_code = info.get('person', {}).get('code')
            p_name = info.get('person', {}).get('name')
            # USE PLAYER CLUB CODE DIRECTLY
            t_code = info.get('club', {}).get('code', local_team_standings)
            
            pts = stats.get('points', 0)
            local_points += pts
            
            # Game Score Calculation
            fgm = stats.get('fieldGoalsMadeTotal', 0)
            fga = stats.get('fieldGoalsAttemptedTotal', 0)
            ftm = stats.get('freeThrowsMade', 0)
            fta = stats.get('freeThrowsAttempted', 0)
            orb = stats.get('offensiveRebounds', 0)
            drb = stats.get('defensiveRebounds', 0)
            stl = stats.get('steals', 0)
            ast = stats.get('assistances', 0)
            blk = stats.get('blocksFavour', 0)
            pf = stats.get('foulsCommited', 0)
            tov = stats.get('turnovers', 0)
            
            gmsc = pts + 0.4*fgm - 0.7*fga - 0.4*(fta - ftm) + 0.7*orb + 0.3*drb + stl + 0.7*ast + 0.7*blk - 0.4*pf - tov
            
            player_stats_list.append({
                'PlayerCode': p_code,
                'PlayerName': p_name,
                'TeamCode': t_code,
                'GameCode': game_code,
                'GmSc': gmsc,
                'PIR': stats.get('valuation', 0),
                'PTS': pts
            })

        # Process Road Players
        for p_entry in road_players:
            stats = p_entry.get('stats', {})
            info = p_entry.get('player', {})
            p_code = info.get('person', {}).get('code')
            p_name = info.get('person', {}).get('name')
            # USE PLAYER CLUB CODE DIRECTLY
            t_code = info.get('club', {}).get('code', road_team_standings)
            
            pts = stats.get('points', 0)
            road_points += pts
            
            fgm = stats.get('fieldGoalsMadeTotal', 0)
            fga = stats.get('fieldGoalsAttemptedTotal', 0)
            ftm = stats.get('freeThrowsMade', 0)
            fta = stats.get('freeThrowsAttempted', 0)
            orb = stats.get('offensiveRebounds', 0)
            drb = stats.get('defensiveRebounds', 0)
            stl = stats.get('steals', 0)
            ast = stats.get('assistances', 0)
            blk = stats.get('blocksFavour', 0)
            pf = stats.get('foulsCommited', 0)
            tov = stats.get('turnovers', 0)
            
            gmsc = pts + 0.4*fgm - 0.7*fga - 0.4*(fta - ftm) + 0.7*orb + 0.3*drb + stl + 0.7*ast + 0.7*blk - 0.4*pf - tov
            
            player_stats_list.append({
                'PlayerCode': p_code,
                'PlayerName': p_name,
                'TeamCode': t_code,
                'GameCode': game_code,
                'GmSc': gmsc,
                'PIR': stats.get('valuation', 0),
                'PTS': pts
            })

        if local_team_standings != "UNKNOWN" and road_team_standings != "UNKNOWN":
            game_results.append({
                'GameCode': game_code,
                'LocalTeam': local_team_standings,
                'RoadTeam': road_team_standings,
                'LocalScore': local_points,
                'RoadScore': road_points,
                'Winner': local_team_standings if local_points > road_points else road_team_standings
            })

    # Save Parsed Player Stats
    df = pd.DataFrame(player_stats_list)
    print("Parsed Data Sample:")
    print(df[['PlayerCode', 'PlayerName', 'TeamCode', 'GameCode', 'GmSc', 'PIR', 'PTS']].head())
    
    df.to_json(output_file, orient='records', indent=4)
    print(f"Saved {output_file}")
    
    # Calculate Standings
    standings = {}
    for g in game_results:
        winner = g['Winner']
        loser = g['RoadTeam'] if g['Winner'] == g['LocalTeam'] else g['LocalTeam']
        
        if winner not in standings: standings[winner] = {'W': 0, 'L': 0, 'GP': 0}
        if loser not in standings: standings[loser] = {'W': 0, 'L': 0, 'GP': 0}
        
        standings[winner]['W'] += 1
        standings[winner]['GP'] += 1
        standings[loser]['L'] += 1
        standings[loser]['GP'] += 1
        
    for team, stats in standings.items():
        if stats['GP'] > 0:
            stats['WinPct'] = stats['W'] / stats['GP']
        else:
            stats['WinPct'] = 0.0
            
    print("Game Results Sample:")
    print(pd.DataFrame(game_results).head())
            
    with open(standings_file, 'w') as f:
        json.dump(standings, f, indent=4)
    print(f"Saved {standings_file}")

if __name__ == "__main__":
    parse_mvp_data_2024()
