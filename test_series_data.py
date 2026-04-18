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
ns2 = {}
exec(ast.unparse(csd_fn), ns2)
compute_series_data = ns2['compute_series_data']

# Empty series_win_probs dict (not yet wired) - we test slot structure first
import pandas as pd
empty_games_df = pd.DataFrame(columns=['round', 'homecode', 'awaycode', 'homescore', 'awayscore', 'played'])

# --- Pre-playoff state ---
result = compute_series_data(None, matchup_probs, seeded, {}, empty_games_df)
assert isinstance(result, dict)
assert set(result.keys()) == {'qf1', 'qf2', 'qf3', 'qf4', 'sf1', 'sf2', 'final'}

qf1 = result['qf1']
assert qf1['id'] == 'qf1'
assert qf1['round'] == 'qf'
assert qf1['label'] == 'Quarterfinal 1'
assert qf1['format'] == 'best_of_5'
assert qf1['home_pattern'] == ['high', 'high', 'low', 'low', 'high']
assert qf1['high_seed'] == {'team': 'T01', 'seed': 1}
assert qf1['low_seed'] == {'team': 'T08', 'seed': 8}

qf2 = result['qf2']
assert qf2['high_seed'] == {'team': 'T02', 'seed': 2}
assert qf2['low_seed'] == {'team': 'T07', 'seed': 7}

qf3 = result['qf3']
assert qf3['high_seed'] == {'team': 'T03', 'seed': 3}
assert qf3['low_seed'] == {'team': 'T06', 'seed': 6}

qf4 = result['qf4']
assert qf4['high_seed'] == {'team': 'T04', 'seed': 4}
assert qf4['low_seed'] == {'team': 'T05', 'seed': 5}

# SF/Final slots start unresolved pre-playoff
sf1 = result['sf1']
assert sf1['id'] == 'sf1'
assert sf1['round'] == 'sf'
assert sf1['high_seed'] is None and sf1['low_seed'] is None

finals = result['final']
assert finals['round'] == 'final'
assert finals['high_seed'] is None and finals['low_seed'] is None

print('Task 2 assertions passed.')
