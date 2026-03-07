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

    # 1b. Load KenPom Adjusted Ratings
    adj_net_lookup = {}
    round_suffix = os.environ.get('EUROLEAGUE_ROUND_SUFFIX', '')
    in_file = f'adjusted_ratings{round_suffix}.json'
    if not os.path.exists(in_file):
        in_file = 'adjusted_ratings.json'
    if os.path.exists(in_file):
        with open(in_file, 'r') as f:
            adj_data = json.load(f)
        for entry in adj_data:
            adj_net_lookup[entry['Team']] = entry['Adj_Net']
        print(f"Loaded Adjusted Net Ratings for {len(adj_net_lookup)} teams.")
    else:
        print("Warning: adjusted_ratings.json not found. Using raw ratings only.")

    team_list = sorted(list(teams_data.keys()))
    num_teams = len(team_list)
    team_to_idx = {t: i for i, t in enumerate(team_list)}
    
    # Base Numpy Arrays
    base_wins = np.zeros(num_teams)
    base_pd = np.zeros(num_teams)
    home_ratings = np.zeros(num_teams)
    away_ratings = np.zeros(num_teams)
    form_ratings = np.zeros(num_teams)
    adj_net_ratings = np.zeros(num_teams)
    
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
        
        # KenPom Adjusted Net Rating
        adj_net_ratings[idx] = adj_net_lookup.get(t, 0)

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
        
        # Cross-check: build set of played game codes from actual results
        played_game_codes = set()
        for _, row in played.iterrows():
            played_game_codes.add(row['GameCode'])
        
        remaining_games = []
        for item in all_items:
            # Check XML played flag
            played_el = item.find('played')
            is_played = played_el is not None and played_el.text and played_el.text.lower() == 'true'
            
            # Also check against actual results (in case XML is stale)
            gc_el = item.find('gamecode')
            if gc_el is not None:
                gc_text = gc_el.text
                gc_num = int(gc_text.split('_')[1]) if '_' in gc_text else int(gc_text)
                if gc_num in played_game_codes:
                    is_played = True
            
            if is_played:
                continue
            
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
        
        # 3.1 Advanced 3-Factor Prediction Formula
        # Factor 1: KenPom Adjusted Net Rating (50%) — opponent-quality corrected
        # Factor 2: True Home/Away Location Split (20%) — captures venue-specific performance
        # Factor 3: Recent Form / Momentum (30%) — last 5 games streak
        
        h_adj = adj_net_ratings[h_idx]
        a_adj = adj_net_ratings[a_idx]
        
        h_loc = home_ratings[h_idx]
        a_loc = away_ratings[a_idx]
        
        h_form = form_ratings[h_idx]
        a_form = form_ratings[a_idx]
        
        # Blended Rating: 50% Adjusted + 20% Location + 30% Form
        h_power = (h_adj * 0.50) + (h_loc * 0.20) + (h_form * 0.30)
        a_power = (a_adj * 0.50) + (a_loc * 0.20) + (a_form * 0.30)
        
        # Adj Net is global (not location-split), so add reduced HCA bonus
        pred_margin = (h_power - a_power) + (hca * 0.5)
        
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
        
        # Win distribution: P(wins >= threshold) for each threshold
        win_dist = {}
        for threshold in range(15, 31):
            pct = int(np.sum(sim_wins[:, i] >= threshold) / num_simulations * 100)
            win_dist[str(threshold)] = pct
        
        # Seed distribution: P(finishing in position N) for N=1..num_teams
        seed_dist = {}
        for pos in range(num_teams):
            pct = round(np.sum(ranks_for_team == pos) / num_simulations * 100, 1)
            seed_dist[str(pos + 1)] = pct
        
        results[t] = {
            'Top4_Pct': round(top4 / num_simulations * 100, 1),
            'Top6_Pct': round(top6 / num_simulations * 100, 1),
            'Top10_Pct': round(top10 / num_simulations * 100, 1),
            'Sort_Metric': int(top6),
            'Avg_Wins': round(avg_wins, 1),
            'Current_Wins': int(base_wins[i]),
            'Win_Distribution': win_dist,
            'Seed_Distribution': seed_dist
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

    round_suffix = os.environ.get('EUROLEAGUE_ROUND_SUFFIX', '')
    outfile = f'monte_carlo_results{round_suffix}.json'

    with open(outfile, 'w') as f:
        json.dump(final_json, f, indent=4)
        
    print(f"\nSaved fully aggregated matrix to {outfile}!")

if __name__ == "__main__":
    run_monte_carlo(10000)
