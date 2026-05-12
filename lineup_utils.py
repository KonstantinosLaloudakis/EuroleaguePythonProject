import ast
import pandas as pd
import numpy as np

FGA_TYPES = {'2FGM', '2FGA', '3FGM', '3FGA'}
TO_TYPES = {'TO'}
FTA_TYPES = {'FTM', 'FTA'}
OREB_TYPES = {'O'}


def parse_lineup(val):
    """Parse a lineup column value into a sorted tuple of player names."""
    if pd.isna(val):
        return None
    try:
        players = ast.literal_eval(val) if isinstance(val, str) else val
        if isinstance(players, list) and len(players) == 5 and len(set(players)) == 5:
            return tuple(sorted(players))
    except Exception:
        pass
    return None


def extract_stints(game_df, lineup_col_a, lineup_col_b):
    """
    Extract stints from a single game's play-by-play data.
    A stint = contiguous stretch where the same 10 players are on court.
    Returns list of stint dicts with lineup, points, and possession info.
    """
    team_a = lineup_col_a.replace('Lineup_', '')
    team_b = lineup_col_b.replace('Lineup_', '')

    game_df = game_df.sort_values('NUMBEROFPLAY').copy()

    # Forward-fill and clean scores
    for col in ['POINTS_A', 'POINTS_B']:
        if col in game_df.columns:
            game_df[col] = pd.to_numeric(game_df[col], errors='coerce')
            game_df[col] = game_df[col].ffill().fillna(0)

    stints = []
    prev_key = None
    cur_a = None
    cur_b = None
    start_score_a = 0.0
    start_score_b = 0.0
    last_a = 0.0
    last_b = 0.0
    stint_fga = 0
    stint_fta = 0
    stint_to = 0
    stint_oreb = 0

    for _, row in game_df.iterrows():
        la = parse_lineup(row.get(lineup_col_a))
        lb = parse_lineup(row.get(lineup_col_b))

        if la is None or lb is None:
            continue

        key = (la, lb)

        # Track running score
        sa = row.get('POINTS_A', np.nan)
        sb = row.get('POINTS_B', np.nan)
        if pd.notna(sa):
            last_a = float(sa)
        if pd.notna(sb):
            last_b = float(sb)

        if key != prev_key:
            # Flush previous stint
            if prev_key is not None:
                poss = stint_fga + 0.44 * stint_fta + stint_to - stint_oreb
                if poss >= 1:
                    stints.append({
                        'lineup_a': cur_a,
                        'lineup_b': cur_b,
                        'team_a': team_a,
                        'team_b': team_b,
                        'pts_a': last_a - start_score_a,
                        'pts_b': last_b - start_score_b,
                        'poss': max(poss, 1),
                    })

            # Start new stint
            prev_key = key
            cur_a, cur_b = la, lb
            start_score_a = last_a
            start_score_b = last_b
            stint_fga = 0
            stint_fta = 0
            stint_to = 0
            stint_oreb = 0

        # Count possession components
        pt = row.get('PLAYTYPE', '')
        if pt in FGA_TYPES:
            stint_fga += 1
        elif pt in FTA_TYPES:
            stint_fta += 1
        elif pt in TO_TYPES:
            stint_to += 1
        elif pt in OREB_TYPES:
            stint_oreb += 1

    # Final stint
    if prev_key is not None:
        poss = stint_fga + 0.44 * stint_fta + stint_to - stint_oreb
        if poss >= 1:
            stints.append({
                'lineup_a': cur_a,
                'lineup_b': cur_b,
                'team_a': team_a,
                'team_b': team_b,
                'pts_a': last_a - start_score_a,
                'pts_b': last_b - start_score_b,
                'poss': max(poss, 1),
            })

    return stints
