import pandas as pd
import json

def analyze():
    print("--- PARTIZAN ORACLE ANOMALY ANALYSIS ---")
    df = pd.read_json('mvp_game_results.json')
    played = df[(df['LocalScore'] > 0) & (df['RoadScore'] > 0)].copy()

    # 1. Calculate League Net Ratings
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

    net_ratings = []
    for t, s in teams.items():
        if s['GP'] > 0:
            net = (s['PTS'] - s['PA']) / s['GP']
            net_ratings.append({'Team': t, 'Net': net})

    net_ratings.sort(key=lambda x: x['Net'], reverse=True)
    
    print("\n--- LEAGUE NET RATINGS (TOP TO BOTTOM) ---")
    for i, t in enumerate(net_ratings):
        print(f"{i+1}. {t['Team']} : {t['Net']:.2f}")

    # 2. Extract Partizan's Actual Games
    par_games = played[(played['LocalTeam'] == 'PAR') | (played['RoadTeam'] == 'PAR')]
    
    close_wins = 0
    blowout_losses = 0
    
    print("\n--- PARTIZAN WINS & LOSSES PROFILE ---")
    
    for _, g in par_games.iterrows():
        is_home = g['LocalTeam'] == 'PAR'
        par_pts = g['LocalScore'] if is_home else g['RoadScore']
        opp_pts = g['RoadScore'] if is_home else g['LocalScore']
        margin = par_pts - opp_pts
        
        if margin > 0:
            if margin <= 5: close_wins += 1
        else:
            if abs(margin) >= 10: blowout_losses += 1

    print(f"Total Games: {len(par_games)}")
    print(f"Total Wins: {sum([1 for _, g in par_games.iterrows() if (g['LocalTeam']=='PAR' and g['LocalScore']>g['RoadScore']) or (g['RoadTeam']=='PAR' and g['RoadScore']>g['LocalScore'])])}")
    print(f"Close Wins (1-5 pts): {close_wins}")
    print(f"Blowout Losses (10+ pts): {blowout_losses}")
    
    # Check HCA impact
    avg_local = played['LocalScore'].mean()
    avg_road = played['RoadScore'].mean()
    hca = avg_local - avg_road
    
    par_net = next(t['Net'] for t in net_ratings if t['Team'] == 'PAR')
    print(f"\nOracle Formula: Partizan Home Pred Margin = PartizanNet ({par_net:.2f}) - OppNet + HCA ({hca:.2f})")
    print(f"Oracle Formula: Partizan Away Pred Margin = PartizanNet ({par_net:.2f}) - OppNet - HCA ({hca:.2f})")

if __name__ == "__main__":
    analyze()
