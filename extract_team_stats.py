import json
import os

def extract_stats():
    # Load the big file
    try:
        with open('mvp_all_game_stats_2025.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Error: mvp_all_game_stats_2025.json not found.")
        return

    team_stats = {}

    print(f"Processing {len(data)} games...")

    for game in data:
        # Process Local Team
        local_code = game['local.coach.code'] # This is coach code, need team code.
        # Structure is game['local.players'][0]['player']['club']['code']
        
        # Helper to get team code safely
        l_team = "UNKNOWN"
        if game.get('local.players'):
            l_team = game['local.players'][0]['player']['club']['code']
            
        r_team = "UNKNOWN"
        if game.get('road.players'):
             r_team = game['road.players'][0]['player']['club']['code']
             
        if l_team not in team_stats: team_stats[l_team] = {'GP': 0, 'TRB': 0, 'ORB': 0, '3PM': 0, '3PA': 0, 'TOV': 0, 'AST': 0, 'STL': 0}
        if r_team not in team_stats: team_stats[r_team] = {'GP': 0, 'TRB': 0, 'ORB': 0, '3PM': 0, '3PA': 0, 'TOV': 0, 'AST': 0, 'STL': 0}
        
        team_stats[l_team]['GP'] += 1
        team_stats[r_team]['GP'] += 1
        
        # Sum Local Players
        for p in game.get('local.players', []):
            stats = p.get('stats', {})
            team_stats[l_team]['TRB'] += stats.get('totalRebounds', 0)
            team_stats[l_team]['ORB'] += stats.get('offensiveRebounds', 0)
            team_stats[l_team]['3PM'] += stats.get('fieldGoalsMade3', 0)
            team_stats[l_team]['3PA'] += stats.get('fieldGoalsAttempted3', 0)
            team_stats[l_team]['TOV'] += stats.get('turnovers', 0)
            team_stats[l_team]['AST'] += stats.get('assistances', 0)
            team_stats[l_team]['STL'] += stats.get('steals', 0)
            
        # Sum Road Players
        for p in game.get('road.players', []):
            stats = p.get('stats', {})
            team_stats[r_team]['TRB'] += stats.get('totalRebounds', 0)
            team_stats[r_team]['ORB'] += stats.get('offensiveRebounds', 0)
            team_stats[r_team]['3PM'] += stats.get('fieldGoalsMade3', 0)
            team_stats[r_team]['3PA'] += stats.get('fieldGoalsAttempted3', 0)
            team_stats[r_team]['TOV'] += stats.get('turnovers', 0)
            team_stats[r_team]['AST'] += stats.get('assistances', 0)
            team_stats[r_team]['STL'] += stats.get('steals', 0)

    # Calculate Averages
    final_stats = {}
    for team, totals in team_stats.items():
        gp = totals['GP']
        if gp == 0: continue
        
        final_stats[team] = {
            'TRB': round(totals['TRB'] / gp, 1),
            'ORB': round(totals['ORB'] / gp, 1),
            '3PM': round(totals['3PM'] / gp, 1),
            '3PA': round(totals['3PA'] / gp, 1),
            '3P%': round((totals['3PM'] / totals['3PA']) * 100, 1) if totals['3PA'] > 0 else 0,
            'TOV': round(totals['TOV'] / gp, 1),
            'AST': round(totals['AST'] / gp, 1),
            'STL': round(totals['STL'] / gp, 1),
            'GP': gp
        }

    # Save
    with open('team_advanced_stats.json', 'w') as f:
        json.dump(final_stats, f, indent=4)
        
    print("Saved team_advanced_stats.json")

if __name__ == "__main__":
    extract_stats()
