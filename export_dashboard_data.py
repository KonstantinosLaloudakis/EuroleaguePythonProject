"""
Export all season analytics data to docs/data/current/dashboard.json
for the Season Hub web page.

Usage:
    python export_dashboard_data.py

Reads from root dir JSON files; writes to docs/data/current/dashboard.json
"""

import json
import os
import glob
import re

# ── Team name mapping ────────────────────────────────────────────────────────
TEAM_NAMES = {
    'BER': 'ALBA Berlin',
    'IST': 'Anadolu Efes',
    'MCO': 'AS Monaco',
    'BAS': 'Baskonia',
    'RED': 'Crvena Zvezda',
    'MIL': 'EA7 Milan',
    'BAR': 'FC Barcelona',
    'MUN': 'Bayern Munich',
    'ULK': 'Fenerbahce',
    'ASV': 'ASVEL',
    'TEL': 'Maccabi Tel Aviv',
    'OLY': 'Olympiacos',
    'PAN': 'Panathinaikos',
    'PAR': 'Partizan',
    'PRS': 'Paris Basketball',
    'MAD': 'Real Madrid',
    'PAM': 'Valencia Basket',
    'VIR': 'Virtus Bologna',
    'ZAL': 'Zalgiris',
    'DUB': 'Dubai Basketball',
    'HTA': 'Hapoel Tel Aviv',
}


def load_json(path):
    """Load JSON file, return None on failure."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"  [WARN] Could not load {path}: {e}")
        return None


def load_with_fallback(suffix, base_name, fallback_name=None):
    """Try loading base_name+suffix first, fall back to fallback_name or base_name."""
    if suffix:
        candidate = base_name.replace('.json', f'{suffix}.json')
        data = load_json(candidate)
        if data is not None:
            print(f"  Loaded: {candidate}")
            return data
    fallback = fallback_name or base_name
    data = load_json(fallback)
    if data is not None:
        print(f"  Loaded: {fallback}")
    return data


def parse_schedule_dates():
    """Parse official_schedule_2025.xml → {(homecode, awaycode): {'date': ..., 'time': ...}}."""
    dates = {}
    try:
        import xml.etree.ElementTree as ET
        tree = ET.parse('official_schedule_2025.xml')
        for item in tree.getroot().iter('item'):
            home = (item.findtext('homecode') or '').strip()
            away = (item.findtext('awaycode') or '').strip()
            date = (item.findtext('date') or '').strip()
            time = (item.findtext('startime') or '').strip()
            if home and away and date:
                dates[(home, away)] = {'date': date, 'time': time}
    except Exception as e:
        print(f"  [WARN] Could not parse schedule XML: {e}")
    return dates


def find_latest_oracle_forecast():
    """Scan for oracle_forecast_round_*_ml.json or oracle_forecast_round_*.json,
    pick highest round number. Returns (path, round_num) or (None, None)."""
    best_round = -1
    best_path = None

    # Prefer ML variants
    for pattern in ['oracle_forecast_round_*_ml.json', 'oracle_forecast_round_*.json']:
        for fpath in glob.glob(pattern):
            m = re.search(r'oracle_forecast_round_(\d+)', fpath)
            if m:
                rnum = int(m.group(1))
                if rnum > best_round:
                    best_round = rnum
                    best_path = fpath

    if best_path:
        print(f"  Latest oracle forecast: {best_path} (Round {best_round})")
    return best_path, best_round


def find_latest_player_forecast(oracle_round):
    """Find player forecast for the same round as oracle."""
    if oracle_round and oracle_round > 0:
        # Try ML variant first
        candidates = [
            f'player_forecast_round_{oracle_round}_ml.json',
            f'player_forecast_round_{oracle_round}.json',
        ]
        for c in candidates:
            if os.path.exists(c):
                print(f"  Loaded player forecast: {c}")
                return load_json(c)
    return None


def build_player_stats(mvp_data):
    """Aggregate per-player season averages from mvp_all_game_stats_2025.json."""
    from collections import defaultdict

    all_stats = load_json('mvp_all_game_stats_2025.json')
    if not all_stats:
        return []

    # Build rankings lookup by player name
    rankings_lookup = {}
    if mvp_data:
        for row in mvp_data:
            rankings_lookup[row.get('PlayerName', '')] = row

    agg = defaultdict(lambda: {
        'name': '', 'team': '', 'position': '',
        'pts': [], 'reb': [], 'ast': [], 'stl': [], 'to_': [], 'blk': [],
        'pir': [], 'fg2m': 0, 'fg2a': 0, 'fg3m': 0, 'fg3a': 0,
        'ftm': 0, 'fta': 0,
    })

    for game in all_stats:
        for side in ('local.players', 'road.players'):
            for entry in game.get(side, []):
                p = entry.get('player', {})
                s = entry.get('stats', {})
                code = p.get('person', {}).get('code', '')
                name = p.get('person', {}).get('name', '')
                team = p.get('club', {}).get('code', '')
                pos = p.get('positionName', '')
                if not code or not name:
                    continue
                # Skip DNPs (no minutes and no stats)
                if s.get('timePlayed', 0) == 0 and s.get('points', 0) == 0 and s.get('valuation', 0) == 0:
                    continue
                d = agg[code]
                d['name'] = name
                d['team'] = team
                d['position'] = pos
                d['pts'].append(s.get('points', 0))
                d['reb'].append(s.get('totalRebounds', 0))
                d['ast'].append(s.get('assistances', 0))
                d['stl'].append(s.get('steals', 0))
                d['to_'].append(s.get('turnovers', 0))
                d['blk'].append(s.get('blocksFavour', 0))
                d['pir'].append(s.get('valuation', 0))
                d['fg2m'] += s.get('fieldGoalsMade2', 0)
                d['fg2a'] += s.get('fieldGoalsAttempted2', 0)
                d['fg3m'] += s.get('fieldGoalsMade3', 0)
                d['fg3a'] += s.get('fieldGoalsAttempted3', 0)
                d['ftm'] += s.get('freeThrowsMade', 0)
                d['fta'] += s.get('freeThrowsAttempted', 0)

    def avg(lst): return round(sum(lst) / len(lst), 1) if lst else 0.0

    result = []
    for code, d in agg.items():
        gp = len(d['pts'])
        if gp < 5:
            continue
        fgm = d['fg2m'] + d['fg3m']
        fga = d['fg2a'] + d['fg3a']
        rnk = rankings_lookup.get(d['name'], {})
        result.append({
            'code': code,
            'name': d['name'],
            'team': d['team'],
            'position': d['position'],
            'gp': gp,
            'avg_pts': avg(d['pts']),
            'avg_reb': avg(d['reb']),
            'avg_ast': avg(d['ast']),
            'avg_stl': avg(d['stl']),
            'avg_to': avg(d['to_']),
            'avg_blk': avg(d['blk']),
            'avg_pir': avg(d['pir']),
            'fg_pct': round(fgm / fga * 100, 1) if fga > 0 else 0.0,
            'fg3_pct': round(d['fg3m'] / d['fg3a'] * 100, 1) if d['fg3a'] > 0 else 0.0,
            'ft_pct': round(d['ftm'] / d['fta'] * 100, 1) if d['fta'] > 0 else 0.0,
            'mvp_score': round(rnk.get('MVP_Score', 0.0), 1),
            'mvp_rank': rnk.get('MVP_Rank', 0),
            'wpa': round(rnk.get('WPA', 0.0), 1),
            'consistency': round(rnk.get('Consistency', 0.0), 3),
            'clutch_eff': round(rnk.get('ClutchEff', 0.0), 3),
        })

    result.sort(key=lambda x: -x['avg_pir'])
    return result


# ── Shot stats aggregation ────────────────────────────────────────────────
def build_shot_stats():
    """Aggregate shot data by zone for league, team, and player breakdowns."""
    import csv
    shot_file = glob.glob('shot_data_*_*.csv')
    if not shot_file:
        print("  No shot data CSV found — skipping shot stats.")
        return None
    shot_file = sorted(shot_file)[-1]  # latest
    print(f"\n--- Building shot stats from {shot_file} ---")

    from collections import defaultdict

    ZONES = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
    ZONE_NAMES = {
        'A': 'At Rim', 'B': 'Left Paint', 'C': 'Right Paint',
        'D': 'Left Mid', 'E': 'Right Mid', 'F': 'Left Extended',
        'G': 'Right Extended', 'H': 'Left 3PT', 'I': 'Right 3PT', 'J': 'Deep 3PT',
    }

    def new_zone(): return {'attempts': 0, 'makes': 0, 'pts': 0}

    league = {z: new_zone() for z in ZONES}
    teams = defaultdict(lambda: {z: new_zone() for z in ZONES})
    players = defaultdict(lambda: {'team': '', 'zones': {z: new_zone() for z in ZONES}, 'total_fga': 0})

    with open(shot_file, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            zone = row.get('ZONE', '').strip()
            if zone not in ZONES:
                continue
            action = row.get('ID_ACTION', '')
            if action == 'FTM':
                continue  # free throws don't have meaningful zone data
            team_code = row.get('TEAM', '')
            player = row.get('PLAYER', '')
            pts = int(row.get('POINTS', 0))
            made = action in ('2FGM', '3FGM')

            # League
            league[zone]['attempts'] += 1
            if made:
                league[zone]['makes'] += 1
                league[zone]['pts'] += pts

            # Team
            teams[team_code][zone]['attempts'] += 1
            if made:
                teams[team_code][zone]['makes'] += 1
                teams[team_code][zone]['pts'] += pts

            # Player
            players[player]['team'] = team_code
            players[player]['zones'][zone]['attempts'] += 1
            players[player]['total_fga'] += 1
            if made:
                players[player]['zones'][zone]['makes'] += 1
                players[player]['zones'][zone]['pts'] += pts

    def finalize(zone_dict):
        result = {}
        for z, d in zone_dict.items():
            att = d['attempts']
            if att == 0:
                continue
            result[z] = {
                'attempts': att,
                'makes': d['makes'],
                'fg_pct': round(d['makes'] / att * 100, 1),
                'pps': round(d['pts'] / att, 2),  # points per shot
            }
        return result

    # Filter players: min 50 FGA
    filtered_players = {}
    for name, pdata in players.items():
        if pdata['total_fga'] >= 50:
            filtered_players[name] = {
                'team': pdata['team'],
                'total_fga': pdata['total_fga'],
                'zones': finalize(pdata['zones']),
            }

    # ── Heatmap grid ─────────────────────────────────────────────────────────
    GRID_COLS, GRID_ROWS = 25, 25
    X_MIN, X_MAX = -740, 740
    Y_MIN, Y_MAX = -100, 1300
    cell_w = (X_MAX - X_MIN) / GRID_COLS
    cell_h = (Y_MAX - Y_MIN) / GRID_ROWS

    def new_grid():
        return [[{'att': 0, 'makes': 0} for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]

    league_grid = new_grid()
    team_grids = defaultdict(new_grid)

    with open(shot_file, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            action = row.get('ID_ACTION', '')
            if action not in ('2FGM', '2FGA', '3FGM', '3FGA'):
                continue
            try:
                x = int(row['COORD_X'])
                y = int(row['COORD_Y'])
            except (ValueError, KeyError):
                continue
            col = min(GRID_COLS - 1, max(0, int((x - X_MIN) / cell_w)))
            r   = min(GRID_ROWS - 1, max(0, int((y - Y_MIN) / cell_h)))
            made = 1 if action in ('2FGM', '3FGM') else 0
            team_code = row.get('TEAM', '')

            league_grid[r][col]['att'] += 1
            league_grid[r][col]['makes'] += made
            team_grids[team_code][r][col]['att'] += 1
            team_grids[team_code][r][col]['makes'] += made

    def grid_to_arrays(grid, min_att=3):
        """Convert grid to fg_pct and attempts 2D arrays with smoothing."""
        fg = []
        att = []
        for r in range(GRID_ROWS):
            fg_row = []
            att_row = []
            for c in range(GRID_COLS):
                cell = grid[r][c]
                if cell['att'] >= min_att:
                    fg_row.append(round(cell['makes'] / cell['att'] * 100, 1))
                    att_row.append(cell['att'])
                else:
                    fg_row.append(None)
                    att_row.append(0)
            fg.append(fg_row)
            att.append(att_row)
        return {'fg_pct': fg, 'attempts': att}

    grid_data = {
        'cols': GRID_COLS, 'rows': GRID_ROWS,
        'x_min': X_MIN, 'x_max': X_MAX,
        'y_min': Y_MIN, 'y_max': Y_MAX,
        'league': grid_to_arrays(league_grid, min_att=5),
        'teams': {code: grid_to_arrays(g, min_att=2) for code, g in team_grids.items()},
    }

    output = {
        'zone_names': ZONE_NAMES,
        'league': finalize(league),
        'teams': {code: finalize(zones) for code, zones in teams.items()},
        'players': filtered_players,
        'grid': grid_data,
    }

    total_shots = sum(d['attempts'] for d in league.values())
    print(f"  Total field goal attempts: {total_shots}")
    print(f"  Teams: {len(teams)}, Players (>=50 FGA): {len(filtered_players)}")
    print(f"  Heatmap grid: {GRID_COLS}x{GRID_ROWS} cells")
    return output


def build_game_recaps():
    """Build per-round game recaps with box scores from game stats + backtest."""
    all_stats = load_json('mvp_all_game_stats_2025.json')
    backtest = load_json('oracle_backtest_predictions.json')
    if not all_stats or not backtest:
        print("  Missing game stats or backtest — skipping game recaps.")
        return None

    # Build backtest lookup by GameCode
    bt_lookup = {}
    for g in backtest:
        bt_lookup[g['GameCode']] = g

    # Build schedule lookup by (homecode, awaycode) for game dates
    sched_lookup = {}
    try:
        import xml.etree.ElementTree as ET
        tree = ET.parse('official_schedule_2025.xml')
        for item in tree.getroot().iter('item'):
            home = (item.findtext('homecode') or '').strip()
            away = (item.findtext('awaycode') or '').strip()
            date = (item.findtext('date') or '').strip()
            time_ = (item.findtext('startime') or '').strip()
            if home and away:
                sched_lookup[(home, away)] = {'date': date, 'time': time_}
    except Exception:
        pass

    rounds = {}  # round_num -> [game, ...]

    for game in all_stats:
        gc = game.get('Gamecode', game.get('GameCode'))
        bt = bt_lookup.get(gc)
        if not bt:
            continue  # skip games not in backtest (future/unplayed)

        local_players = game.get('local.players', [])
        road_players = game.get('road.players', [])
        if not local_players and not road_players:
            continue  # no box score data

        rnd = bt['Round']
        home_code = bt['Home']
        away_code = bt['Away']
        home_pts = game.get('local.total.points', 0) or 0
        away_pts = game.get('road.total.points', 0) or 0

        def fmt_time(secs):
            secs = int(secs or 0)
            return f"{secs // 60}:{secs % 60:02d}"

        def build_player_row(entry):
            p = entry.get('player', {})
            s = entry.get('stats', {})
            person = p.get('person', {})
            time_secs = s.get('timePlayed', 0) or 0
            pts = int(s.get('points', 0) or 0)
            fg2m = int(s.get('fieldGoalsMade2', 0) or 0)
            fg2a = int(s.get('fieldGoalsAttempted2', 0) or 0)
            fg3m = int(s.get('fieldGoalsMade3', 0) or 0)
            fg3a = int(s.get('fieldGoalsAttempted3', 0) or 0)
            ftm = int(s.get('freeThrowsMade', 0) or 0)
            fta = int(s.get('freeThrowsAttempted', 0) or 0)
            return {
                'name': person.get('name', ''),
                'starter': bool(s.get('startFive')),
                'min': fmt_time(time_secs),
                'pts': pts,
                'reb': int(s.get('totalRebounds', 0) or 0),
                'ast': int(s.get('assistances', 0) or 0),
                'stl': int(s.get('steals', 0) or 0),
                'to': int(s.get('turnovers', 0) or 0),
                'blk': int(s.get('blocksFavour', 0) or 0),
                'pir': int(s.get('valuation', 0) or 0),
                'pm': int(s.get('plusMinus', 0) or 0),
                'fg': f"{fg2m + fg3m}/{fg2a + fg3a}",
                'fg3': f"{fg3m}/{fg3a}",
                'ft': f"{ftm}/{fta}",
            }

        home_roster = [build_player_row(e) for e in local_players
                       if (e.get('stats', {}).get('timePlayed', 0) or 0) > 0
                       or e.get('stats', {}).get('startFive')]
        away_roster = [build_player_row(e) for e in road_players
                       if (e.get('stats', {}).get('timePlayed', 0) or 0) > 0
                       or e.get('stats', {}).get('startFive')]

        # Sort: starters first (by PIR desc), then bench (by PIR desc)
        for roster in (home_roster, away_roster):
            roster.sort(key=lambda x: (-x['starter'], -x['pir']))

        # Team totals
        def team_totals(prefix):
            return {
                'pts': int(game.get(f'{prefix}.total.points', 0) or 0),
                'reb': int(game.get(f'{prefix}.total.totalRebounds', 0) or 0),
                'ast': int(game.get(f'{prefix}.total.assistances', 0) or 0),
                'stl': int(game.get(f'{prefix}.total.steals', 0) or 0),
                'to': int(game.get(f'{prefix}.total.turnovers', 0) or 0),
                'blk': int(game.get(f'{prefix}.total.blocksFavour', 0) or 0),
                'fg2': f"{int(game.get(f'{prefix}.total.fieldGoalsMade2', 0) or 0)}/{int(game.get(f'{prefix}.total.fieldGoalsAttempted2', 0) or 0)}",
                'fg3': f"{int(game.get(f'{prefix}.total.fieldGoalsMade3', 0) or 0)}/{int(game.get(f'{prefix}.total.fieldGoalsAttempted3', 0) or 0)}",
                'ft': f"{int(game.get(f'{prefix}.total.freeThrowsMade', 0) or 0)}/{int(game.get(f'{prefix}.total.freeThrowsAttempted', 0) or 0)}",
                'pir': int(game.get(f'{prefix}.total.valuation', 0) or 0),
            }

        # Find top performer (highest PIR across both teams)
        all_players = home_roster + away_roster
        top = max(all_players, key=lambda x: x['pir']) if all_players else None

        # Game date/time from schedule
        sched = sched_lookup.get((home_code, away_code), {})

        game_obj = {
            'gameCode': gc,
            'home': home_code,
            'away': away_code,
            'homePts': int(home_pts),
            'awayPts': int(away_pts),
            'homeName': TEAM_NAMES.get(home_code, home_code),
            'awayName': TEAM_NAMES.get(away_code, away_code),
            'date': sched.get('date', ''),
            'time': sched.get('time', ''),
            'homeRoster': home_roster,
            'awayRoster': away_roster,
            'homeTotals': team_totals('local'),
            'awayTotals': team_totals('road'),
            'oracle': {
                'predictedWinner': bt.get('PredictedWinner', ''),
                'homeWinProb': bt.get('HomeWinProb', 50),
                'margin': bt.get('PredictedMargin', 0),
                'correct': bt.get('Correct', False),
            },
        }
        if top:
            game_obj['topPerformer'] = {
                'name': top['name'],
                'pts': top['pts'],
                'reb': top['reb'],
                'ast': top['ast'],
                'pir': top['pir'],
            }

        rounds.setdefault(rnd, []).append(game_obj)

    # Sort games within each round by gamecode
    for rnd in rounds:
        rounds[rnd].sort(key=lambda x: x['gameCode'])

    # Convert to sorted list of rounds
    from datetime import datetime, timezone
    output = {
        'rounds': {str(r): rounds[r] for r in sorted(rounds.keys())},
        'totalRounds': max(rounds.keys()) if rounds else 0,
        'updated': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    }

    print(f"  Game recaps: {sum(len(v) for v in rounds.values())} games across {len(rounds)} rounds")
    return output


def main():
    suffix = os.environ.get('EUROLEAGUE_ROUND_SUFFIX', '')
    print(f"\n=== Dashboard Export ===")
    print(f"Round suffix: '{suffix}' (from EUROLEAGUE_ROUND_SUFFIX)")

    # ── Load all source data ─────────────────────────────────────────────────
    adjusted = load_with_fallback(suffix, 'adjusted_ratings.json')
    elo_data = load_with_fallback(suffix, 'elo_ratings.json')
    mc_data = load_with_fallback(suffix, 'monte_carlo_results.json')
    mvp_data = load_with_fallback(suffix, 'mvp_rankings_2025.json')
    standings_data = load_json('mvp_standings_derived.json')
    # Accuracy: try oracle_accuracy{suffix}.json first (no _ml infix), then ml variant, then bare
    accuracy_data = None
    if suffix:
        accuracy_data = load_json(f'oracle_accuracy{suffix}.json')
        if accuracy_data is not None:
            print(f"  Loaded: oracle_accuracy{suffix}.json")
    if accuracy_data is None:
        accuracy_data = load_with_fallback(suffix, 'oracle_accuracy_ml.json', 'oracle_accuracy_ml.json')
    if accuracy_data is None:
        accuracy_data = load_with_fallback(suffix, 'oracle_accuracy.json')

    oracle_path, oracle_round = find_latest_oracle_forecast()
    oracle_data = load_json(oracle_path) if oracle_path else None

    # Load player forecast and attach it to oracle data
    player_forecasts = find_latest_player_forecast(oracle_round)
    if oracle_data and player_forecasts:
        oracle_data['player_forecasts'] = player_forecasts

    # Enrich oracle predictions with game dates from schedule XML
    schedule_dates = parse_schedule_dates()
    if oracle_data and schedule_dates:
        for pred in oracle_data.get('predictions', []):
            key = (pred.get('Local', ''), pred.get('Road', ''))
            info = schedule_dates.get(key, {})
            pred['Date'] = info.get('date', '')
            pred['Time'] = info.get('time', '')

    # ── Compute Last 5 / home-away records / round results from backtest ─────
    l5_lookup       = {}
    home_rec_lookup = {}   # team -> {'W': n, 'L': n}
    away_rec_lookup = {}
    round_results_lookup = {}  # team -> [{round, result, opp}]
    backtest_data = load_with_fallback(suffix, 'oracle_backtest_predictions.json', 'oracle_backtest_predictions.json')
    if backtest_data:
        from collections import defaultdict
        team_games      = defaultdict(list)   # (rnd, result, opp, is_home)
        home_rec        = defaultdict(lambda: {'W': 0, 'L': 0})
        away_rec        = defaultdict(lambda: {'W': 0, 'L': 0})
        for g in backtest_data:
            home, away, winner = g.get('Home'), g.get('Away'), g.get('ActualWinner')
            rnd = g.get('Round', 0)
            if home and away and winner:
                hw = 'W' if winner == home else 'L'
                aw = 'W' if winner == away else 'L'
                team_games[home].append((rnd, hw, away,  True))
                team_games[away].append((rnd, aw, home, False))
                home_rec[home][hw] += 1
                away_rec[away][aw] += 1
        for team, games in team_games.items():
            games.sort(key=lambda x: x[0])
            l5_lookup[team] = [r for _, r, _, _ in games[-5:]]
            home_rec_lookup[team] = dict(home_rec[team])
            away_rec_lookup[team] = dict(away_rec[team])
            round_results_lookup[team] = [
                {'round': rnd, 'result': res, 'opp': opp, 'home': is_home}
                for rnd, res, opp, is_home in games
            ]

    # ── Build Elo lookup ─────────────────────────────────────────────────────
    elo_lookup = {}
    if elo_data:
        for row in elo_data:
            elo_lookup[row['Team']] = row.get('Elo', 1500.0)

    # ── Build Monte Carlo lookup ─────────────────────────────────────────────
    mc_lookup = {}
    if mc_data:
        for row in mc_data:
            mc_lookup[row['Team']] = row

    # ── Build standings lookup ───────────────────────────────────────────────
    standings_lookup = {}
    if standings_data:
        for code, vals in standings_data.items():
            standings_lookup[code] = vals

    # ── Determine round number ───────────────────────────────────────────────
    # Derive from suffix, standings GP, or oracle round
    round_num = 0
    if suffix:
        m = re.search(r'R(\d+)', suffix)
        if m:
            round_num = int(m.group(1))
    if round_num == 0 and standings_data:
        gp_vals = [v.get('GP', 0) for v in standings_data.values()]
        if gp_vals:
            round_num = max(gp_vals)
    if round_num == 0 and oracle_round and oracle_round > 0:
        round_num = oracle_round - 1  # oracle predicts NEXT round

    print(f"  Determined round: {round_num}")

    # ── Build teams list ─────────────────────────────────────────────────────
    teams = []
    if adjusted:
        for row in adjusted:
            code = row['Team']
            mc = mc_lookup.get(code, {})
            sl = standings_lookup.get(code, {})
            wins = sl.get('W', sl.get('Wins', row.get('Wins', 0)))
            losses = sl.get('L', sl.get('Losses', row.get('Losses', 0)))
            gp = sl.get('GP', wins + losses)
            win_pct = round((wins / gp * 100) if gp > 0 else 0.0, 1)

            teams.append({
                'team': code,
                'name': TEAM_NAMES.get(code, code),
                'wins': wins,
                'losses': losses,
                'win_pct': win_pct,
                'adj_net': round(row.get('Adj_Net', 0.0), 2),
                'adj_off': round(row.get('Adj_Off', 0.0), 2),
                'adj_def': round(row.get('Adj_Def', 0.0), 2),
                'elo': round(elo_lookup.get(code, 1500.0), 1),
                'sos': round(row.get('SOS_WinPct', 0.0) * 100, 1),
                'remaining': row.get('Remaining_Games', 0),
                'top4_pct': mc.get('Top4_Pct', 0.0),
                'top6_pct': mc.get('Top6_Pct', 0.0),
                'top10_pct': mc.get('Top10_Pct', 0.0),
                'avg_wins': round(mc.get('Avg_Wins', wins), 1),
                'current_wins': mc.get('Current_Wins', wins),
                'last5': l5_lookup.get(code, []),
                'home_record': home_rec_lookup.get(code, {'W': 0, 'L': 0}),
                'away_record': away_rec_lookup.get(code, {'W': 0, 'L': 0}),
                'round_results': round_results_lookup.get(code, []),
                'remaining_sos': round(row.get('Remaining_SOS', 0.0), 1),
                'home_games': row.get('Home_Games', 0),
                'away_games': row.get('Away_Games', 0),
                'remaining_opponents': row.get('Remaining_Opponents', []),
            })

    # Sort: wins desc, then adj_net desc
    teams.sort(key=lambda t: (-t['wins'], -t['adj_net']))

    # ── Build MVP list (top 15) with component breakdowns ─────────────────────
    mvp_list = []
    if mvp_data:
        for row in mvp_data[:15]:
            mvp_list.append({
                'rank': row.get('MVP_Rank', 0),
                'player': row.get('PlayerName', ''),
                'team': row.get('TeamCode', ''),
                'mvp_score': round(row.get('MVP_Score', 0.0), 2),
                'avg_pir': round(row.get('AvgPIR', 0.0), 2),
                'avg_gmsc': round(row.get('AvgGmSc', 0.0), 2),
                'wpa': round(row.get('WPA', 0.0), 1),
                'team_win_pct': round(row.get('TeamWinPct', 0.0) * 100, 1),
                'clutch_eff': round(row.get('ClutchEff', 0.0), 4),
                'clutch_pts': round(row.get('ClutchPoints', 0.0), 1),
                'consistency': round(row.get('Consistency', 0.0), 4),
                'gp': row.get('GP', 0),
            })

    # ── Build MVP race timeline ─────────────────────────────────────────────
    mvp_race = load_json('mvp_race_timeline.json') or []
    if mvp_race:
        rounds_in_race = len(set(r['round'] for r in mvp_race))
        print(f"  MVP race timeline: {len(mvp_race)} data points across {rounds_in_race} rounds")

    # ── Build player stats leaderboard ───────────────────────────────────────
    player_stats = build_player_stats(mvp_data)
    print(f"  Player stats: {len(player_stats)} players")

    # ── Load RAPM ratings ────────────────────────────────────────────────────
    rapm_data = load_with_fallback(suffix, 'rapm_ratings.json')
    if rapm_data:
        print(f"  RAPM ratings: {len(rapm_data)} players")
    else:
        rapm_data = []

    # ── Build output ─────────────────────────────────────────────────────────
    from datetime import datetime
    output = {
        'round': round_num,
        'updated': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'teams': teams,
        'mvp': mvp_list,
        'mvp_race': mvp_race,
        'player_stats': player_stats,
        'rapm': rapm_data,
        'oracle': oracle_data,
        'accuracy': accuracy_data,
    }

    # ── Write output ─────────────────────────────────────────────────────────
    out_dir = os.path.join('docs', 'data', 'current')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, 'dashboard.json')

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n=== Export Summary ===")
    print(f"  Output: {out_path}")
    print(f"  Round: {round_num}")
    print(f"  Teams: {len(teams)}")
    print(f"  MVP entries: {len(mvp_list)}")
    if oracle_data:
        preds = oracle_data.get('predictions', [])
        print(f"  Oracle predictions: {len(preds)} (Round {oracle_data.get('round', '?')})")
        if player_forecasts:
            print(f"  Player forecasts: {len(player_forecasts)}")
    else:
        print("  Oracle: not available")
    if accuracy_data:
        print(f"  Accuracy: {accuracy_data.get('accuracy', '?')}% over {accuracy_data.get('n_games', '?')} games")
    print(f"\nDone! dashboard.json written to {out_path}")

    # ── Shot stats export ────────────────────────────────────────────────────
    shot_stats = build_shot_stats()
    if shot_stats:
        shot_path = os.path.join(out_dir, 'shot_stats.json')
        with open(shot_path, 'w', encoding='utf-8') as f:
            json.dump(shot_stats, f, ensure_ascii=False, indent=2)
        n_players = len(shot_stats.get('players', {}))
        n_teams = len(shot_stats.get('teams', {}))
        print(f"  Shot stats: {n_teams} teams, {n_players} players -> {shot_path}")

    # ── Game recaps export ─────────────────────────────────────────────────
    print("\n--- Building game recaps ---")
    game_recaps = build_game_recaps()
    if game_recaps:
        recap_path = os.path.join(out_dir, 'game_recaps.json')
        with open(recap_path, 'w', encoding='utf-8') as f:
            json.dump(game_recaps, f, ensure_ascii=False)
        print(f"  Game recaps -> {recap_path}")

    # Copy backtest predictions for H2H page
    import shutil
    backtest_src = f'oracle_backtest_predictions.json'
    if os.path.exists(backtest_src):
        shutil.copy2(backtest_src, os.path.join(out_dir, 'oracle_backtest_predictions.json'))
        print(f"  Copied backtest predictions to {out_dir}")


if __name__ == '__main__':
    main()
