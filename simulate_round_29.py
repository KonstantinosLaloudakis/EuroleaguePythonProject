import json
import pandas as pd
import xml.etree.ElementTree as ET
import re

def simulate_round_29():
    print("--- Simulating Round 29 (The Oracle) ---")
    
    # 1. Load Team Stats (Ratings & HCA)
    # We need Current Ratings. Let's recalculate from mvp_game_results.json
    try:
        df = pd.read_json('mvp_game_results.json')
        played = df[(df['LocalScore'] > 0) & (df['RoadScore'] > 0)].copy()
        
        # HCA
        hca = (played['LocalScore'] - played['RoadScore']).mean()
        print(f"Global HCA: +{hca:.2f} pts")
        
        # Net Ratings
        teams = {}
        for _, row in played.iterrows():
            local, road = row['LocalTeam'], row['RoadTeam']
            l_pts, r_pts = row['LocalScore'], row['RoadScore']
            
            if local not in teams: teams[local] = {'PTS': 0, 'PA': 0, 'GP': 0}
            if road not in teams: teams[road] = {'PTS': 0, 'PA': 0, 'GP': 0}
            
            teams[local]['PTS'] += l_pts
            teams[local]['PA'] += r_pts
            teams[local]['GP'] += 1
            
            teams[road]['PTS'] += r_pts
            teams[road]['PA'] += l_pts
            teams[road]['GP'] += 1
            
        ratings = {}
        for t, s in teams.items():
            ratings[t] = (s['PTS'] - s['PA']) / s['GP'] if s['GP'] > 0 else 0
            
    except Exception as e:
        print(f"Error loading stats: {e}")
        return

    # 2. Parse Round 29 Matchups from XML
    matchups = []
    try:
        tree = ET.parse('official_schedule_2025.xml')
        root = tree.getroot()
        
        # Name Mapping (XML to Our Codes)
        # XML Names are full uppercase, e.g. "ZALGIRIS KAUNAS"
        # Our Codes are 3-letter, e.g. "ZAL"
        # We need a robust mapping.
        # Let's infer from existing data or hardcode known ones.
        namemap = {
            "ZALGIRIS KAUNAS": "ZAL", "OLYMPIACOS PIRAEUS": "OLY",
            "DUBAI BASKETBALL": "DUB", "LDLC ASVEL VILLEURBANNE": "ASV",
            "FENERBAHCE BEKO ISTANBUL": "ULK", "PARTIZAN MOZZART BET BELGRADE": "PAR", # Fener uses ULK code in our dataset? Or FNB? Let's check.
            "REAL MADRID": "MAD", "FC BAYERN MUNICH": "MUN",
            "VALENCIA BASKET": "PAM", # Valencia is PAM? Pamesa? Or VAL? In our dataset it seems to be PAM based on Standings? No, Valencia is VAL?
            # Wait, our dataset uses Codes like: IST, TEL, BAS, OLY, RED, PAO, ZAL, ...
            # Let's peek at `mvp_game_results.json` teams to be sure.
        }
        
        # Rough manual map based on dataset observation
        # IST = Efes? ULK = Fener? 
        # Let's perform a "Fuzzy Match" later or check the codes in JSON.
        # Actually, let's just use the `teams` keys from Step 1 to Map.
        
        known_codes = sorted(list(ratings.keys()))
        print(f"Dataset Team Keys ({len(known_codes)}): {known_codes}")
        
        # Refined Map based on typical Euroleague codes
        # Refined Map based on typical Euroleague codes
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

        r29_items = [i for i in root.findall('item') if i.find('gameday').text == '29']
        
        predictions = []
        
        print("\n--- Round 29 Predictions ---")
        for item in r29_items:
            home_name = item.find('hometeam').text
            away_name = item.find('awayteam').text
            
            home_code = name_to_code.get(home_name, "UNK")
            away_code = name_to_code.get(away_name, "UNK")
            
            if home_code == "UNK" or away_code == "UNK":
                print(f"Warning: Could not map {home_name} or {away_name}")
                continue
                
            # Oracle Logic
            h_net = ratings.get(home_code, 0)
            a_net = ratings.get(away_code, 0)
            
            pred_margin = (h_net - a_net) + hca
            winner = home_code if pred_margin > 0 else away_code
            margin = abs(pred_margin)
            
            # Confidence/Insight
            # "Lock" if margin > 8
            # "Toss-up" if margin < 3
            # "Upset Alert" if Away Favorite (Margin < 0 from Home perspective)
            
            insight = ""
            if margin > 9: insight = "🔒 BANKER"
            elif margin < 3: insight = "⚖️ TOSS-UP"
            elif winner == away_code: insight = "🚨 UPSET ALERT"
            else: insight = "✅ SOLID FAVORITE"
            
            print(f"{home_code} vs {away_code} | Pred: {winner} +{margin:.1f} | {insight}")
            
            predictions.append({
                'Home': home_code,
                'Away': away_code,
                'Winner': winner,
                'Margin': round(margin, 1),
                'Insight': insight
            })
            
        # Save Predictions
        with open('round_29_forecast.json', 'w') as f:
            json.dump(predictions, f, indent=4)
            
        print("Predictions saved to round_29_forecast.json")

        # 3. Visualization (The Poster)
        import matplotlib.pyplot as plt
        import matplotlib.image as mpimg
        from matplotlib.offsetbox import OffsetImage, AnnotationBbox
        import os

        # Set up the figure
        fig, ax = plt.subplots(figsize=(12, 16))
        fig.patch.set_facecolor('#0f172a') # Dark Navy Background
        ax.set_facecolor('#0f172a')
        
        # Title
        ax.text(0.5, 0.96, "THE ORACLE", ha='center', va='center', fontsize=30, color='#fbbf24', fontweight='bold')
        ax.text(0.5, 0.93, "ROUND 29 FORECAST", ha='center', va='center', fontsize=20, color='white', fontweight='light')
        
        # Grid System for Matchups
        # 2 columns of 5 games.
        y_start = 0.85
        x_left = 0.25
        x_right = 0.75
        
        # Sort by Margin (Closest first)
        predictions.sort(key=lambda x: x['Margin'], reverse=False) 
        
        for i, game in enumerate(predictions):
            if i >= 10: break # Limit to top 10 if more
            col = x_left if i < 5 else x_right
            row = i if i < 5 else i - 5
            y = y_start - (row * 0.15)
            
            home = game['Home']
            away = game['Away']
            winner = game['Winner']
            margin = game['Margin']
            insight = game.get('Insight', '')
            
            # Matchup Text
            ax.text(col, y, f"{home} vs {away}", ha='center', va='bottom', fontsize=16, color='white', fontweight='bold')
            
            # Prediction
            if winner == home:
                pred_text = f"{home} +{margin}"
                color = '#4ade80' # Green
            else:
                pred_text = f"{away} +{margin}"
                color = '#f87171' # Red
                
            ax.text(col, y-0.03, f"Pick: {pred_text}", ha='center', va='top', fontsize=20, color=color, fontweight='bold')
            
            # Insight Pill
            if insight:
                ax.text(col, y-0.06, insight, ha='center', va='top', fontsize=12, color='#fbbf24', style='italic')
                
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        
        plt.tight_layout()
        plt.savefig('round_29_forecast.png', dpi=150, facecolor='#0f172a')
        print("Forecast poster saved to round_29_forecast.png")

    except Exception as e:
        print(f"Error parsing schedule: {e}")

if __name__ == "__main__":
    simulate_round_29()
