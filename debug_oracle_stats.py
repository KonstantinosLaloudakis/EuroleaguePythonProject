import pandas as pd
import json

def debug_stats():
    # 1. Load Data
    try:
        df = pd.read_json('mvp_game_results.json')
    except Exception as e:
        print(f"Error loading mvp_game_results.json: {e}")
        return

    # Filter for played games only
    played = df[(df['LocalScore'] > 0) & (df['RoadScore'] > 0)].copy()
    
    # 3. Calculate Team Ratings (ORTG/DRTG)
    teams = {}
    
    for _, row in played.iterrows():
        local = row['LocalTeam']
        road = row['RoadTeam']
        l_pts = row['LocalScore']
        r_pts = row['RoadScore']
        
        if local not in teams: teams[local] = {'PTS': 0, 'PA': 0, 'GP': 0}
        if road not in teams: teams[road] = {'PTS': 0, 'PA': 0, 'GP': 0}
        
        teams[local]['PTS'] += l_pts
        teams[local]['PA'] += r_pts
        teams[local]['GP'] += 1
        
        teams[road]['PTS'] += r_pts
        teams[road]['PA'] += l_pts
        teams[road]['GP'] += 1
        
    team_stats = {}
    for t, s in teams.items():
        if s['GP'] > 0:
            team_stats[t] = {
                'ORTG': s['PTS'] / s['GP'],
                'DRTG': s['PA'] / s['GP'],
                'Net': (s['PTS'] - s['PA']) / s['GP'],
                'GP': s['GP']
            }

    # Rank them
    sorted_ortg = sorted(team_stats.items(), key=lambda x: x[1]['ORTG'], reverse=True)
    sorted_drtg = sorted(team_stats.items(), key=lambda x: x[1]['DRTG'])
    
    ortg_rank = {team: i+1 for i, (team, _) in enumerate(sorted_ortg)}
    drtg_rank = {team: i+1 for i, (team, _) in enumerate(sorted_drtg)}
    
    # Inspect ULK and PAR
    targets = ['ULK', 'PAR']
    print(f"{'Team':<5} {'GP':<4} {'ORTG':<6} {'DRTG':<6} {'Net':<6} {'O-Rank':<8} {'D-Rank':<8}")
    print("-" * 60)
    for t in targets:
        s = team_stats.get(t)
        if s:
            o_r = ortg_rank.get(t)
            d_r = drtg_rank.get(t)
            print(f"{t:<5} {s['GP']:<4} {s['ORTG']:<6.1f} {s['DRTG']:<6.1f} {s['Net']:<6.1f} #{o_r:<7} #{d_r:<7}")
        else:
            print(f"{t} not found in stats.")

    # Logic Check for ULK (Local) vs PAR (Road)
    # Replicate logic
    l_o_rank = ortg_rank.get('ULK', 99)
    r_o_rank = ortg_rank.get('PAR', 99)
    l_d_rank = drtg_rank.get('ULK', 99)
    r_d_rank = drtg_rank.get('PAR', 99)
    
    ulf_net = team_stats['ULK']['Net']
    par_net = team_stats['PAR']['Net']
    
    print("\nLogic Trace:")
    print(f"1. New Blood? No.")
    print(f"2. Mismatch (Top 5 Off vs Bottom 5 Def)? ULK Off #{l_o_rank} vs PAR Def #{r_d_rank}. (Req: <=5 vs >=15)")
    print(f"3. Upset (Top 5 Off vs Bottom 5 Def)? PAR Off #{r_o_rank} vs ULK Def #{l_d_rank}. (Req: <=5 vs >=15)")
    print(f"4. Shootout (Top 8 Off vs Top 8 Off)? #{l_o_rank} vs #{r_o_rank}. (Req: Both <=8)")
    print(f"5. Grind It Out (Top 6 Def vs Top 6 Def)? #{l_d_rank} vs #{r_d_rank}. (Req: Both <=6)")
    print(f"6. Toss-Up (Diff < 2)? Abs({ulf_net:.1f} - {par_net:.1f}) = {abs(ulf_net - par_net):.1f}")
    print(f"7. Heavyweight (Both > +5)? {ulf_net:.1f} > 5 and {par_net:.1f} > 5?")
    print(f"8. Default Case: ULK ORTG {team_stats['ULK']['ORTG']:.1f} > 85?")

if __name__ == "__main__":
    debug_stats()
