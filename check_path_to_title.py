"""Quick sanity check for compute_path_to_title."""
import json, os, sys

# Load export_dashboard_data as a module so we can reach its inner functions.
# Simplest: run export and inspect dashboard.json instead.
dash_path = os.path.join('docs', 'data', 'current', 'dashboard.json')
with open(dash_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

path = data.get('path_to_title')
assert path is not None, "path_to_title key missing from dashboard.json"
assert isinstance(path, list), f"path_to_title must be a list, got {type(path)}"

if not path:
    print("path_to_title is empty (no playoff-eligible teams). This is expected pre-playoffs when Monte Carlo has not run.")
    sys.exit(0)

assert len(path) == 10, f"Expected 10 playoff-eligible teams, got {len(path)}"

for entry in path:
    assert 'team' in entry
    assert entry['status'] in ('alive', 'eliminated', 'champion')
    assert entry['eliminated_at'] in (None, 'play_in', 'qf', 'sf', 'final')
    assert isinstance(entry['championship_odds'], (int, float))
    assert 0 <= entry['championship_odds'] <= 100
    assert isinstance(entry['rounds'], list)
    assert len(entry['rounds']) == 4, f"{entry['team']} should have 4 rounds, got {len(entry['rounds'])}"
    for r in entry['rounds']:
        assert r['round'] in ('play_in', 'qf', 'sf', 'final')
        assert r['status'] in ('completed', 'in_progress', 'upcoming', 'unreached')
        if r['status'] == 'upcoming':
            assert 'reach_prob' in r and 'win_prob' in r and 'branches' in r
            for b in r['branches']:
                assert 'opponent' in b and 'reach_prob_for_opp' in b and 'win_prob_vs' in b

# Pre-playoff sanity: with no real results, seeds 1-6 should have play_in status=unreached
# and seeds 7-10 should have play_in status=upcoming
pre_playoff = not data.get('playoff_results')
if pre_playoff:
    by_team = {e['team']: e for e in path}
    seeded = data.get('teams', [])[:10]
    top6 = [t['team'] for t in seeded[:6]]
    bottom4 = [t['team'] for t in seeded[6:10]]
    for t in top6:
        e = by_team.get(t)
        if e:
            pi = next((r for r in e['rounds'] if r['round'] == 'play_in'), None)
            assert pi and pi['status'] == 'unreached', f"{t} should have play_in status=unreached"
    for t in bottom4:
        e = by_team.get(t)
        if e:
            pi = next((r for r in e['rounds'] if r['round'] == 'play_in'), None)
            assert pi and pi['status'] == 'upcoming', f"{t} should have play_in status=upcoming, got {pi}"

# Championship odds should sum close to 100 (small Monte Carlo noise)
total = sum(e['championship_odds'] for e in path)
assert 98.0 <= total <= 102.0, f"championship_odds across all teams should sum close to 100, got {total}"

print(f"OK — path_to_title has {len(path)} teams, sum of championship odds = {total:.1f}")
print("Top 3 by championship odds:")
for e in path[:3]:
    print(f"  {e['team']}: {e['championship_odds']}% ({e['status']})")
