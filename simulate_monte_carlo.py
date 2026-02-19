import pandas as pd
import numpy as np
import xml.etree.ElementTree as ET
import json
import os

def run_monte_carlo(num_simulations=10000):
    print("--- 🏀 Euroleague Monte Carlo Playoff Matrix 🏀 ---")
    print(f"Running {num_simulations} simulations of the remaining season...")

    # 1. Load baseline data from mvp_game_results.json
    if not os.path.exists('mvp_game_results.json'):
        print("Error: mvp_game_results.json not found.")
        return

    try:
        df = pd.read_json('mvp_game_results.json')
        played = df[(df['LocalScore'] > 0) & (df['RoadScore'] > 0)].copy()
        
        # Base HCA
        hca = (played['LocalScore'] - played['RoadScore']).mean()
        
        # Calculate current standings and advanced ratings
        teams_data = {}
        for _, row in played.iterrows():
            local, road = row['LocalTeam'], row['RoadTeam']
            l_pts, r_pts = row['LocalScore'], row['RoadScore']
            
            for t in (local, road):
                if t not in teams_data:
                    # Added arrays to track Home/Away specifically and game-by-game for Form
                    teams_data[t] = {
                        'W': 0, 'L': 0, 
                        'HomePTS': 0, 'HomePA': 0, 'HomeGP': 0,
                        'AwayPTS': 0, 'AwayPA': 0, 'AwayGP': 0,
                        'GameMargins': []
                    }
            
            if l_pts > r_pts:
                teams_data[local]['W'] += 1
                teams_data[road]['L'] += 1
            else:
                teams_data[road]['W'] += 1
                teams_data[local]['L'] += 1
                
            # Home Splits
            teams_data[local]['HomePTS'] += l_pts
            teams_data[local]['HomePA'] += r_pts
            teams_data[local]['HomeGP'] += 1
            teams_data[local]['GameMargins'].append(l_pts - r_pts)
            
            # Away Splits
            teams_data[road]['AwayPTS'] += r_pts
            teams_data[road]['AwayPA'] += l_pts
            teams_data[road]['AwayGP'] += 1
            teams_data[road]['GameMargins'].append(r_pts - l_pts)
            
        print(f"Loaded {len(teams_data)} teams with {len(played)} played games.")
        
    except Exception as e:
        print(f"Error loading base data: {e}")
        return

    team_list = sorted(list(teams_data.keys()))
    num_teams = len(team_list)
    team_to_idx = {t: i for i, t in enumerate(team_list)}
    
    # Base Numpy Arrays
    base_wins = np.zeros(num_teams)
    base_pd = np.zeros(num_teams)
    home_ratings = np.zeros(num_teams)
    away_ratings = np.zeros(num_teams)
    form_ratings = np.zeros(num_teams)
    
    for t in team_list:
        idx = team_to_idx[t]
        stats = teams_data[t]
        
        base_wins[idx] = stats['W']
        # Total PD
        t_pts = stats['HomePTS'] + stats['AwayPTS']
        t_pa = stats['HomePA'] + stats['AwayPA']
        base_pd[idx] = t_pts - t_pa
        
        # True Home Rating
        home_ratings[idx] = (stats['HomePTS'] - stats['HomePA']) / stats['HomeGP'] if stats['HomeGP'] > 0 else 0
        
        # True Away Rating
        away_ratings[idx] = (stats['AwayPTS'] - stats['AwayPA']) / stats['AwayGP'] if stats['AwayGP'] > 0 else 0
        
        # Momentum (Last 5 Games Avg Margin)
        recent_games = stats['GameMargins'][-5:] if len(stats['GameMargins']) >=5 else stats['GameMargins']
        form_ratings[idx] = sum(recent_games) / len(recent_games) if recent_games else 0

    # 2. Extract Unplayed Games
    name_to_code = {
        'ALBA BERLIN': 'BER', 'ANADOLU EFES ISTANBUL': 'IST', 'AS MONACO': 'MCO',
        'BASKONIA VITORIA-GASTEIZ': 'BAS', 'KOSNER BASKONIA VITORIA-GASTEIZ': 'BAS',
        'CRVENA ZVEZDA MERIDIANBET BELGRADE': 'RED',
        'EA7 EMPORIO ARMANI MILAN': 'MIL', 
        'FC BARCELONA': 'BAR', 'FC BAYERN MUNICH': 'MUN',
        'FENERBAHCE BEKO ISTANBUL': 'ULK', 
        'LDLC ASVEL VILLEURBANNE': 'ASV',
        'MACCABI PLAYTIKA TEL AVIV': 'TEL', 'MACCABI RAPYD TEL AVIV': 'TEL',
        'OLYMPIACOS PIRAEUS': 'OLY',
        'PANATHINAIKOS AKTOR ATHENS': 'PAN', 
        'PARTIZAN MOZZART BET BELGRADE': 'PAR',
        'PARIS BASKETBALL': 'PRS', 
        'REAL MADRID': 'MAD', 
        'VALENCIA BASKET': 'PAM', 
        'VIRTUS SEGAFREDO BOLOGNA': 'VIR', 'VIRTUS BOLOGNA': 'VIR',
        'ZALGIRIS KAUNAS': 'ZAL', 
        'DUBAI BASKETBALL': 'DUB',
        'HAPOEL IBI TEL AVIV': 'HTA'
    }

    try:
        tree = ET.parse('official_schedule_2025.xml')
        root = tree.getroot()
        all_items = root.findall('item')
        
        remaining_games = []
        for item in all_items:
            gameday_text = item.find('gameday').text
            if not gameday_text: continue
            
            gameday = int(gameday_text)
            if gameday > 28:
                home_name = item.find('hometeam').text
                away_name = item.find('awayteam').text
                
                h_code = name_to_code.get(home_name, "UNK")
                a_code = name_to_code.get(away_name, "UNK")
                
                if h_code != "UNK" and a_code != "UNK":
                    remaining_games.append((h_code, a_code))
                    
        print(f"Found {len(remaining_games)} unplayed games to simulate.")
        
    except Exception as e:
        print(f"Error loading schedule: {e}")
        return

    # 3. Simulate
    np.random.seed(42) # For reproducibility
    
    sim_wins = np.tile(base_wins, (num_simulations, 1))
    sim_pd = np.tile(base_pd, (num_simulations, 1))

    for h_code, a_code in remaining_games:
        h_idx = team_to_idx[h_code]
        a_idx = team_to_idx[a_code]
        
        # 3.1 Advanced Prediction Formula
        # Instead of static net rating, we use True Home Rating vs True Away Rating
        # Then we blend in current Form (momentum) weighted at 30%
        
        h_base = home_ratings[h_idx]
        a_base = away_ratings[a_idx]
        
        h_form = form_ratings[h_idx]
        a_form = form_ratings[a_idx]
        
        # Blended Rating: 70% Base Location Strength + 30% Recent Form
        h_power = (h_base * 0.70) + (h_form * 0.30)
        a_power = (a_base * 0.70) + (a_form * 0.30)
        
        # Calculate Margin. Note: HCA is inherently baked into the True Home/Away split, 
        # so we DO NOT add the flat +3.4 anymore.
        pred_margin = h_power - a_power
        
        # Simulate Margin with noise (std dev of 12 points)
        margins = np.random.normal(loc=pred_margin, scale=12.0, size=num_simulations)
        
        # Resolve exact ties randomly
        margins[margins == 0] = np.random.choice([0.1, -0.1], size=np.sum(margins == 0))
        
        home_wins = (margins > 0).astype(int)
        away_wins = 1 - home_wins
        
        sim_wins[:, h_idx] += home_wins
        sim_wins[:, a_idx] += away_wins
        
        sim_pd[:, h_idx] += margins
        sim_pd[:, a_idx] -= margins

    # 4. Rank and Aggregate
    print("Aggregating ranks...")
    
    # Sort primarily by Wins, secondarily by PD
    combine_score = sim_wins * 10000 + sim_pd
    
    ranks_idx = np.argsort(-combine_score, axis=1) 
    team_ranks = np.argsort(ranks_idx, axis=1) 
    
    results = {}
    for i, t in enumerate(team_list):
        ranks_for_team = team_ranks[:, i] 
        
        # REVERTED COLUMNS: Standard Cumulative Probabilities
        top4 = np.sum(ranks_for_team < 4)
        top6 = np.sum(ranks_for_team < 6)
        top10 = np.sum(ranks_for_team < 10)
        
        avg_wins = np.mean(sim_wins[:, i])
        
        results[t] = {
            'Top4_Pct': round(top4 / num_simulations * 100, 1),
            'Top6_Pct': round(top6 / num_simulations * 100, 1),
            'Top10_Pct': round(top10 / num_simulations * 100, 1),
            'Sort_Metric': int(top6),
            'Avg_Wins': round(avg_wins, 1),
            'Current_Wins': int(base_wins[i])
        }

    # Sort results
    sorted_results = sorted(list(results.items()), key=lambda x: (x[1]['Sort_Metric'], x[1]['Top10_Pct']), reverse=True)
    
    final_json = []
    print("\n--- FINAL SIMULATION RESULTS ---")
    for t_tuple in sorted_results:
        t = t_tuple[0]
        data = t_tuple[1]
        final_json.append({'Team': t, **data})
        print(f"{t}: Avg Wins: {data['Avg_Wins']} | Top 4: {data['Top4_Pct']:>5.1f}% | Top 6: {data['Top6_Pct']:>5.1f}% | Top 10: {data['Top10_Pct']:>5.1f}%")

    with open('monte_carlo_results.json', 'w') as f:
        json.dump(final_json, f, indent=4)
        
    print("\nSaved fully aggregated matrix to monte_carlo_results.json!")

if __name__ == "__main__":
    run_monte_carlo(10000)
