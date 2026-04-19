"""
Calibration backtest for the playoff matchup probability formula.

Replays 2022-2024 seasons: builds RS-only adjusted ratings + Elo + HCA inputs
per season, then predicts P(home wins) for every played game in that season
(RS + postseason) using the exact formula from export_dashboard_data.py:1185-
1208. Reports Brier / LogLoss / ECE overall, RS-only, and postseason-only,
plus a reliability diagram.

If combined postseason ECE > 0.05, fits a Platt scaling correction on the
multi-season postseason sample and writes coefficients.

Run:  ./.venv/Scripts/python.exe backtest_matchup_calibration.py
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression

from calculate_adjusted_ratings import calculate_raw_ratings, run_iterative_adjustment
from wp_model_utils import predict_wp


SEASONS = [2022, 2023, 2024]
ELO_JSON = Path('data_cache') / 'game_elos.json'
ELO_BASELINE = 1500.0
NEUTRAL_ROUNDS = {'FF'}
POST_ROUNDS = {'PI', 'PO', 'FF'}


def _detect_home_team(game_df, teams):
    """Find the CODETEAM whose baskets increment POINTS_A (= home team)."""
    prev_a, prev_b = 0, 0
    for _, row in game_df.dropna(subset=['POINTS_A', 'POINTS_B', 'CODETEAM']).iterrows():
        if row['CODETEAM'] not in teams:
            continue
        try:
            a, b = int(row['POINTS_A']), int(row['POINTS_B'])
        except (ValueError, TypeError):
            continue
        if a > prev_a and b == prev_b:
            return row['CODETEAM']
        if b > prev_b and a == prev_a:
            return [t for t in teams if t != row['CODETEAM']][0]
        prev_a, prev_b = a, b
    return None


def build_games_from_pbp(season):
    """Derive a games DataFrame (round, gamecode, homecode, awaycode, homescore,
    awayscore) from the season's PBP file. Verified against games_2024.csv to
    match 100% of games on home/away and final scores.
    """
    pbp_path = Path('data_cache') / f'pbp_{season}.csv'
    df = pd.read_csv(
        pbp_path,
        usecols=['Phase', 'Round', 'Gamecode', 'CODETEAM', 'POINTS_A', 'POINTS_B'],
    )
    rows = []
    for gc, game in df.groupby('Gamecode'):
        teams = game['CODETEAM'].dropna().unique().tolist()
        if len(teams) != 2:
            continue
        pa = game['POINTS_A'].dropna()
        pb = game['POINTS_B'].dropna()
        if pa.empty or pb.empty:
            continue
        home = _detect_home_team(game, teams)
        if home is None:
            continue
        away = [t for t in teams if t != home][0]
        rows.append({
            'round': game['Phase'].iloc[0],
            'gamecode': f'E{season}_{int(gc)}',
            'gc_num': int(gc),
            'homecode': home,
            'awaycode': away,
            'homescore': int(pa.max()),
            'awayscore': int(pb.max()),
            'played': True,
        })
    return pd.DataFrame(rows)


def csv_row_to_game_dict(row):
    """Adapt a games row (from CSV or PBP-derived) to calculate_raw_ratings shape."""
    return {
        'LocalTeam': row['homecode'],
        'RoadTeam': row['awaycode'],
        'LocalScore': int(row['homescore']),
        'RoadScore': int(row['awayscore']),
        'GameCode': int(row['gc_num']),
    }


def build_hca_maps(rs_games_dicts):
    """Mirror export_dashboard_data.py:1163-1183, but on RS games only."""
    df = pd.DataFrame(rs_games_dicts)
    hca_global = float((df['LocalScore'] - df['RoadScore']).mean())

    td = {}
    for _, row in df.iterrows():
        loc, road = row['LocalTeam'], row['RoadTeam']
        lp, rp = row['LocalScore'], row['RoadScore']
        for t in (loc, road):
            if t not in td:
                td[t] = {'HP': 0, 'HA': 0, 'HG': 0, 'AP': 0, 'AA': 0, 'AG': 0}
        td[loc]['HP'] += lp; td[loc]['HA'] += rp; td[loc]['HG'] += 1
        td[road]['AP'] += rp; td[road]['AA'] += lp; td[road]['AG'] += 1

    home_net_map, net_map = {}, {}
    for t, s in td.items():
        gp = s['HG'] + s['AG']
        net_map[t] = ((s['HP'] + s['AP']) - (s['HA'] + s['AA'])) / gp if gp > 0 else 0
        home_net_map[t] = (s['HP'] - s['HA']) / s['HG'] if s['HG'] > 0 else 0
    return hca_global, home_net_map, net_map


def matchup_prob(team_a_adj, team_a_elo, team_b_adj, team_b_elo,
                 team_a_code, venue, hca_global, home_net_map, net_map):
    """Verbatim port of _matchup_prob from export_dashboard_data.py:1185-1208."""
    a_adj, b_adj = team_a_adj, team_b_adj
    a_elo, b_elo = team_a_elo, team_b_elo

    if venue == 'home':
        elo_margin = (a_elo - b_elo + 50) / 25
        margin_raw = (a_adj - b_adj) * 0.75 + elo_margin * 0.25
        team_hca = home_net_map.get(team_a_code, 0) - net_map.get(team_a_code, 0)
        blended_hca = (hca_global * 0.7 + team_hca * 0.3) * 0.5
        pred_margin = margin_raw + blended_hca
        return predict_wp(margin=pred_margin, seconds_remaining=2400, elo_diff=a_elo - b_elo)

    elif venue == 'away':
        return 1.0 - matchup_prob(team_b_adj, team_b_elo, team_a_adj, team_a_elo,
                                  None, 'home', hca_global, home_net_map, net_map)

    else:  # neutral
        elo_margin = (a_elo - b_elo) / 25
        margin_raw = (a_adj - b_adj) * 0.75 + elo_margin * 0.25
        p_a = predict_wp(margin=margin_raw, seconds_remaining=2400, elo_diff=a_elo - b_elo)
        p_b = predict_wp(margin=-margin_raw, seconds_remaining=2400, elo_diff=b_elo - a_elo)
        return (p_a + (1.0 - p_b)) / 2.0


def brier(p, y):
    return float(np.mean((p - y) ** 2))


def log_loss(p, y, eps=1e-12):
    p = np.clip(p, eps, 1 - eps)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def ece(p, y, n_bins=10):
    """Expected Calibration Error using equal-width bins on [0,1]."""
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    n = len(p)
    total = 0.0
    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        mask = (p >= lo) & (p < hi) if i < n_bins - 1 else (p >= lo) & (p <= hi)
        if mask.sum() == 0:
            continue
        bin_pred = p[mask].mean()
        bin_actual = y[mask].mean()
        total += (mask.sum() / n) * abs(bin_pred - bin_actual)
    return float(total)


def reliability_table(p, y, n_bins=10):
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    rows = []
    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        mask = (p >= lo) & (p < hi) if i < n_bins - 1 else (p >= lo) & (p <= hi)
        n = int(mask.sum())
        if n == 0:
            rows.append((f"[{lo:.1f},{hi:.1f}]", 0, None, None))
        else:
            rows.append((f"[{lo:.1f},{hi:.1f}]", n, float(p[mask].mean()), float(y[mask].mean())))
    return rows


def plot_reliability(p, y, out_path, n_bins=10):
    rows = reliability_table(p, y, n_bins)
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.plot([0, 1], [0, 1], '--', color='gray', label='Perfect calibration', linewidth=1)
    xs, ys, sizes = [], [], []
    for _, n, pm, ar in rows:
        if n == 0:
            continue
        xs.append(pm); ys.append(ar); sizes.append(n)
    sizes_arr = np.array(sizes, dtype=float)
    bubble = 30 + (sizes_arr / sizes_arr.max()) * 600
    ax.scatter(xs, ys, s=bubble, alpha=0.6, edgecolors='black', linewidths=0.8, color='#1f77b4')
    for x, yv, n in zip(xs, ys, sizes):
        ax.annotate(str(n), (x, yv), textcoords='offset points', xytext=(0, -3),
                    ha='center', fontsize=8)
    ax.set_xlabel('Predicted P(home win) — bin mean')
    ax.set_ylabel('Actual home win rate')
    ax.set_title(f'Matchup Formula Reliability — {SEASONS[0]}–{SEASONS[-1]} seasons ({len(p)} games)\n'
                 f'Bubble size = games per bin')
    ax.set_xlim(-0.02, 1.02); ax.set_ylim(-0.02, 1.02)
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper left')
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def _load_season_games(season):
    """Return a played-games DataFrame for a season, preferring the CSV when
    available and falling back to PBP derivation (verified equivalent on 2024)."""
    csv_path = Path('data_cache') / f'games_{season}.csv'
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        df = df[df['played'] == True].copy()
        df['gc_num'] = df['gamecode'].apply(lambda s: int(s.split('_')[1]))
        return df
    return build_games_from_pbp(season)


def _backtest_season(season, elo_db):
    """Run the per-season pipeline and return a list of game records."""
    df = _load_season_games(season)
    rs_df = df[df['round'] == 'RS'].copy()

    rs_game_dicts = [csv_row_to_game_dict(r) for _, r in rs_df.iterrows()]
    if not rs_game_dicts:
        print(f'  Season {season}: no RS games — skipping')
        return []

    teams, league_avg = calculate_raw_ratings(rs_game_dicts)
    adj_off, adj_def, adj_net = run_iterative_adjustment(teams, league_avg)
    hca_global, home_net_map, net_map = build_hca_maps(rs_game_dicts)

    records = []
    for _, row in df.iterrows():
        gc_num = int(row['gc_num'])
        elo_key = f"{season}_{gc_num}"
        if elo_key not in elo_db:
            continue
        elo_diff = float(elo_db[elo_key]['elo_diff'])
        home_elo = ELO_BASELINE + elo_diff / 2.0
        away_elo = ELO_BASELINE - elo_diff / 2.0

        home, away = row['homecode'], row['awaycode']
        if home not in adj_net or away not in adj_net:
            continue

        venue = 'neutral' if row['round'] in NEUTRAL_ROUNDS else 'home'
        p_home = matchup_prob(
            team_a_adj=adj_net[home], team_a_elo=home_elo,
            team_b_adj=adj_net[away], team_b_elo=away_elo,
            team_a_code=home, venue=venue,
            hca_global=hca_global, home_net_map=home_net_map, net_map=net_map,
        )
        actual = 1 if int(row['homescore']) > int(row['awayscore']) else 0
        margin = int(row['homescore']) - int(row['awayscore'])
        records.append({
            'season': season,
            'gamecode': row['gamecode'],
            'round': row['round'],
            'home': home, 'away': away,
            'venue': venue,
            'predicted_home_wp': float(p_home),
            'actual_home_won': actual,
            'margin': margin,
        })

    n_rs = sum(1 for r in records if r['round'] == 'RS')
    n_po = sum(1 for r in records if r['round'] in POST_ROUNDS)
    print(f'  Season {season}: {len(records)} games ({n_rs} RS + {n_po} postseason)')
    return records


def main():
    with open(ELO_JSON) as f:
        elo_db = json.load(f)

    print(f'Running calibration backtest across seasons: {SEASONS}')
    records = []
    for season in SEASONS:
        records.extend(_backtest_season(season, elo_db))

    rec_df = pd.DataFrame(records)
    p_all = rec_df['predicted_home_wp'].to_numpy()
    y_all = rec_df['actual_home_won'].to_numpy()

    rs_mask = rec_df['round'] == 'RS'
    po_mask = rec_df['round'].isin(POST_ROUNDS)

    summary = {
        'overall': {
            'n': int(len(rec_df)),
            'brier': brier(p_all, y_all),
            'log_loss': log_loss(p_all, y_all),
            'ece': ece(p_all, y_all),
        },
        'rs': {
            'n': int(rs_mask.sum()),
            'brier': brier(p_all[rs_mask], y_all[rs_mask]),
            'log_loss': log_loss(p_all[rs_mask], y_all[rs_mask]),
            'ece': ece(p_all[rs_mask], y_all[rs_mask]),
        },
        'postseason': {
            'n': int(po_mask.sum()),
            'brier': brier(p_all[po_mask], y_all[po_mask]),
            'log_loss': log_loss(p_all[po_mask], y_all[po_mask]),
            'ece': ece(p_all[po_mask], y_all[po_mask]),
        },
    }

    rel = reliability_table(p_all, y_all, n_bins=10)
    plot_reliability(p_all, y_all, 'backtest_reliability.png', n_bins=10)

    # Print summary
    print()
    print('=== Calibration Backtest ===')
    n_rs = int(rs_mask.sum()); n_po = int(po_mask.sum())
    print(f'Seasons {SEASONS}: {len(rec_df)} games ({n_rs} RS + {n_po} postseason)')
    o, r, p = summary['overall'], summary['rs'], summary['postseason']
    print(f"Overall: Brier={o['brier']:.3f}, LogLoss={o['log_loss']:.3f}, ECE={o['ece']:.3f}")
    print(f"RS only:  Brier={r['brier']:.3f}, LogLoss={r['log_loss']:.3f}, ECE={r['ece']:.3f}")
    print(f"PO only:  Brier={p['brier']:.3f}, LogLoss={p['log_loss']:.3f}, ECE={p['ece']:.3f}")
    print('Reliability by bin: [(bin_range, n_games, pred_mean, actual_rate)...]')
    for r_row in rel:
        print(f'  {r_row}')

    # Platt scaling on postseason if needed
    platt_info = None
    if summary['postseason']['ece'] > 0.05 and po_mask.sum() >= 5:
        X = p_all[po_mask].reshape(-1, 1)
        y = y_all[po_mask]
        # logit transform input for proper Platt scaling
        X_clip = np.clip(X, 1e-6, 1 - 1e-6)
        X_logit = np.log(X_clip / (1 - X_clip))
        lr = LogisticRegression(C=1e6, solver='lbfgs')
        lr.fit(X_logit, y)
        coef = float(lr.coef_[0][0])
        intercept = float(lr.intercept_[0])
        platt_info = {
            'method': 'platt_sigmoid_on_logit',
            'coef': coef,
            'intercept': intercept,
            'usage': 'p_corrected = sigmoid(coef * logit(p_raw) + intercept)',
            'fit_on': 'postseason',
            'n_fit': int(po_mask.sum()),
        }
        with open('calibration_correction.json', 'w') as f:
            json.dump(platt_info, f, indent=2)
        print(f'\nPostseason ECE > 0.05 — fit Platt scaling:')
        print(f'  coef={coef:.4f}, intercept={intercept:.4f}')
        print(f'  saved to calibration_correction.json')
    else:
        print('\nCalibration OK — no correction needed')

    # Save full results JSON
    out = {
        'seasons': SEASONS,
        'summary': summary,
        'reliability_bins': [
            {'range': r_row[0], 'n': r_row[1],
             'pred_mean': r_row[2], 'actual_rate': r_row[3]}
            for r_row in rel
        ],
        'platt': platt_info,
        'records': records,
    }
    with open('backtest_results.json', 'w') as f:
        json.dump(out, f, indent=2)
    print(f'\nSaved backtest_results.json ({len(records)} game records)')
    print('Saved backtest_reliability.png')


if __name__ == '__main__':
    main()
