"""
Verifies compute_path_to_title handles every play-in phase correctly, including
the edge case where Game A loser / Game B winner are still alive waiting for
Game C. Extracts the nested function from export_dashboard_data.py via AST.
"""
import ast
import random

with open('export_dashboard_data.py', 'r', encoding='utf-8') as f:
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

def pi_round(entry):
    return next(r for r in entry['rounds'] if r['round'] == 'play_in')

def run(playoff_results, label):
    random.seed(42)
    result = compute_path_to_title(playoff_results, matchup_probs, seeded, n_sims=2000)
    print(f'\n=== {label} ===')
    for code in SEEDS[6:10]:
        e = find(result, code)
        r = pi_round(e)
        print(f'  {code}  status={e["status"]:<10}  play_in={r}')
    return result

# --- State 1: No games played (pre-play-in, current live state) ---
r1 = run(None, 'Pre-play-in (nothing played)')
for code in SEEDS[6:10]:
    r = pi_round(find(r1, code))
    assert r['status'] == 'upcoming', f'{code} should be upcoming, got {r["status"]}'
    assert find(r1, code)['status'] == 'alive'
    assert len(r['branches']) == 1

# --- State 2: Game A done (T07 beat T08), Game B/C pending ---
# Expected:
#   T07 (Game A winner) -> completed won, status alive (advances to QF)
#   T08 (Game A loser)  -> upcoming (waiting for Game C), status alive, NOT completed
#   T09, T10            -> upcoming (first game), alive
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
t07 = find(r2, 'T07'); t07_pi = pi_round(t07)
assert t07_pi['status'] == 'completed' and t07_pi['actual_result'] == 'won', f'T07 should be completed won: {t07_pi}'
assert t07['status'] == 'alive'
t08 = find(r2, 'T08'); t08_pi = pi_round(t08)
assert t08_pi['status'] == 'upcoming', f'T08 should still be upcoming (waiting for C), got {t08_pi}'
assert t08['status'] == 'alive', f'T08 should still be alive, got {t08["status"]}'
# T08's branches should include the potential Game B winners (T09 and/or T10) — NOT T07
branch_opps = {b['opponent'] for b in t08_pi['branches']}
assert 'T07' not in branch_opps, f'T08 should not face T07 again; branches: {t08_pi["branches"]}'
assert branch_opps & {'T09', 'T10'}, f'T08 should face Game B winner; branches: {t08_pi["branches"]}'

# --- State 3: Game A + B done, Game C pending ---
# T07 won A (advance), T08 lost A (waits for C), T09 won B (waits for C), T10 lost B (eliminated)
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
t07 = find(r3, 'T07'); assert pi_round(t07)['status'] == 'completed' and t07['status'] == 'alive'
t08 = find(r3, 'T08'); t08_pi = pi_round(t08)
assert t08_pi['status'] == 'upcoming' and t08['status'] == 'alive'
# T08's only possible Game C opp is T09 (deterministic now)
assert len(t08_pi['branches']) == 1 and t08_pi['branches'][0]['opponent'] == 'T09', t08_pi
t09 = find(r3, 'T09'); t09_pi = pi_round(t09)
assert t09_pi['status'] == 'upcoming' and t09['status'] == 'alive'
assert len(t09_pi['branches']) == 1 and t09_pi['branches'][0]['opponent'] == 'T08', t09_pi
t10 = find(r3, 'T10'); t10_pi = pi_round(t10)
assert t10_pi['status'] == 'completed' and t10_pi['actual_result'] == 'lost'
assert t10['status'] == 'eliminated'

# --- State 4: All three play-in games done ---
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
# T07: won A, advanced
assert find(r4, 'T07')['status'] == 'alive'
# T08: lost A but won C vs T09 → advanced
t08 = find(r4, 'T08'); t08_pi = pi_round(t08)
assert t08_pi['status'] == 'completed' and t08_pi['actual_result'] == 'won' and t08_pi['actual_opponent'] == 'T09'
assert t08['status'] == 'alive'
# T09: won B but lost C → eliminated
t09 = find(r4, 'T09'); t09_pi = pi_round(t09)
assert t09_pi['status'] == 'completed' and t09_pi['actual_result'] == 'lost' and t09_pi['actual_opponent'] == 'T08'
assert t09['status'] == 'eliminated'
# T10: lost B → eliminated
assert find(r4, 'T10')['status'] == 'eliminated'

print('\nAll 4 state assertions passed.')
