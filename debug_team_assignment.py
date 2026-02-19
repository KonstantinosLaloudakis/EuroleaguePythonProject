import json
import pandas as pd

def debug_de_colo():
    try:
        df = pd.read_json('mvp_parsed_games.json')
        # Filter for De Colo
        # Name might vary, search for "COLO"
        de_colo = df[df['PlayerName'].str.contains("COLO", na=False)]
        
        print("--- Nando De Colo Entries ---")
        print(de_colo[['GameCode', 'PlayerName', 'TeamCode']].sort_values('GameCode').to_string())
        
        # Check a game where he is ULK
        ulk_games = de_colo[de_colo['TeamCode'] == 'ULK']
        if not ulk_games.empty:
            bad_game = ulk_games.iloc[0]['GameCode']
            print(f"\nScanning raw JSON for Game {bad_game}...")
            
            with open('mvp_all_game_stats_2025.json', 'r') as f:
                games = json.load(f)
                
            for g in games:
                if g.get('Gamecode') == bad_game:
                    print(f"Game {bad_game} Found.")
                    # Check local/road clubs
                    l_club = g.get('local', {}).get('club', {}).get('code')
                    r_club = g.get('road', {}).get('club', {}).get('code')
                    print(f"Local Club: {l_club}")
                    print(f"Road Club: {r_club}")
                    
                    # Check first player club in local/road
                    l_players = g.get('local', {}).get('players', [])
                    if l_players:
                        first_l = l_players[0].get('player', {}).get('club', {}).get('code')
                        print(f"First Local Player Club: {first_l}")
                        
                    # Check De Colo in extracted list
                    for p in l_players:
                        if "COLO" in p.get('player', {}).get('person', {}).get('name', ''):
                            print(f"Found De Colo in LOCAL roster. His club code: {p.get('player', {}).get('club', {}).get('code')}")
                            
                    r_players = g.get('road', {}).get('players', [])
                    for p in r_players:
                        if "COLO" in p.get('player', {}).get('person', {}).get('name', ''):
                            print(f"Found De Colo in ROAD roster. His club code: {p.get('player', {}).get('club', {}).get('code')}")
                            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_de_colo()
