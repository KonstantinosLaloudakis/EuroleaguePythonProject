"""
Verifies compute_championship_odds returns per-series win probabilities
alongside championship odds. Extracts the nested function from
export_dashboard_data.py via AST.
"""
import ast
import os

_here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_here, 'export_dashboard_data.py'), 'r', encoding='utf-8') as f:
    src = f.read()

tree = ast.parse(src)
main_fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
cco_fn = next(n for n in ast.walk(main_fn) if isinstance(n, ast.FunctionDef) and n.name == 'compute_championship_odds')

ns = {}
exec(ast.unparse(cco_fn), ns)
compute_championship_odds = ns['compute_championship_odds']

# 10 synthetic teams, higher seed favored
seeded = [{'team': f'T{i+1:02d}'} for i in range(10)]
SEEDS = [t['team'] for t in seeded]
matchup_probs = {}
for i, ta in enumerate(SEEDS):
    matchup_probs[ta] = {}
    for j, tb in enumerate(SEEDS):
        if i == j:
            continue
        p_ta = 0.65 if i < j else 0.35
        matchup_probs[ta][tb] = {'home': p_ta, 'away': p_ta - 0.1, 'neutral': p_ta - 0.05}

result = compute_championship_odds(None, matchup_probs, seeded, n_sims=2000)

assert isinstance(result, dict), f'expected dict, got {type(result)}'
assert 'championship' in result, f'missing championship key: {result.keys()}'
assert 'series' in result, f'missing series key: {result.keys()}'

champ = result['championship']
assert isinstance(champ, dict)
for code in SEEDS:
    assert code in champ, f'missing {code} in championship'
    assert 0 <= champ[code] <= 100

series = result['series']
expected_slots = {'qf1', 'qf2', 'qf3', 'qf4', 'sf1', 'sf2', 'final'}
assert set(series.keys()) == expected_slots, f'unexpected slots: {series.keys()}'

# Every slot should have probs summing to ~100 across the teams that could reach it
for slot, probs in series.items():
    total = sum(probs.values())
    assert 99.0 <= total <= 101.0, f'{slot} probs sum to {total}: {probs}'

# Seed 1 should win qf1 most of the time
assert series['qf1'].get('T01', 0) > series['qf1'].get('T08', 0), \
    f'qf1 higher seed should win more: {series["qf1"]}'

print('Task 1 assertions passed.')

# ── Task 2: compute_series_data scaffolding ────────────────────────────────
csd_fn = next(n for n in ast.walk(main_fn) if isinstance(n, ast.FunctionDef) and n.name == 'compute_series_data')

# compute_series_data now references module-level helpers (build_momentum,
# build_tale_of_the_tape, compute_remaining_series_wp). Inject them into the
# exec namespace so the extracted function can resolve them at call time.
from export_dashboard_data import (
    build_momentum,
    build_tale_of_the_tape,
    compute_remaining_series_wp,
)
ns2 = {
    'build_momentum': build_momentum,
    'build_tale_of_the_tape': build_tale_of_the_tape,
    'compute_remaining_series_wp': compute_remaining_series_wp,
}
exec(ast.unparse(csd_fn), ns2)
compute_series_data = ns2['compute_series_data']

# Empty series_win_probs dict (not yet wired) - we test slot structure first
import pandas as pd
empty_games_df = pd.DataFrame(columns=['round', 'homecode', 'awaycode', 'homescore', 'awayscore', 'played'])

# Empty defaults for the new parameters added by the Tale of the Tape /
# Momentum work — the existing assertions don't depend on these outputs.
empty_teams_by_code = {}
empty_box_metrics = {}
empty_paint_share = {}

# --- Pre-playoff state ---
result = compute_series_data(None, matchup_probs, seeded, {}, empty_games_df,
                             empty_teams_by_code, empty_box_metrics, empty_paint_share)
assert isinstance(result, dict)
assert set(result.keys()) == {'qf1', 'qf2', 'qf3', 'qf4', 'sf1', 'sf2', 'final'}

qf1 = result['qf1']
assert qf1['id'] == 'qf1'
assert qf1['round'] == 'qf'
assert qf1['label'] == 'Quarterfinal 1'
assert qf1['format'] == 'best_of_5'
assert qf1['home_pattern'] == ['high', 'high', 'low', 'low', 'high']
assert qf1['high_seed'] == {'team': 'T01', 'seed': 1}
# Seed 8 comes from the play-in; pre-play-in, the low side must be unresolved.
assert qf1['low_seed'] is None
assert qf1['status'] == 'awaiting_teams'

qf2 = result['qf2']
assert qf2['high_seed'] == {'team': 'T02', 'seed': 2}
# Seed 7 also comes from the play-in.
assert qf2['low_seed'] is None
assert qf2['status'] == 'awaiting_teams'

# QF3 and QF4 are fully seeded from the regular-season standings, so they
# should be known even before the play-in resolves.
qf3 = result['qf3']
assert qf3['high_seed'] == {'team': 'T03', 'seed': 3}
assert qf3['low_seed'] == {'team': 'T06', 'seed': 6}
assert qf3['status'] == 'not_started'

qf4 = result['qf4']
assert qf4['high_seed'] == {'team': 'T04', 'seed': 4}
assert qf4['low_seed'] == {'team': 'T05', 'seed': 5}
assert qf4['status'] == 'not_started'

# SF/Final slots start unresolved pre-playoff
sf1 = result['sf1']
assert sf1['id'] == 'sf1'
assert sf1['round'] == 'sf'
assert sf1['high_seed'] is None and sf1['low_seed'] is None

finals = result['final']
assert finals['round'] == 'final'
assert finals['high_seed'] is None and finals['low_seed'] is None

print('Task 2 assertions passed.')

# ── Task 3: state + games ──────────────────────────────────────────────────

# Build a playoff_results with QF1 at 2-1 in favor of T01 (3 completed games)
# and qf2 swept 3-0 by T02
pr_state = {
    'play_in': {'game_a': None, 'game_b': None, 'game_c': None},
    'qf': {
        '1v8': {
            'higher_seed': 'T01', 'lower_seed': 'T08',
            'series': [2, 1],
            'winner': None,
            'games': [
                {'game_num': 1, 'date': '2026-04-21', 'home': 'T01', 'away': 'T08',
                 'home_score': 90, 'away_score': 75, 'winner': 'T01', 'gamecode': 401},
                {'game_num': 2, 'date': '2026-04-23', 'home': 'T01', 'away': 'T08',
                 'home_score': 80, 'away_score': 88, 'winner': 'T08', 'gamecode': 402},
                {'game_num': 3, 'date': '2026-04-26', 'home': 'T08', 'away': 'T01',
                 'home_score': 70, 'away_score': 85, 'winner': 'T01', 'gamecode': 403},
            ],
        },
        '2v7': {
            'higher_seed': 'T02', 'lower_seed': 'T07',
            'series': [3, 0],
            'winner': 'T02',
            'games': [
                {'game_num': 1, 'date': '2026-04-21', 'home': 'T02', 'away': 'T07',
                 'home_score': 95, 'away_score': 78, 'winner': 'T02', 'gamecode': 404},
                {'game_num': 2, 'date': '2026-04-23', 'home': 'T02', 'away': 'T07',
                 'home_score': 88, 'away_score': 85, 'winner': 'T02', 'gamecode': 405},
                {'game_num': 3, 'date': '2026-04-26', 'home': 'T07', 'away': 'T02',
                 'home_score': 79, 'away_score': 82, 'winner': 'T02', 'gamecode': 406},
            ],
        },
        '3v6': {'higher_seed': 'T03', 'lower_seed': 'T06', 'series': [0, 0], 'winner': None, 'games': []},
        '4v5': {'higher_seed': 'T04', 'lower_seed': 'T05', 'series': [0, 0], 'winner': None, 'games': []},
    },
    'sf': {'sf1': None, 'sf2': None},
    'final': {},
}

# Synthetic series_win_probs
swp = {
    'qf1': {'T01': 72.0, 'T08': 28.0},
    'qf2': {'T02': 100.0},   # completed
    'qf3': {'T03': 60.0, 'T06': 40.0},
    'qf4': {'T04': 55.0, 'T05': 45.0},
    'sf1': {'T01': 40.0, 'T04': 30.0, 'T05': 20.0, 'T08': 10.0},
    'sf2': {'T02': 50.0, 'T03': 30.0, 'T06': 20.0},
    'final': {'T01': 25.0, 'T02': 30.0, 'T03': 15.0, 'T04': 12.0, 'T05': 8.0, 'T06': 5.0, 'T08': 5.0},
}

result = compute_series_data(pr_state, matchup_probs, seeded, swp, empty_games_df,
                             empty_teams_by_code, empty_box_metrics, empty_paint_share)

# qf1: in progress, 2-1
qf1 = result['qf1']
assert qf1['status'] == 'in_progress', qf1['status']
assert qf1['wins'] == {'high': 2, 'low': 1}, qf1['wins']
assert qf1['winner'] is None
assert qf1['series_win_prob'] == {'high': 72.0, 'low': 28.0}, qf1['series_win_prob']

# 5 game entries total
assert len(qf1['games']) == 5
g1 = qf1['games'][0]
assert g1['status'] == 'completed'
assert g1['home'] == 'T01' and g1['away'] == 'T08'
assert g1['home_score'] == 90 and g1['away_score'] == 75
assert g1['winner'] == 'T01'
assert g1['gamecode'] == 401

g4 = qf1['games'][3]
assert g4['status'] == 'upcoming', g4['status']
assert g4['game_num'] == 4
assert g4['home'] == 'T08'   # home_pattern[3] = 'low' = T08
assert g4['away'] == 'T01'
assert 'pregame_wp' in g4
assert 'home' in g4['pregame_wp'] and 'away' in g4['pregame_wp']

# qf2: sweep, winner set, status completed
qf2 = result['qf2']
assert qf2['status'] == 'completed'
assert qf2['winner'] == 'T02'
assert qf2['wins'] == {'high': 3, 'low': 0}
assert qf2['series_win_prob'] == {'high': 100.0, 'low': 0.0}

# qf2 games: 3 completed, G4/G5 marked unnecessary (sweep)
assert len(qf2['games']) == 5
assert qf2['games'][3]['status'] == 'unnecessary'
assert qf2['games'][4]['status'] == 'unnecessary'

# qf3: not_started, all 5 upcoming
qf3 = result['qf3']
assert qf3['status'] == 'not_started'
assert qf3['winner'] is None
assert all(g['status'] == 'upcoming' for g in qf3['games'])

print('Task 3 assertions passed.')

# ── Task 4: RS H2H ─────────────────────────────────────────────────────────

# Build a synthetic games_df with 2 RS meetings between T01 and T08
rs_games = pd.DataFrame([
    {'round': 'RS', 'homecode': 'T01', 'awaycode': 'T08', 'homescore': 84,
     'awayscore': 79, 'played': True, 'gameday': 7},
    {'round': 'RS', 'homecode': 'T08', 'awaycode': 'T01', 'homescore': 91,
     'awayscore': 88, 'played': True, 'gameday': 22},
    {'round': 'RS', 'homecode': 'T02', 'awaycode': 'T07', 'homescore': 80,
     'awayscore': 75, 'played': True, 'gameday': 10},
    # T03/T06 have no RS meetings
])

# QF1/QF2 opponents depend on play-in results. Provide a playoff_results
# with the play-in resolved so T01/T08 and T02/T07 become the QF matchups.
pr_post_playin = {
    'play_in': {
        'game_a': {'winner': 'T07'},
        'game_b': None,
        'game_c': {'winner': 'T08'},
    },
    'qf': {
        '1v8': {'higher_seed': 'T01', 'lower_seed': 'T08', 'series': [0, 0], 'winner': None, 'games': []},
        '2v7': {'higher_seed': 'T02', 'lower_seed': 'T07', 'series': [0, 0], 'winner': None, 'games': []},
        '3v6': {'higher_seed': 'T03', 'lower_seed': 'T06', 'series': [0, 0], 'winner': None, 'games': []},
        '4v5': {'higher_seed': 'T04', 'lower_seed': 'T05', 'series': [0, 0], 'winner': None, 'games': []},
    },
    'sf': {'sf1': None, 'sf2': None},
    'final': {},
}

result = compute_series_data(pr_post_playin, matchup_probs, seeded, {}, rs_games,
                             empty_teams_by_code, empty_box_metrics, empty_paint_share)

qf1 = result['qf1']
assert len(qf1['rs_h2h']) == 2, f'expected 2 rs_h2h, got {len(qf1["rs_h2h"])}'
m0 = qf1['rs_h2h'][0]
assert m0['home'] == 'T01' and m0['away'] == 'T08'
assert m0['home_score'] == 84 and m0['away_score'] == 79
assert m0['winner'] == 'T01'
assert m0['round'] == 7

m1 = qf1['rs_h2h'][1]
assert m1['home'] == 'T08' and m1['away'] == 'T01'
assert m1['winner'] == 'T08'
assert m1['round'] == 22

# qf2: 1 meeting
qf2 = result['qf2']
assert len(qf2['rs_h2h']) == 1
assert qf2['rs_h2h'][0]['winner'] == 'T02'

# qf3: 0 meetings
qf3 = result['qf3']
assert qf3['rs_h2h'] == []

# SF/Final slots (unresolved seeds): no H2H
assert result['sf1']['rs_h2h'] == []

print('Task 4 assertions passed.')
