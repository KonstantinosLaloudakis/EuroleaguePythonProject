"""
Game Control Index (GCI) — How teams win, not just that they win.

Computes per-game control metrics from Win Probability trajectory data,
aggregates into team season profiles, and generates storylines.

Usage:
    python calculate_gci.py
"""

import json
import os
import math
import statistics


SEASON = "2025"
WP_DATA_DIR = os.path.join("docs", "data", SEASON)
GAME_RESULTS_PATH = "mvp_game_results.json"


def load_game_results():
    """Load game metadata: teams, scores, winner per gamecode."""
    with open(GAME_RESULTS_PATH, 'r', encoding='utf-8') as f:
        raw = json.load(f)
    games = {}
    for g in raw:
        gc = g['GameCode']
        if g.get('Winner', 'UNKNOWN') == 'UNKNOWN':
            continue
        games[gc] = {
            'home': g['LocalTeam'],
            'away': g['RoadTeam'],
            'home_score': int(g['LocalScore']),
            'away_score': int(g['RoadScore']),
            'winner': g['Winner'],
        }
    return games


def load_wp_timeline(gamecode):
    """Load WP replay timeline for a single game. Returns list of play dicts or None."""
    path = os.path.join(WP_DATA_DIR, f"{gamecode}.json")
    if not os.path.exists(path):
        return None, None, None
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('timeline', []), data.get('ta'), data.get('tb')


def compute_game_metrics(timeline, winner_is_home):
    """
    Compute GCI sub-metrics from a WP timeline.

    Args:
        timeline: list of dicts with keys {e, s, a, b, w, p, d}
                  w = WP for home team (0.0 to 1.0)
                  s = seconds remaining (2400 -> 0)
                  p = period (1-4 regulation, 5+ OT)
        winner_is_home: True if home team won

    Returns:
        dict with per-game metrics, or None if insufficient data.
    """
    if not timeline or len(timeline) < 3:
        return None

    wp_values = [play['w'] for play in timeline]

    # 1. Dominance Score: mean(WP_home - 0.5)
    dominance = sum(wp - 0.5 for wp in wp_values) / len(wp_values)

    # 2. Control Duration: % of plays where the team had WP > 0.6
    #    Computed from BOTH perspectives so each team gets its own value
    control_home = sum(1 for wp in wp_values if wp > 0.6) / len(wp_values)
    control_away = sum(1 for wp in wp_values if wp < 0.4) / len(wp_values)

    # 3. Drama Index: total variation of WP curve
    drama = sum(abs(wp_values[i + 1] - wp_values[i]) for i in range(len(wp_values) - 1))

    # 4. Comeback Magnitude: 1.0 - min(winner_WP)
    if winner_is_home:
        comeback = 1.0 - min(wp_values)
    else:
        comeback = max(wp_values)  # = 1 - min(1-w) = max(w)

    # 5. Crunch-Time Swing: WP change in final 5 minutes (s <= 300)
    pre_crunch = [p for p in timeline if p['s'] > 300]
    crunch_plays = [p for p in timeline if p['s'] <= 300]
    if pre_crunch and crunch_plays:
        wp_at_5min = pre_crunch[-1]['w']
        wp_final = timeline[-1]['w']
        crunch_home = wp_final - wp_at_5min
        crunch_away = -crunch_home
    else:
        crunch_home = 0.0
        crunch_away = 0.0

    # 6. Killer Instinct: avg WP delta in Q4+ when leading with WP > 0.6
    q4_plays = [p for p in timeline if p['p'] >= 4]
    killer_home_deltas = []
    killer_away_deltas = []
    for i in range(len(q4_plays) - 1):
        wp_now = q4_plays[i]['w']
        wp_next = q4_plays[i + 1]['w']
        if wp_now > 0.6:
            killer_home_deltas.append(wp_next - wp_now)
        if wp_now < 0.4:
            killer_away_deltas.append(wp_now - wp_next)

    killer_home = statistics.mean(killer_home_deltas) if killer_home_deltas else 0.0
    killer_away = statistics.mean(killer_away_deltas) if killer_away_deltas else 0.0

    return {
        'dominance': round(dominance, 4),
        'control_home': round(control_home, 4),
        'control_away': round(control_away, 4),
        'drama': round(drama, 4),
        'comeback': round(comeback, 4),
        'crunch_home': round(crunch_home, 4),
        'crunch_away': round(crunch_away, 4),
        'killer_home': round(killer_home, 4),
        'killer_away': round(killer_away, 4),
    }


def extract_wp_curve(timeline, max_points=40):
    """Extract a condensed WP curve for SVG rendering. Returns list of [pct_elapsed, wp] pairs."""
    if not timeline:
        return []
    total_time = timeline[0]['s']
    if total_time <= 0:
        total_time = 2400
    curve = []
    for play in timeline:
        elapsed_pct = round(1.0 - play['s'] / total_time, 4)
        curve.append([elapsed_pct, round(play['w'], 4)])
    if len(curve) > max_points:
        step = len(curve) / max_points
        curve = [curve[int(i * step)] for i in range(max_points)]
        last = [1.0, round(timeline[-1]['w'], 4)]
        if curve[-1] != last:
            curve.append(last)
    return curve
