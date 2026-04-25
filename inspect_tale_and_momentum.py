"""
Quick sanity check for Tale of the Tape + Series Momentum data.
Run after `python refresh_all.py --no-fetch` to print a summary
of every series entry.
"""
import json

with open('docs/data/current/dashboard.json', encoding='utf-8') as f:
    d = json.load(f)

print(f"Round: {d.get('round')}")
print()

for slot in ('qf1', 'qf2', 'qf3', 'qf4', 'sf1', 'sf2', 'final'):
    s = d['series'].get(slot) or {}
    hi = (s.get('high_seed') or {}).get('team') or '?'
    lo = (s.get('low_seed') or {}).get('team') or '?'
    print(f"=== {slot}: {hi} vs {lo} ({s.get('status')}) ===")

    tot = s.get('tale_of_the_tape') or {}
    rows = tot.get('rows') or []
    print(f"  rows: {len(rows)}")
    for r in rows:
        better = ''
        if r.get('lower_is_better'):
            better = ' (lower better)'
        print(f"    {r['label']:<18s}  {r['high']:>7}  vs  {r['low']:<7}{better}")

    edges = tot.get('edges') or []
    print(f"  edges: {len(edges)}")
    for e in edges:
        print(f"    [{e['type']:<10s}] favor={str(e['favor']):<5s} {e['text']}")

    m = s.get('momentum')
    if m:
        cps = m.get('checkpoints') or []
        bs = m.get('biggest_swing') or {}
        print(f"  momentum: {len(cps)} checkpoints, biggest swing G{bs.get('game_num')} {bs.get('delta_pct')}% to {bs.get('shifted_to')}")
    else:
        print(f"  momentum: (none — no games played)")
    print()
