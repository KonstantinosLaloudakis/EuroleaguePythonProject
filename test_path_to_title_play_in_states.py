"""
Verifies compute_path_to_title handles every play-in phase correctly, including
the edge case where Game A loser / Game B winner are still alive waiting for
Game C. Extracts the nested function from export_dashboard_data.py via AST.
"""
import ast
import os
import random

_here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_here, 'export_dashboard_data.py'), 'r', encoding='utf-8') as f:
    src = f.read()

tree = ast.parse(src)
main_fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
cpt_fn = next(n for n in ast.walk(main_fn) if isinstance(n, ast.FunctionDef) and n.name == 'compute_path_to_title')

ns = {}
exec(ast.unparse(cpt_fn), ns)
compute_path_to_title = ns['compute_path_to_title']

# 10 synthetic teams seeded in order
seeded = [{'team': f'T{i+1:02d}'} for i in range(10)]
SEEDS = [t['team'] for t in seeded]

# Synthetic matchup probs: higher seed always favored 60% at home / 55% away / 55% neutral
matchup_probs = {}
for i, ta in enumerate(SEEDS):
    matchup_probs[ta] = {}
    for j, tb in enumerate(SEEDS):
        if i == j:
            continue
        if i < j:  # ta is higher seed
            matchup_probs[ta][tb] = {'home': 0.65, 'away': 0.55, 'neutral': 0.58}
        else:
            matchup_probs[ta][tb] = {'home': 0.45, 'away': 0.35, 'neutral': 0.42}

def find(result, team):
    return next(e for e in result if e['team'] == team)

def pi_round_n(entry, n):
    return next(r for r in entry['rounds'] if r['round'] == f'play_in_{n}')

def run(playoff_results, label):
    random.seed(42)
    result = compute_path_to_title(playoff_results, matchup_probs, seeded, n_sims=2000)
    print(f'\n=== {label} ===')
    for code in SEEDS[6:10]:
        e = find(result, code)
        r1 = pi_round_n(e, 1)
        r2 = pi_round_n(e, 2)
        print(f'  {code}  status={e["status"]:<10}  pi1={r1}  pi2={r2}')
    return result

# --- State 1: No games played (pre-play-in, current live state) ---
r1 = run(None, 'Pre-play-in (nothing played)')
for code in SEEDS[6:10]:
    e = find(r1, code)
    assert e['status'] == 'alive'
    pi1 = pi_round_n(e, 1)
    pi2 = pi_round_n(e, 2)
    assert pi1['status'] == 'upcoming', f'{code} play_in_1 should be upcoming, got {pi1["status"]}'
    assert len(pi1['branches']) == 1, f'{code} play_in_1 should have 1 branch, got {pi1["branches"]}'
    assert pi2['status'] == 'upcoming', f'{code} play_in_2 should be upcoming, got {pi2["status"]}'
    assert pi2['reach_prob'] < 100, f'{code} play_in_2 reach should be < 100, got {pi2["reach_prob"]}'
    # Seeds 7/8 face potential Game C opps T09/T10; seeds 9/10 face T07/T08
    expected_opps = {'T09', 'T10'} if code in ('T07', 'T08') else {'T07', 'T08'}
    branch_opps = {b['opponent'] for b in pi2['branches']}
    assert branch_opps == expected_opps, f'{code} play_in_2 branches should be {expected_opps}, got {branch_opps}'

# --- State 2: Game A done (T07 beat T08), Game B/C pending ---
pr2 = {
    'play_in': {
        'game_a': {'home': 'T07', 'away': 'T08', 'winner': 'T07'},
        'game_b': None,
        'game_c': None,
    },
    'qf': {},
    'sf': {},
    'final': {},
}
r2 = run(pr2, 'Game A done (T07 beat T08), B/C pending')
t07 = find(r2, 'T07')
t07_pi1 = pi_round_n(t07, 1); t07_pi2 = pi_round_n(t07, 2)
assert t07_pi1['status'] == 'completed' and t07_pi1['actual_result'] == 'won' and t07_pi1['actual_opponent'] == 'T08'
assert t07_pi2['status'] == 'unreached', f'T07 play_in_2 should be unreached, got {t07_pi2}'
assert t07['status'] == 'alive'

t08 = find(r2, 'T08')
t08_pi1 = pi_round_n(t08, 1); t08_pi2 = pi_round_n(t08, 2)
assert t08_pi1['status'] == 'completed' and t08_pi1['actual_result'] == 'lost' and t08_pi1['actual_opponent'] == 'T07'
assert t08_pi2['status'] == 'upcoming' and t08_pi2['reach_prob'] == 100.0, f'T08 play_in_2 should be upcoming @ 100%, got {t08_pi2}'
assert t08['status'] == 'alive'
t08_opps = {b['opponent'] for b in t08_pi2['branches']}
assert t08_opps == {'T09', 'T10'}, f'T08 play_in_2 branches should be T09/T10, got {t08_opps}'

t09 = find(r2, 'T09')
t09_pi1 = pi_round_n(t09, 1); t09_pi2 = pi_round_n(t09, 2)
assert t09_pi1['status'] == 'upcoming' and len(t09_pi1['branches']) == 1 and t09_pi1['branches'][0]['opponent'] == 'T10'
assert t09_pi2['status'] == 'upcoming'
t09_pi2_opps = {b['opponent'] for b in t09_pi2['branches']}
assert t09_pi2_opps == {'T08'}, f'T09 play_in_2 branches should be just T08 (Game A resolved), got {t09_pi2_opps}'

t10 = find(r2, 'T10')
t10_pi1 = pi_round_n(t10, 1); t10_pi2 = pi_round_n(t10, 2)
assert t10_pi1['status'] == 'upcoming' and len(t10_pi1['branches']) == 1 and t10_pi1['branches'][0]['opponent'] == 'T09'
assert t10_pi2['status'] == 'upcoming'
t10_pi2_opps = {b['opponent'] for b in t10_pi2['branches']}
assert t10_pi2_opps == {'T08'}, f'T10 play_in_2 branches should be just T08, got {t10_pi2_opps}'

# --- State 3: Game A + B done, Game C pending ---
pr3 = {
    'play_in': {
        'game_a': {'home': 'T07', 'away': 'T08', 'winner': 'T07'},
        'game_b': {'home': 'T09', 'away': 'T10', 'winner': 'T09'},
        'game_c': None,
    },
    'qf': {},
    'sf': {},
    'final': {},
}
r3 = run(pr3, 'Game A + B done, C pending')

t07 = find(r3, 'T07')
assert pi_round_n(t07, 1)['status'] == 'completed' and pi_round_n(t07, 1)['actual_result'] == 'won'
assert pi_round_n(t07, 2)['status'] == 'unreached'
assert t07['status'] == 'alive'

t08 = find(r3, 'T08')
t08_pi1 = pi_round_n(t08, 1); t08_pi2 = pi_round_n(t08, 2)
assert t08_pi1['status'] == 'completed' and t08_pi1['actual_result'] == 'lost'
assert t08_pi2['status'] == 'upcoming' and t08_pi2['reach_prob'] == 100.0
assert len(t08_pi2['branches']) == 1 and t08_pi2['branches'][0]['opponent'] == 'T09', t08_pi2
assert t08['status'] == 'alive'

t09 = find(r3, 'T09')
t09_pi1 = pi_round_n(t09, 1); t09_pi2 = pi_round_n(t09, 2)
assert t09_pi1['status'] == 'completed' and t09_pi1['actual_result'] == 'won'
assert t09_pi2['status'] == 'upcoming' and t09_pi2['reach_prob'] == 100.0
assert len(t09_pi2['branches']) == 1 and t09_pi2['branches'][0]['opponent'] == 'T08', t09_pi2
assert t09['status'] == 'alive'

t10 = find(r3, 'T10')
t10_pi1 = pi_round_n(t10, 1); t10_pi2 = pi_round_n(t10, 2)
assert t10_pi1['status'] == 'completed' and t10_pi1['actual_result'] == 'lost'
assert t10_pi2['status'] == 'unreached'
assert t10['status'] == 'eliminated'

# --- State 4: All three play-in games done (T08 beat T09 in Game C) ---
pr4 = {
    'play_in': {
        'game_a': {'home': 'T07', 'away': 'T08', 'winner': 'T07'},
        'game_b': {'home': 'T09', 'away': 'T10', 'winner': 'T09'},
        'game_c': {'home': 'T08', 'away': 'T09', 'winner': 'T08'},
    },
    'qf': {},
    'sf': {},
    'final': {},
}
r4 = run(pr4, 'All play-in games done')

t07 = find(r4, 'T07')
assert pi_round_n(t07, 1)['status'] == 'completed' and pi_round_n(t07, 1)['actual_result'] == 'won'
assert pi_round_n(t07, 2)['status'] == 'unreached'
assert t07['status'] == 'alive'

t08 = find(r4, 'T08')
t08_pi1 = pi_round_n(t08, 1); t08_pi2 = pi_round_n(t08, 2)
assert t08_pi1['status'] == 'completed' and t08_pi1['actual_result'] == 'lost' and t08_pi1['actual_opponent'] == 'T07'
assert t08_pi2['status'] == 'completed' and t08_pi2['actual_result'] == 'won' and t08_pi2['actual_opponent'] == 'T09'
assert t08['status'] == 'alive'

t09 = find(r4, 'T09')
t09_pi1 = pi_round_n(t09, 1); t09_pi2 = pi_round_n(t09, 2)
assert t09_pi1['status'] == 'completed' and t09_pi1['actual_result'] == 'won' and t09_pi1['actual_opponent'] == 'T10'
assert t09_pi2['status'] == 'completed' and t09_pi2['actual_result'] == 'lost' and t09_pi2['actual_opponent'] == 'T08'
assert t09['status'] == 'eliminated'

t10 = find(r4, 'T10')
assert pi_round_n(t10, 1)['status'] == 'completed' and pi_round_n(t10, 1)['actual_result'] == 'lost'
assert pi_round_n(t10, 2)['status'] == 'unreached'
assert t10['status'] == 'eliminated'

print('\nAll 4 state assertions passed.')
