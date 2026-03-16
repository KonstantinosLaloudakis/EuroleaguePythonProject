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
    accuracy_data = load_with_fallback(suffix, 'oracle_accuracy_ml.json', 'oracle_accuracy_ml.json')
    if accuracy_data is None:
        accuracy_data = load_with_fallback(suffix, 'oracle_accuracy.json')

    oracle_path, oracle_round = find_latest_oracle_forecast()
    oracle_data = load_json(oracle_path) if oracle_path else None

    # Load player forecast and attach it to oracle data
    player_forecasts = find_latest_player_forecast(oracle_round)
    if oracle_data and player_forecasts:
        oracle_data['player_forecasts'] = player_forecasts

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
            })

    # Sort: wins desc, then adj_net desc
    teams.sort(key=lambda t: (-t['wins'], -t['adj_net']))

    # ── Build MVP list (top 15) ──────────────────────────────────────────────
    mvp_list = []
    if mvp_data:
        for row in mvp_data[:15]:
            mvp_list.append({
                'rank': row.get('MVP_Rank', 0),
                'player': row.get('PlayerName', ''),
                'team': row.get('TeamCode', ''),
                'mvp_score': round(row.get('MVP_Score', 0.0), 2),
                'avg_pir': round(row.get('AvgPIR', 0.0), 2),
                'wpa': round(row.get('WPA', 0.0), 1),
                'team_win_pct': round(row.get('TeamWinPct', 0.0) * 100, 1),
                'clutch_eff': round(row.get('ClutchEff', 0.0), 4),
                'gp': row.get('GP', 0),
            })

    # ── Build output ─────────────────────────────────────────────────────────
    output = {
        'round': round_num,
        'teams': teams,
        'mvp': mvp_list,
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


if __name__ == '__main__':
    main()
