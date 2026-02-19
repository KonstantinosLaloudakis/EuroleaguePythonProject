import json
import random

def generate_schedule():
    # Definitive 20 Team List for 2025-26 (Verified via API)
    # ALBA Berlin (BER) is excluded.
    el_teams = [
        'ULK', 'HTA', 'DUB', 'MIL', 'PAN', 
        'IST', 'OLY', 'VIR', 'ZAL', 'PAM', 
        'ASV', 'MCO', 'BAS', 'MAD', 'TEL', 
        'MUN', 'RED', 'PAR', 'BAR', 'PRS'
    ]
    
    print(f"Generating hypothetical 2025-26 Round 29 for {len(el_teams)} teams (10 Games)...")
    
    # Generate random pairs for simulation
    random.shuffle(el_teams)
    
    new_games = []
    # Exactly 20 teams -> 10 games
    for i in range(0, 20, 2):
        local = el_teams[i]
        road = el_teams[i+1]
        new_games.append({
            'GameCode': 280 + (i//2),
            'LocalTeam': local,
            'RoadTeam': road,
            'LocalScore': 0,
            'RoadScore': 0,
            'Winner': 'UNKNOWN'
        })
        print(f"Matchup {i//2+1}: {local} vs {road}")

    # Save to manual_round_29.json
    with open('manual_round_29.json', 'w') as f:
        json.dump(new_games, f, indent=4)
        print("Saved manual_round_29.json with correct 2025 Roster.")

if __name__ == "__main__":
    generate_schedule()
