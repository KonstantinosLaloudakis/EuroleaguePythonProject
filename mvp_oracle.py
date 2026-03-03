import pandas as pd
import matplotlib.pyplot as plt
import argparse
import sys
import json
import numpy as np
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import matplotlib.image as mpimg
from PIL import Image
import os

def run_oracle(target_round=None):
    # 1. Load Data
    try:
        df = pd.read_json('mvp_game_results.json')
    except Exception as e:
        print(f"Error loading mvp_game_results.json: {e}")
        return

    # 2. Determine HCA (Home Court Advantage)
    # Filter for played games only
    played = df[(df['LocalScore'] > 0) & (df['RoadScore'] > 0)].copy()
    
    if played.empty:
        print("No played games found. Cannot calculate stats.")
        return
        
    avg_local = played['LocalScore'].mean()
    avg_road = played['RoadScore'].mean()
    hca = avg_local - avg_road
    print(f"Global Home Court Advantage (HCA): +{hca:.1f} pts")

    # 3. Calculate Team Ratings (ORTG/DRTG) with Home/Away Splits
    teams = {}
    
    for _, row in played.iterrows():
        local = row['LocalTeam']
        road = row['RoadTeam']
        l_pts = row['LocalScore']
        r_pts = row['RoadScore']
        
        if local not in teams: teams[local] = {
            'PTS': 0, 'PA': 0, 'GP': 0,
            'HomePTS': 0, 'HomePA': 0, 'HomeGP': 0,
            'AwayPTS': 0, 'AwayPA': 0, 'AwayGP': 0,
            'GameMargins': []
        }
        if road not in teams: teams[road] = {
            'PTS': 0, 'PA': 0, 'GP': 0,
            'HomePTS': 0, 'HomePA': 0, 'HomeGP': 0,
            'AwayPTS': 0, 'AwayPA': 0, 'AwayGP': 0,
            'GameMargins': []
        }
        
        teams[local]['PTS'] += l_pts
        teams[local]['PA'] += r_pts
        teams[local]['GP'] += 1
        teams[local]['HomePTS'] += l_pts
        teams[local]['HomePA'] += r_pts
        teams[local]['HomeGP'] += 1
        teams[local]['GameMargins'].append(l_pts - r_pts)
        
        teams[road]['PTS'] += r_pts
        teams[road]['PA'] += l_pts
        teams[road]['GP'] += 1
        teams[road]['AwayPTS'] += r_pts
        teams[road]['AwayPA'] += l_pts
        teams[road]['AwayGP'] += 1
        teams[road]['GameMargins'].append(r_pts - l_pts)
        
    team_names = {
        'OLY': 'Olympiacos', 'ULK': 'Fenerbahce', 'PAN': 'Panathinaikos',
        'MAD': 'Real Madrid', 'BAR': 'Barcelona', 'MCO': 'Monaco',
        'ZAL': 'Zalgiris', 'DUB': 'Dubai BC', 'IST': 'Anadolu Efes',
        'HTA': 'Hapoel Tel Aviv', 'PAR': 'Partizan', 'RED': 'Crvena Zvezda',
        'TEL': 'Maccabi', 'BAS': 'Baskonia', 'MUN': 'Bayern',
        'VIR': 'Virtus Bologna', 'PAM': 'Valencia', 'ASV': 'ASVEL',
        'PRS': 'Paris Basketball', 'BER': 'ALBA Berlin',
        'MIL': 'EA7 Milan'
    }

    team_stats = {}
    for t, s in teams.items():
        if s['GP'] > 0:
            home_net = (s['HomePTS'] - s['HomePA']) / s['HomeGP'] if s['HomeGP'] > 0 else 0
            away_net = (s['AwayPTS'] - s['AwayPA']) / s['AwayGP'] if s['AwayGP'] > 0 else 0
            form_margins = s['GameMargins'][-5:] if len(s['GameMargins']) >= 5 else s['GameMargins']
            form = sum(form_margins) / len(form_margins) if form_margins else 0
            team_stats[t] = {
                'ORTG': s['PTS'] / s['GP'],
                'DRTG': s['PA'] / s['GP'],
                'Net': (s['PTS'] - s['PA']) / s['GP'],
                'HomeNet': home_net,
                'AwayNet': away_net,
                'Form': form
            }
        else:
             team_stats[t] = {'ORTG': 80, 'DRTG': 80, 'Net': 0, 'HomeNet': 0, 'AwayNet': 0, 'Form': 0}

    # 3.1 Load KenPom Adjusted Net Ratings
    adj_net_lookup = {}
    sos_lookup = {}
    if os.path.exists('adjusted_ratings.json'):
        with open('adjusted_ratings.json', 'r') as f:
            adj_data = json.load(f)
        for entry in adj_data:
            adj_net_lookup[entry['Team']] = entry['Adj_Net']
            sos_lookup[entry['Team']] = entry.get('SOS_WinPct', 0.5)
        print(f"Loaded KenPom Adjusted Net Ratings for {len(adj_net_lookup)} teams.")
    else:
        print("Warning: adjusted_ratings.json not found. Falling back to raw ratings.")

    # 3.5 Calculate League Rankings
    # Sort by ORTG (Desc) and DRTG (Asc)
    sorted_ortg = sorted(team_stats.items(), key=lambda x: x[1]['ORTG'], reverse=True)
    sorted_drtg = sorted(team_stats.items(), key=lambda x: x[1]['DRTG']) # Lower is better
    
    # Create Rank Maps
    ortg_rank = {team: i+1 for i, (team, _) in enumerate(sorted_ortg)}
    drtg_rank = {team: i+1 for i, (team, _) in enumerate(sorted_drtg)}
    
    total_teams = len(team_stats)

    # 3.6 Calculate Form and Venue Stats
    team_form = {t: {'Streak': 0, 'Last5': [], 'HomeW': 0, 'HomeG': 0, 'RoadW': 0, 'RoadG': 0} for t in team_stats}
    
    # Re-iterate games in chronological order to build form
    # Sort by GameCode just in case
    df_sorted = df.sort_values('GameCode')
    
    for _, row in df_sorted.iterrows():
        if row['LocalScore'] == 0: continue # Skip unplayed
        
        local = row['LocalTeam']
        road = row['RoadTeam']
        l_pts = row['LocalScore']
        r_pts = row['RoadScore']
        
        l_win = l_pts > r_pts
        r_win = r_pts > l_pts # Tie unlikely but possible in agg? No, single game.
        
        # Update Local
        if local in team_form:
            team_form[local]['HomeG'] += 1
            if l_win: 
                team_form[local]['HomeW'] += 1
                if team_form[local]['Streak'] > 0: team_form[local]['Streak'] += 1
                else: team_form[local]['Streak'] = 1
                team_form[local]['Last5'].append('W')
            else:
                if team_form[local]['Streak'] < 0: team_form[local]['Streak'] -= 1
                else: team_form[local]['Streak'] = -1
                team_form[local]['Last5'].append('L')
            if len(team_form[local]['Last5']) > 5: team_form[local]['Last5'].pop(0)

        # Update Road
        if road in team_form:
            team_form[road]['RoadG'] += 1
            if r_win:
                team_form[road]['RoadW'] += 1
                if team_form[road]['Streak'] > 0: team_form[road]['Streak'] += 1
                else: team_form[road]['Streak'] = 1
                team_form[road]['Last5'].append('W')
            else:
                if team_form[road]['Streak'] < 0: team_form[road]['Streak'] -= 1
                else: team_form[road]['Streak'] = -1
                team_form[road]['Last5'].append('L')
            if len(team_form[road]['Last5']) > 5: team_form[road]['Last5'].pop(0)

    # 4. Identify Target Round
    # 9 games per round.
    # If target_round not provided, find first game with score 0
    df['GameIdx'] = df.index
    # Assuming chronological order in JSON (parse_mvp_data usually keeps it)
    # GameCode is key.
    
    if target_round is None:
        unplayed = df[df['LocalScore'] == 0]
        if not unplayed.empty:
            first_game = unplayed.iloc[0]['GameCode']
            # Heuristic: Round = (GameCode-1) // 9 + 1
            # But GameCodes in file might be sparse? 
            # Let's trust the input file order.
            # mvp_game_results has 1 row per game.
            # Row index // 9 + 1 = Round?
            # Let's use GameCode if present.
            target_round = (first_game - 1) // 9 + 1
            print(f"Auto-detected next round: {target_round} (GameCode {first_game})")
        else:
            print("All games played. Defaulting to Round 30.")
            target_round = 30
            
    # Try to load manual schedule if available
    manual_file = f'manual_round_{target_round}.json'
    import os
    if os.path.exists(manual_file):
        print(f"Loading manual schedule from {manual_file}...")
        try:
            manual_games = pd.read_json(manual_file)
            round_games = manual_games
        except Exception as e:
            print(f"Error loading manual schedule: {e}")
            round_games = pd.DataFrame()
    else:
        # Filter from main dataset with Offset
        # Offset Calculation:
        # Round 1 starts at GameCode 28 (Offset 27).
        # Round 29 starts at (29-1)*9 + 1 + 27 = 252 + 1 + 27 = 280.
        offset = 27
        
        start_gc = (target_round - 1) * 9 + 1 + offset
        end_gc = target_round * 9 + offset
        
        round_games = df[(df['GameCode'] >= start_gc) & (df['GameCode'] <= end_gc)].copy()
    
    if round_games.empty:
        print(f"No games found for Round {target_round}.")
        return

    print(f"Predicting {len(round_games)} games for Round {target_round}...")
    
    # Load Advanced Stats (optional, for X-Factor insights)
    adv_stats = {}
    try:
        with open('C:/Users/klalo/PycharmProjects/pythonProject/team_advanced_stats.json', 'r') as f:
            adv_stats = json.load(f)
    except:
        pass
    
    # 5. Predict Matches using 3-Factor Model
    predictions = []
    
    for _, row in round_games.iterrows():
        local = row['LocalTeam']
        road = row['RoadTeam']
        
        local_name = team_names.get(local, local)
        road_name = team_names.get(road, road)

        l_stat = team_stats.get(local, {'ORTG': 80, 'DRTG': 80, 'Net': 0, 'HomeNet': 0, 'AwayNet': 0, 'Form': 0})
        r_stat = team_stats.get(road, {'ORTG': 80, 'DRTG': 80, 'Net': 0, 'HomeNet': 0, 'AwayNet': 0, 'Form': 0})
        
        l_form = team_form.get(local, {'Streak': 0, 'HomeW': 0, 'HomeG': 1, 'Last5': [], 'RoadW': 0, 'RoadG': 1})
        r_form = team_form.get(road, {'Streak': 0, 'RoadW': 0, 'RoadG': 1, 'Last5': [], 'HomeW': 0, 'HomeG': 1})
        
        # Rankings
        l_o_rank = ortg_rank.get(local, 99)
        l_d_rank = drtg_rank.get(local, 99)
        r_o_rank = ortg_rank.get(road, 99)
        r_d_rank = drtg_rank.get(road, 99)
        
        l_home_pct = (l_form['HomeW'] / l_form['HomeG']) * 100 if l_form['HomeG'] > 0 else 0
        r_road_pct = (r_form['RoadW'] / r_form['RoadG']) * 100 if r_form['RoadG'] > 0 else 0
        
        # === 3-FACTOR PREDICTION MODEL ===
        # Weights optimized via incremental backtest (70/10/20 > 50/20/30)
        # Factor 1: KenPom Adjusted Net Rating (70%) — strongest single predictor
        l_adj = adj_net_lookup.get(local, l_stat['Net'])
        r_adj = adj_net_lookup.get(road, r_stat['Net'])
        
        # Factor 2: True Home/Away Location Split (10%)
        l_loc = l_stat['HomeNet']   # Local team's home performance
        r_loc = r_stat['AwayNet']   # Road team's away performance
        
        # Factor 3: Recent Form / Momentum (20%)
        l_form_val = l_stat['Form']
        r_form_val = r_stat['Form']
        
        # Blended Power Rating
        l_power = (l_adj * 0.70) + (l_loc * 0.10) + (l_form_val * 0.20)
        r_power = (r_adj * 0.70) + (r_loc * 0.10) + (r_form_val * 0.20)
        
        # Predicted margin with reduced HCA (since Adj Net is global)
        margin = (l_power - r_power) + (hca * 0.5)
        
        winner = local if margin > 0 else road
        
        # Logistic confidence (proper probability calibration)
        win_prob = 1 / (1 + np.exp(-margin / 6)) * 100
        
        # === X-FACTOR INSIGHTS ===
        # Now data-driven with SOS context
        insight = ""
        l_sos = sos_lookup.get(local, 0.5)
        r_sos = sos_lookup.get(road, 0.5)
        
        # 1. Hot Streaks (>=5)
        if l_form['Streak'] >= 5: insight = f"🔥 {local_name} Won {l_form['Streak']} Straight"
        elif r_form['Streak'] >= 5: insight = f"🔥 {road_name} Won {r_form['Streak']} Straight"
        elif l_form['Streak'] <= -5: insight = f"❄️ {local_name} Lost {abs(l_form['Streak'])} Straight"
        elif r_form['Streak'] <= -5: insight = f"❄️ {road_name} Lost {abs(r_form['Streak'])} Straight"
        
        # 2. Venue Fortress (>85% Home)
        elif l_home_pct >= 85:
             insight = f"🏟️ FORTRESS: {local_name} {l_home_pct:.0f}% at Home"
             
        # 3. Road Warriors (>55% Road)
        elif r_road_pct >= 55:
             insight = f"✈️ {road_name} {r_road_pct:.0f}% Away Win Rate"
        
        # 4. SOS mismatch (one team's SOS >> other's)
        elif abs(l_sos - r_sos) > 0.08:
            harder = local_name if l_sos > r_sos else road_name
            insight = f"📊 {harder} has faced tougher schedule"
        
        # 5. Rank Clash
        elif l_o_rank <= 4 and r_d_rank <= 4:
             insight = f"⚔️ Top 4 Offense vs Top 4 Defense"
             
        # Default: Adj Net gap
        else:
            gap = abs(l_adj - r_adj)
            if gap > 5:
                stronger = local_name if l_adj > r_adj else road_name
                insight = f"📈 {stronger} +{gap:.1f} Adj Net advantage"
            else:
                insight = f"⚖️ Evenly matched (Adj Net gap: {gap:.1f})"
        
        # Build insight block
        line2 = f"Adj Net: {l_adj:+.1f} v {r_adj:+.1f}  |  Form: {l_form_val:+.1f} v {r_form_val:+.1f}"
        
        l_l5 = l_form.get('Last5', [])
        r_l5 = r_form.get('Last5', [])
        l_l5_w = l_l5.count('W')
        r_l5_w = r_l5.count('W')
        
        line3 = f"L5: {l_l5_w}-{(5-l_l5_w)} v {r_l5_w}-{(5-r_l5_w)}  |  H: {l_form['HomeW']}-{l_form['HomeG']-l_form['HomeW']} v A: {r_form.get('RoadW',0)}-{r_form.get('RoadG',0)-r_form.get('RoadW',0)}"
        
        final_insight = f"{insight}\n{line2}\n{line3}"
        
        predictions.append({
            'Local': local,
            'Road': road,
            'Margin': margin,
            'Winner': winner,
            'Conf': win_prob,
            'Insight': final_insight
        })

    # 6. Visualize
    cols = 3
    rows = (len(predictions) // cols) + (1 if len(predictions)%cols else 0)
    
    rows = (len(predictions) // cols) + (1 if len(predictions)%cols else 0)
    
    # Taller figsize to fit text (even taller for 3-line insight)
    # INCREASED HEIGHT: 8 inches per row to prevent layout cramping
    fig, axes = plt.subplots(rows, cols, figsize=(15, 8*rows))
    fig.suptitle(f"THE ORACLE: Round {target_round} Forecast", fontsize=24, fontweight='bold', color='#1d428a')
    
    axes = axes.flatten()
    
    team_colors = {
        'OLY': '#E2001A', 'ULK': '#002B5C', 'PAN': '#007F3D', 
        'MAD': '#645486', 'BAR': '#004D98', 'MCO': '#D4AF37',
        'ZAL': '#006233', 'DUB': '#000000', 'IST': '#003366',
        'HTA': '#000000', 'PAR': '#000000', 'RED': '#CC0000', 
        'TEL': '#F6C300', 'BAS': '#B50031', 'MUN': '#0066B2',
        'VIR': '#000000', 'PAM': '#EB7622', 'ASV': '#000000',
        'PRS': '#000000' # Paris
    }
    


    for i, pred in enumerate(predictions):
        ax = axes[i]
        
        local = pred['Local']
        road = pred['Road']
        
        local_name = team_names.get(local, local)
        road_name = team_names.get(road, road)
        
        margin = pred['Margin']
        win_prob = pred['Conf']  # Already calibrated by logistic function
        
        # Card BG
        ax.set_facecolor('#f8f9fa')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        
        # Team Names
        l_col = team_colors.get(local, '#333')
        r_col = team_colors.get(road, '#333')
        # Team Names (Larger)
        # Team Names (Larger)
        # Add Logos if available
        # Add Logos if available
        def add_normalized_logo(ax, team_code, x, y):
             logo_path = f"logos/{team_code}.png"
             if os.path.exists(logo_path):
                 try:
                     img = Image.open(logo_path).convert("RGBA")
                     img.thumbnail((150, 150)) # Keep 150 for resolution
                     
                     # Zoom 0.75 was too big (112px). 
                     # Target ~60px effective size -> 0.40 zoom
                     imagebox = OffsetImage(img, zoom=0.40) 
                     ab = AnnotationBbox(imagebox, (x, y), frameon=False)
                     ax.add_artist(ab)
                     return True
                 except Exception as e:
                     print(f"Error loading logo for {team_code}: {e}")
             return False

        # LOGO PLACEMENT: Vertical Stack "Poster Style"
        # Since horizontal space is tight for long names, we stack them vertically.
        # Structure:
        # [Home Logo]
        # [Home Name]
        #     vs
        # [Away Name]
        # [Away Logo]
        
        # LOGO PLACEMENT: Vertical Stack "Poster Style"
        # Since horizontal space is tight for long names, we stack them vertically.
        # Structure:
        # [Home Logo]
        # [Home Name]
        #     vs
        # [Away Name]
        # [Away Logo]
        # [Gap]
        # [Winner]
        # [Insight]
        # [Chart]
        
        # Local (Top)
        # Logo at Top (0.5, 0.92)
        logo_loaded = add_normalized_logo(ax, local, 0.5, 0.92)
        
        # Name below Logo (0.5, 0.81)
        ax.text(0.5, 0.81, local_name, ha='center', va='center', fontsize=14, fontweight='bold', color=l_col)
        
        # VS (0.5, 0.74)
        ax.text(0.5, 0.74, "vs", ha='center', va='center', fontsize=10, color='#aaa')
        
        # Road (Below VS)
        # Name (0.5, 0.67)
        ax.text(0.5, 0.67, road_name, ha='center', va='center', fontsize=14, fontweight='bold', color=r_col)
        
        # Logo below Name (0.5, 0.55) - Increased gap
        logo_loaded_r = add_normalized_logo(ax, road, 0.5, 0.55)
        
        # Winner (0.5, 0.40) - Huge gap from logo
        winner = pred['Winner']
        # User request: "Winner: Team by X.X"
        ax.text(0.5, 0.40, f"WINNER: {team_names.get(winner, winner)} by {abs(margin):.1f}", ha='center', fontsize=16, fontweight='bold', color='green')
        ax.text(0.5, 0.34, f"{win_prob:.0f}% Confidence", ha='center', fontsize=11, color='#666')
        
        # Insight (0.5, 0.22)
        ax.text(0.5, 0.22, pred['Insight'], ha='center', fontsize=9, fontstyle='normal', color='#333', 
                bbox=dict(facecolor='white', alpha=0.9, edgecolor='#ddd', boxstyle='round,pad=0.3'))
        
        # Removed Bottom Bar as per user request. Margin is now in the Winner line.

        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off') # Hide axes lines



    # Hide unused subplots completely
    for j in range(i+1, len(axes)):
        axes[j].set_visible(False)
    
    plt.tight_layout()
    plt.subplots_adjust(top=0.92)
    
    outfile = f"oracle_forecast_round_{target_round}.png"
    plt.savefig(outfile, dpi=150)
    print(f"Forecast saved to {outfile}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--round', type=int, help='Round number to predict')
    args = parser.parse_args()
    
    run_oracle(args.round)
