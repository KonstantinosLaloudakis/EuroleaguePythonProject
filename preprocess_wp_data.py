"""
Pre-process PBP CSVs into compact JSON for the GitHub Pages WP Replay dashboard.
Reads data_cache/pbp_{year}.csv files and outputs:
  docs/data/seasons.json         — List of available seasons
  docs/data/{year}/games.json    — Game index for each season
  docs/data/{year}/{gc}.json     — Scoring timeline for each game
"""

import pandas as pd
import numpy as np
import json
import os
import math
import glob


def win_probability(margin, seconds_remaining, total_seconds=2400):
    if seconds_remaining <= 0:
        return 1.0 if margin > 0 else (0.0 if margin < 0 else 0.5)
    time_frac = seconds_remaining / total_seconds
    sigma = 11.0 * math.sqrt(time_frac)
    if sigma == 0:
        return 1.0 if margin > 0 else (0.0 if margin < 0 else 0.5)
    z = margin / sigma
    return 1.0 / (1.0 + math.exp(-0.8 * z))


def parse_marker_time(marker_str, period):
    if pd.isna(marker_str):
        return None
    try:
        parts = str(marker_str).split(':')
        minutes = int(parts[0])
        seconds = int(parts[1])
        period_seconds_left = minutes * 60 + seconds
        if period <= 4:
            remaining_periods = 4 - period
            total_remaining = period_seconds_left + remaining_periods * 600
        else:
            total_remaining = period_seconds_left
        return total_remaining
    except (ValueError, IndexError):
        return None


def detect_team_a(game, teams):
    """Auto-detect which team maps to POINTS_A."""
    scoring = game[game['POINTS_A'].notna() & game['CODETEAM'].isin(teams)]
    prev_a, prev_b = 0, 0
    for _, row in scoring.iterrows():
        try:
            a, b = int(float(row['POINTS_A'])), int(float(row['POINTS_B']))
        except (ValueError, TypeError):
            continue
        team = row['CODETEAM']
        if a > prev_a and b == prev_b:
            return team
        elif b > prev_b and a == prev_a:
            return [t for t in teams if t != team][0]
        prev_a, prev_b = a, b
    return teams[0]


def process_game(game_df, teams):
    """Process a single game into a scoring timeline."""
    team_a = detect_team_a(game_df, teams)
    team_b = [t for t in teams if t != team_a][0]

    timeline = []
    last_a, last_b = 0, 0

    for _, row in game_df.iterrows():
        pts_a = row.get('POINTS_A')
        pts_b = row.get('POINTS_B')
        if pd.isna(pts_a) or pd.isna(pts_b):
            continue
        try:
            pts_a, pts_b = int(float(pts_a)), int(float(pts_b))
        except (ValueError, TypeError):
            continue
            
        if pts_a == last_a and pts_b == last_b:
            continue

        period = int(row['PERIOD']) if pd.notna(row['PERIOD']) else 1
        secs = parse_marker_time(row.get('MARKERTIME'), period)
        if secs is None:
            continue

        elapsed = 2400 - secs
        margin_a = pts_a - pts_b
        wp_a = win_probability(margin_a, secs)

        player = str(row.get('PLAYER', '')) if pd.notna(row.get('PLAYER')) else ''
        team = str(row.get('CODETEAM', '')) if pd.notna(row.get('CODETEAM')) else ''
        play_info = str(row.get('PLAYINFO', '')) if pd.notna(row.get('PLAYINFO')) else ''
        desc = f"{player} ({team})" + (f" — {play_info}" if play_info else "")

        timeline.append({
            'e': round(elapsed, 1),      # elapsed seconds
            's': secs,                     # seconds remaining
            'a': pts_a,                    # team A score
            'b': pts_b,                    # team B score
            'w': round(wp_a, 4),           # WP for team A
            'p': period,                   # period
            'd': desc,                     # play description
        })

        last_a, last_b = pts_a, pts_b

    # Sort by elapsed to prevent backward jumps
    timeline.sort(key=lambda x: x['e'])

    # Add final buzzer
    final_wp = 1.0 if last_a > last_b else (0.0 if last_a < last_b else 0.5)
    timeline.append({
        'e': 2400, 's': 0, 'a': last_a, 'b': last_b,
        'w': final_wp, 'p': 4, 'd': 'Final Buzzer',
    })

    return timeline, team_a, team_b, last_a, last_b


def extract_advanced_stats(game_df, team_a, team_b):
    stats = {}
    
    # Calculate Quarter Margins
    try:
        q_scores = game_df.groupby('PERIOD')[['POINTS_A', 'POINTS_B']].max().reset_index()
        q_scores['Q_PTS_A'] = q_scores['POINTS_A'].diff().fillna(q_scores['POINTS_A'])
        q_scores['Q_PTS_B'] = q_scores['POINTS_B'].diff().fillna(q_scores['POINTS_B'])
        
        q_margins = []
        for _, row in q_scores.iterrows():
            q_margins.append({
                'p': int(row['PERIOD']),
                'a': int(row['Q_PTS_A']),
                'b': int(row['Q_PTS_B'])
            })
        stats['q'] = q_margins
    except:
        stats['q'] = []
        
    # Player Impact
    try:
        player_events = game_df[pd.notna(game_df['PLAYER'])].copy()
        impacts = []
        if not player_events.empty:
            for player, pdf in player_events.groupby('PLAYER'):
                pts = (len(pdf[pdf['PLAYTYPE'] == '2FGM']) * 2 + 
                       len(pdf[pdf['PLAYTYPE'] == '3FGM']) * 3 + 
                       len(pdf[pdf['PLAYTYPE'] == 'FTM']) * 1)
                
                hustle = (len(pdf[pdf['PLAYTYPE'] == 'D']) + 
                          len(pdf[pdf['PLAYTYPE'] == 'O']) + 
                          len(pdf[pdf['PLAYTYPE'] == 'AS']) + 
                          len(pdf[pdf['PLAYTYPE'] == 'ST']))
                          
                if pts > 0 or hustle > 0:
                    team = pdf['CODETEAM'].iloc[0]
                    name_parts = str(player).split(',')
                    clean_name = name_parts[0].title() if len(name_parts) > 0 else str(player)
                    impacts.append({'n': clean_name, 'p': pts, 'h': hustle, 't': team})
        stats['i'] = impacts
    except:
        stats['i'] = []
        
    # Scoring Runs
    try:
        def parse_marker(m_str, p):
            if pd.isna(m_str): return None
            try:
                mins, secs = map(int, str(m_str).split(':'))
                ps_left = mins * 60 + secs
                return ps_left + (4 - p) * 600 if p <= 4 else ps_left
            except: return None
            
        runs = []
        curr_team = None
        curr_pts = 0
        run_start = None
        last_a, last_b = 0, 0
        
        for _, row in game_df.sort_values('NUMBEROFPLAY').iterrows():
            pa, pb = row.get('POINTS_A'), row.get('POINTS_B')
            if pd.isna(pa) or pd.isna(pb): continue
            try: pa, pb = int(float(pa)), int(float(pb))
            except: continue
            
            if pa == last_a and pb == last_b: continue
            period = int(row['PERIOD']) if pd.notna(row['PERIOD']) else 1
            sf = parse_marker(row.get('MARKERTIME'), period)
            if sf is None: continue
            elapsed = 2400 - sf
            
            scoring_team = team_a if pa > last_a else team_b
            pts = (pa - last_a) if pa > last_a else (pb - last_b)
            
            if curr_team == scoring_team:
                curr_pts += pts
            else:
                if curr_pts >= 8:
                    runs.append({'t': curr_team, 'p': curr_pts, 'st': run_start, 'en': elapsed})
                curr_team = scoring_team
                curr_pts = pts
                run_start = elapsed
            last_a, last_b = pa, pb
            
        if curr_pts >= 8:
            runs.append({'t': curr_team, 'p': curr_pts, 'st': run_start, 'en': 2400})
            
        stats['r'] = runs
    except:
        stats['r'] = []
        
    return stats


def process_season(year):
    """Process one season's PBP data."""
    csv_path = f'data_cache/pbp_{year}.csv'
    if not os.path.exists(csv_path):
        print(f"  [SKIP] {csv_path} not found")
        return None

    print(f"  Processing season {year}-{str(year+1)[-2:]}...")
    df = pd.read_csv(csv_path, low_memory=False)

    # Get unique gamecodes
    gamecodes = sorted(df['Gamecode'].unique())
    games_index = []
    out_dir = f'docs/data/{year}'
    os.makedirs(out_dir, exist_ok=True)

    for gc in gamecodes:
        game = df[df['Gamecode'] == gc].sort_values('NUMBEROFPLAY')
        teams = [t for t in game['CODETEAM'].dropna().unique() if t and str(t).strip()]
        if len(teams) < 2:
            continue

        try:
            timeline, team_a, team_b, score_a, score_b = process_game(game, teams)
            adv = extract_advanced_stats(game, team_a, team_b)
            
            # Extract Round
            round_val = game['Round'].dropna().iloc[0] if not game['Round'].dropna().empty else "Unknown"
            
            # Extract Full Team Names
            ta_name = game[game['CODETEAM'] == team_a]['TEAM'].dropna().iloc[0] if not game[game['CODETEAM'] == team_a]['TEAM'].dropna().empty else team_a
            tb_name = game[game['CODETEAM'] == team_b]['TEAM'].dropna().iloc[0] if not game[game['CODETEAM'] == team_b]['TEAM'].dropna().empty else team_b

        except Exception as e:
            print(f"    Error on gamecode {gc}: {e}")
            continue

        if len(timeline) < 5:
            continue

        # Save game timeline
        game_file = os.path.join(out_dir, f'{gc}.json')
        with open(game_file, 'w') as f:
            json.dump({'ta': team_a, 'tb': team_b, 'timeline': timeline, 'adv': adv}, f,
                     separators=(',', ':'))

        games_index.append({
            'gc': int(gc),
            'rnd': int(round_val) if str(round_val).isdigit() else str(round_val),
            'ta': team_a,
            'ta_name': str(ta_name),
            'tb': team_b,
            'tb_name': str(tb_name),
            'sa': int(score_a),
            'sb': int(score_b),
        })

    # Save games index
    index_file = os.path.join(out_dir, 'games.json')
    with open(index_file, 'w') as f:
        json.dump(games_index, f, separators=(',', ':'))

    print(f"    Processed {len(games_index)} games for {year}")
    return {'season': year, 'label': f'{year}-{str(year+1)[-2:]}', 'count': len(games_index)}


def main():
    os.makedirs('docs/data', exist_ok=True)
    seasons_meta = []

    for year in range(2007, 2026):
        result = process_season(year)
        if result:
            seasons_meta.append(result)

    # Save seasons index
    with open('docs/data/seasons.json', 'w') as f:
        json.dump(seasons_meta, f, indent=2)

    print(f"\nDone! Processed {len(seasons_meta)} seasons.")
    print(f"Total games: {sum(s['count'] for s in seasons_meta)}")


if __name__ == '__main__':
    main()
