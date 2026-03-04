"""
Shot Creation Network — The Architect's Blueprint
Combines spatial xFG% model with PbP assist parsing to find
who creates the highest-quality shots for whom.

Three stages:
1. Build xFG% model from 45K shot coordinates
2. Parse PbP to extract Passer → Scorer connections
3. Merge to calculate shot quality per connection
"""

import pandas as pd
import numpy as np
import json
import sys


# ======================================================================
# STAGE 1: xFG% Model (Spatial Shot Quality)
# ======================================================================

def build_xfg_model(shots_df):
    """
    Build Expected FG% by zone/distance.
    Uses the ZONE column (A-J) and shot distance from basket.
    """
    # Calculate distance from basket (basket is roughly at x=0, y=0 in Euroleague coords)
    # Euroleague court: basket at ~(0, 0), half court at ~(0, 700)
    shots_df = shots_df.copy()
    shots_df['COORD_X'] = pd.to_numeric(shots_df['COORD_X'], errors='coerce')
    shots_df['COORD_Y'] = pd.to_numeric(shots_df['COORD_Y'], errors='coerce')
    
    # Filter out invalid coordinates
    shots_df = shots_df.dropna(subset=['COORD_X', 'COORD_Y'])
    shots_df = shots_df[(shots_df['COORD_X'] != -1) & (shots_df['COORD_Y'] != -1)]
    
    # Distance from basket
    shots_df['DIST'] = np.sqrt(shots_df['COORD_X']**2 + shots_df['COORD_Y']**2)
    
    # Determine if made or missed (POINTS > 0 means made)
    shots_df['MADE'] = (pd.to_numeric(shots_df['POINTS'], errors='coerce') > 0).astype(int)
    
    # Shot type
    shots_df['SHOT_TYPE'] = shots_df['ACTION'].apply(
        lambda x: '3PT' if 'Three' in str(x) else ('2PT' if 'Two' in str(x) else 'FT')
    )
    
    # Filter to field goals only (exclude free throws for xFG)
    fg_shots = shots_df[shots_df['SHOT_TYPE'].isin(['2PT', '3PT'])].copy()
    
    # Create distance bins for the model
    bins = [0, 50, 100, 150, 200, 300, 400, 500, 700, 1000]
    labels = ['0-50', '50-100', '100-150', '150-200', '200-300', '300-400', '400-500', '500-700', '700+']
    fg_shots['DIST_BIN'] = pd.cut(fg_shots['DIST'], bins=bins, labels=labels, right=False)
    
    # Calculate xFG% per zone + distance bin + shot type
    xfg_table = fg_shots.groupby(['ZONE', 'SHOT_TYPE', 'DIST_BIN']).agg(
        xFG=('MADE', 'mean'),
        COUNT=('MADE', 'count')
    ).reset_index()
    
    # Also calculate a simpler fallback: per zone + shot type
    xfg_zone = fg_shots.groupby(['ZONE', 'SHOT_TYPE']).agg(
        xFG=('MADE', 'mean'),
        COUNT=('MADE', 'count')
    ).reset_index()
    
    # And per shot type overall as last fallback
    xfg_type = fg_shots.groupby('SHOT_TYPE').agg(
        xFG=('MADE', 'mean'),
        COUNT=('MADE', 'count')
    ).reset_index()
    
    print(f"  xFG% Model built from {len(fg_shots)} field goals")
    print(f"  Overall 2PT xFG%: {xfg_type[xfg_type['SHOT_TYPE']=='2PT']['xFG'].values[0]*100:.1f}%")
    print(f"  Overall 3PT xFG%: {xfg_type[xfg_type['SHOT_TYPE']=='3PT']['xFG'].values[0]*100:.1f}%")
    
    return xfg_table, xfg_zone, xfg_type, fg_shots


def lookup_xfg(zone, shot_type, dist_bin, xfg_table, xfg_zone, xfg_type):
    """Look up the xFG% for a given shot, with fallbacks."""
    # Try zone + type + distance
    match = xfg_table[(xfg_table['ZONE'] == zone) & 
                       (xfg_table['SHOT_TYPE'] == shot_type) & 
                       (xfg_table['DIST_BIN'] == dist_bin)]
    if not match.empty and match.iloc[0]['COUNT'] >= 10:
        return match.iloc[0]['xFG']
    
    # Fallback: zone + type
    match = xfg_zone[(xfg_zone['ZONE'] == zone) & (xfg_zone['SHOT_TYPE'] == shot_type)]
    if not match.empty:
        return match.iloc[0]['xFG']
    
    # Fallback: type only
    match = xfg_type[xfg_type['SHOT_TYPE'] == shot_type]
    if not match.empty:
        return match.iloc[0]['xFG']
    
    return 0.45  # League average fallback


# ======================================================================
# STAGE 2: Parse Assist Connections from PbP
# ======================================================================

def parse_assist_connections(pbp_df, team_code):
    """
    Extract all Passer → Scorer connections for a team.
    Handles both field goal assists and foul-drawn assists (FT).
    """
    pbp = pbp_df[pbp_df['Gamecode'].isin(
        pbp_df[pbp_df['CODETEAM'] == team_code]['Gamecode'].unique()
    )].copy()
    pbp = pbp.sort_values(['Gamecode', 'NUMBEROFPLAY']).reset_index(drop=True)
    
    connections = []
    
    for i in range(len(pbp)):
        row = pbp.iloc[i]
        if str(row['PLAYTYPE']).strip() != 'AS':
            continue
        if str(row['CODETEAM']).strip() != team_code:
            continue
            
        passer = str(row['PLAYER']).strip()
        gc = row['Gamecode']
        nop = row['NUMBEROFPLAY']
        
        # Look backwards (1-3 events) for the scoring event
        scorer = None
        shot_type = None
        is_ft_assist = False
        
        for j in range(1, 5):
            if i - j < 0:
                break
            prev = pbp.iloc[i - j]
            if prev['Gamecode'] != gc:
                break
            prev_type = str(prev['PLAYTYPE']).strip()
            prev_team = str(prev['CODETEAM']).strip()
            
            if prev_team == team_code:
                if prev_type in ('2FGM', '3FGM'):
                    scorer = str(prev['PLAYER']).strip()
                    shot_type = '2PT' if prev_type == '2FGM' else '3PT'
                    break
                elif prev_type in ('FTM', 'FTA'):
                    scorer = str(prev['PLAYER']).strip()
                    shot_type = 'FT'
                    is_ft_assist = True
                    break
        
        if scorer and scorer != passer:
            connections.append({
                'Gamecode': gc,
                'NumberOfPlay': nop,
                'Passer': passer,
                'Scorer': scorer,
                'ShotType': shot_type,
                'IsFTAssist': is_ft_assist,
            })
    
    print(f"  Found {len(connections)} assist connections for {team_code}")
    ft_count = sum(1 for c in connections if c['IsFTAssist'])
    print(f"    Field Goal assists: {len(connections) - ft_count}")
    print(f"    Free Throw assists: {ft_count}")
    
    return connections


# ======================================================================
# STAGE 3: Merge Assists with xFG% and Shot Coordinates
# ======================================================================

def merge_connections_with_xfg(connections, shots_df, xfg_table, xfg_zone, xfg_type, team_code):
    """
    For each assist connection, find the corresponding shot in shot_data
    and assign its xFG%.
    """
    team_shots = shots_df[shots_df['TEAM'] == team_code].copy()
    
    # Pre-compute distance bins for all shots
    team_shots['DIST'] = np.sqrt(
        pd.to_numeric(team_shots['COORD_X'], errors='coerce')**2 + 
        pd.to_numeric(team_shots['COORD_Y'], errors='coerce')**2
    )
    bins = [0, 50, 100, 150, 200, 300, 400, 500, 700, 1000]
    labels = ['0-50', '50-100', '100-150', '150-200', '200-300', '300-400', '400-500', '500-700', '700+']
    team_shots['DIST_BIN'] = pd.cut(team_shots['DIST'], bins=bins, labels=labels, right=False)
    
    team_shots['SHOT_TYPE'] = team_shots['ACTION'].apply(
        lambda x: '3PT' if 'Three' in str(x) else ('2PT' if 'Two' in str(x) else 'FT')
    )
    
    enriched = []
    matched = 0
    
    for conn in connections:
        xfg = None
        
        if conn['IsFTAssist']:
            # FT assists: assign league average FT% as xFG
            xfg = 0.75
        else:
            # Try to match with shot_data by gamecode + player + shot type
            game_shots = team_shots[
                (team_shots['Gamecode'] == conn['Gamecode']) & 
                (team_shots['PLAYER'] == conn['Scorer'])
            ]
            
            # Filter by shot type (made shots only for assists)
            action_type = 'Two Pointer' if conn['ShotType'] == '2PT' else 'Three Pointer'
            made_shots = game_shots[
                (game_shots['ACTION'].str.contains(action_type, na=False)) & 
                (pd.to_numeric(game_shots['POINTS'], errors='coerce') > 0)
            ]
            
            if not made_shots.empty:
                # Take the closest shot by NUM_ANOT
                shot = made_shots.iloc[0]  # First made shot of this type
                zone = shot.get('ZONE', '')
                shot_type = conn['ShotType']
                dist_bin = shot.get('DIST_BIN', '200-300')
                xfg = lookup_xfg(zone, shot_type, dist_bin, xfg_table, xfg_zone, xfg_type)
                matched += 1
            else:
                # Fallback: use shot type average
                xfg = lookup_xfg('', conn['ShotType'], '', xfg_table, xfg_zone, xfg_type)
        
        enriched.append({
            **conn,
            'xFG': xfg,
        })
    
    print(f"  Matched {matched}/{len(connections)} assists with shot coordinates")
    return enriched


# ======================================================================
# MAIN: Build the network for a team
# ======================================================================

def build_network(team_code):
    print(f"\n{'='*60}")
    print(f"  SHOT CREATION NETWORK — {team_code}")
    print(f"{'='*60}")
    
    # Load data
    shots_df = pd.read_csv('shot_data_2025_2025.csv')
    pbp_df = pd.read_csv('pbp_2025.csv')
    
    # Stage 1: Build xFG model
    print("\n  [Stage 1] Building xFG% model...")
    xfg_table, xfg_zone, xfg_type, fg_shots = build_xfg_model(shots_df)
    
    # Stage 2: Parse assist connections
    print(f"\n  [Stage 2] Parsing assist connections for {team_code}...")
    connections = parse_assist_connections(pbp_df, team_code)
    
    # Stage 3: Merge with xFG
    print(f"\n  [Stage 3] Merging with shot quality...")
    enriched = merge_connections_with_xfg(connections, shots_df, xfg_table, xfg_zone, xfg_type, team_code)
    
    # Aggregate: Passer → Scorer network edges
    edge_data = {}
    for conn in enriched:
        key = (conn['Passer'], conn['Scorer'])
        if key not in edge_data:
            edge_data[key] = {'count': 0, 'xfg_sum': 0, 'shot_types': []}
        edge_data[key]['count'] += 1
        edge_data[key]['xfg_sum'] += conn['xFG'] if conn['xFG'] else 0
        edge_data[key]['shot_types'].append(conn['ShotType'])
    
    # Build edges list
    edges = []
    for (passer, scorer), data in edge_data.items():
        avg_xfg = data['xfg_sum'] / data['count'] if data['count'] > 0 else 0
        edges.append({
            'Passer': passer,
            'Scorer': scorer,
            'Assists': data['count'],
            'AvgXFG': round(avg_xfg * 100, 1),
            'ThreePT': data['shot_types'].count('3PT'),
            'TwoPT': data['shot_types'].count('2PT'),
            'FT': data['shot_types'].count('FT'),
        })
    
    edges.sort(key=lambda x: -x['Assists'])
    
    # Node stats
    passer_stats = {}
    scorer_stats = {}
    for e in edges:
        p = e['Passer']
        s = e['Scorer']
        if p not in passer_stats:
            passer_stats[p] = {'total_assists': 0, 'avg_xfg_created': []}
        passer_stats[p]['total_assists'] += e['Assists']
        passer_stats[p]['avg_xfg_created'].append((e['AvgXFG'], e['Assists']))
        
        if s not in scorer_stats:
            scorer_stats[s] = {'total_assisted': 0}
        scorer_stats[s]['total_assisted'] += e['Assists']
    
    # Calculate weighted avg xFG created per passer
    for p, stats in passer_stats.items():
        total_w = sum(w for _, w in stats['avg_xfg_created'])
        if total_w > 0:
            stats['weighted_xfg'] = round(sum(v*w for v,w in stats['avg_xfg_created']) / total_w, 1)
        else:
            stats['weighted_xfg'] = 0
    
    # Print top connections
    print(f"\n  --- Top 15 Assist Connections ---")
    print(f"  {'Passer':<22} {'Scorer':<22} {'AST':>4} {'xFG%':>6} {'2PT':>4} {'3PT':>4}")
    print(f"  {'-'*66}")
    for e in edges[:15]:
        print(f"  {e['Passer']:<22} {e['Scorer']:<22} {e['Assists']:>4} {e['AvgXFG']:>5.1f}% {e['TwoPT']:>4} {e['ThreePT']:>4}")
    
    # Print top shot creators
    print(f"\n  --- Top Shot Creators (by xFG% generated) ---")
    creators = sorted(passer_stats.items(), key=lambda x: -x[1]['total_assists'])
    print(f"  {'Player':<25} {'Total AST':>9} {'Avg xFG%':>9}")
    print(f"  {'-'*45}")
    for p, stats in creators[:10]:
        print(f"  {p:<25} {stats['total_assists']:>9} {stats['weighted_xfg']:>8.1f}%")
    
    # Save
    result = {
        'team': team_code,
        'edges': edges,
        'passer_stats': {p: {'total_assists': s['total_assists'], 'weighted_xfg': s['weighted_xfg']} 
                         for p, s in passer_stats.items()},
        'scorer_stats': scorer_stats,
    }
    
    output_file = f'shot_network_{team_code}.json'
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=4)
    print(f"\n  Saved to {output_file}")
    
    return result


def main():
    teams_to_analyze = ['OLY', 'PAM', 'PAN', 'MAD', 'MCO', 'MUN', 'BAR', 'ZAL', 'TEL']
    for team in teams_to_analyze:
        try:
            build_network(team)
        except Exception as e:
            print(f"Error processing {team}: {e}")

if __name__ == '__main__':
    main()
