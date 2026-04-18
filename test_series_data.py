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
