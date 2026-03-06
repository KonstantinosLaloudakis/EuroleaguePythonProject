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
            json.dump({'ta': team_a, 'tb': team_b, 'timeline': timeline}, f,
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
