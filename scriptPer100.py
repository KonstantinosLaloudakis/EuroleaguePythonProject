
import json
from collections import defaultdict

with open('mvp_all_game_stats_2025.json') as f:
    games = json.load(f)

team_games = defaultdict(list)

for g in games:
    lp = g.get('local.players') or []
    rp = g.get('road.players') or []
    if not lp or not rp:
        continue
    lc = lp[0]['player']['club']['code']
    rc = rp[0]['player']['club']['code']
    gc = g.get('Gamecode') or g.get('GameCode') or 0

    # Road offense = local team's defense
    r_fga = (g.get('road.total.fieldGoalsAttempted2') or 0) + (g.get('road.total.fieldGoalsAttempted3') or 0)
    r_fta = g.get('road.total.freeThrowsAttempted') or 0
    r_to  = g.get('road.total.turnovers') or 0
    r_oreb = g.get('road.total.offensiveRebounds') or 0
    r_pts = g.get('road.total.points') or 0
    r_poss = r_fga + 0.44 * r_fta + r_to - r_oreb

    # Local offense = road team's defense
    l_fga = (g.get('local.total.fieldGoalsAttempted2') or 0) + (g.get('local.total.fieldGoalsAttempted3') or 0)
    l_fta = g.get('local.total.freeThrowsAttempted') or 0
    l_to  = g.get('local.total.turnovers') or 0
    l_oreb = g.get('local.total.offensiveRebounds') or 0
    l_pts = g.get('local.total.points') or 0
    l_poss = l_fga + 0.44 * l_fta + l_to - l_oreb

    if r_poss > 0:
        team_games[lc].append((gc, r_pts, r_poss))
    if l_poss > 0:
        team_games[rc].append((gc, l_pts, l_poss))

results = []
for team, glist in team_games.items():
    glist.sort(key=lambda x: x[0], reverse=True)  # sort by Gamecode descending
    last10 = glist[:10]
    total_pts = sum(x[1] for x in last10)
    total_poss = sum(x[2] for x in last10)
    drtg = (total_pts / total_poss) * 100 if total_poss > 0 else 0
    results.append((team, drtg, len(last10), total_pts, total_poss))

results.sort(key=lambda x: x[1])

print(f"{'#':<4} {'Team':<6} {'DRtg':>6} {'GP':>4} {'Pts Allowed':>12} {'Poss':>7}")
print('-' * 44)
for i, (team, drtg, gp, pts, poss) in enumerate(results, 1):
    print(f'{i:<4} {team:<6} {drtg:>6.1f} {gp:>4} {pts:>12.0f} {poss:>7.1f}')

