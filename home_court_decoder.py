"""
Home Court Decoder v2 — What Makes Home Court Actually Work?
Decomposes HCA into 6 components:
  OFFENSE: Shooting Boost, Whistle Advantage, Ball Security, OREB Boost
  DEFENSE: Defensive Squeeze (opponents play worse at our home)
  RESIDUAL: What's left (crowd intangibles, travel fatigue, etc.)
"""

import pandas as pd
import numpy as np
import json


def build_home_court_decoder():
    # ── Load data ──────────────────────────────────────────────
    pbp = pd.read_csv('pbp_2025.csv', low_memory=False)
    games = pd.read_csv('data_cache/games_2025.csv', low_memory=False)
    games = games[games['played'] == True]

    # Build gamecode → home/away team mapping (PBP uses integer Gamecode, games uses gamenumber)
    home_map = dict(zip(games['gamenumber'], games['homecode']))
    away_map = dict(zip(games['gamenumber'], games['awaycode']))
    home_score_map = dict(zip(games['gamenumber'], games['homescore']))
    away_score_map = dict(zip(games['gamenumber'], games['awayscore']))

    # Tag each PBP row as Home or Away
    pbp = pbp[pbp['CODETEAM'].notna()].copy()
    pbp['IS_HOME'] = pbp.apply(
        lambda r: r['CODETEAM'] == home_map.get(r['Gamecode']), axis=1
    )

    # For defensive analysis: tag opponent's plays
    # For a given gamecode, identify the opponent team
    def get_opponent(row):
        gc = row['Gamecode']
        team = row['CODETEAM']
        h = home_map.get(gc)
        a = away_map.get(gc)
        if team == h:
            return a
        elif team == a:
            return h
        return None

    # ── Count play types per subset ────────────────────────────
    def count_plays(subset):
        return pd.Series({
            'FGM_2': (subset['PLAYTYPE'] == '2FGM').sum(),
            'FGA_2': ((subset['PLAYTYPE'] == '2FGM') | (subset['PLAYTYPE'] == '2FGA')).sum(),
            'FGM_3': (subset['PLAYTYPE'] == '3FGM').sum(),
            'FGA_3': ((subset['PLAYTYPE'] == '3FGM') | (subset['PLAYTYPE'] == '3FGA')).sum(),
            'FTM':   (subset['PLAYTYPE'] == 'FTM').sum(),
            'FTA':   ((subset['PLAYTYPE'] == 'FTM') | (subset['PLAYTYPE'] == 'FTA')).sum(),
            'TO':    (subset['PLAYTYPE'] == 'TO').sum(),
            'OREB':  (subset['PLAYTYPE'] == 'O').sum(),
        })

    PPP = 1.0  # Points per possession estimate

    all_teams = sorted(pbp['CODETEAM'].unique())
    results = []

    for team in all_teams:
        team_data = pbp[pbp['CODETEAM'] == team]

        home_games = team_data[team_data['IS_HOME'] == True]
        away_games = team_data[team_data['IS_HOME'] == False]

        home_gcs = home_games['Gamecode'].unique()
        away_gcs = away_games['Gamecode'].unique()

        n_home = len(home_gcs)
        n_away = len(away_gcs)

        if n_home == 0 or n_away == 0:
            continue

        # ── OFFENSIVE components ──────────────────────────────
        h = count_plays(home_games)
        a = count_plays(away_games)
        h_pg = h / n_home
        a_pg = a / n_away

        # 1. Shooting Boost
        h_pts_shooting = 2 * h_pg['FGM_2'] + 3 * h_pg['FGM_3']
        a_pts_shooting = 2 * a_pg['FGM_2'] + 3 * a_pg['FGM_3']
        shooting_boost = h_pts_shooting - a_pts_shooting

        # 2. Whistle Advantage (FT points)
        whistle_advantage = h_pg['FTM'] - a_pg['FTM']

        # 3. Ball Security (fewer TOs = more possessions)
        ball_security = (a_pg['TO'] - h_pg['TO']) * PPP

        # 4. OREB Boost (extra offensive rebounds → extra possessions)
        oreb_boost = (h_pg['OREB'] - a_pg['OREB']) * PPP

        # ── DEFENSIVE components ──────────────────────────────
        # What does the OPPONENT do when playing AT our home vs when we visit them?
        # Opponent stats when we are home:
        opp_at_home = pbp[
            (pbp['Gamecode'].isin(home_gcs)) &
            (pbp['CODETEAM'] != team) &
            (pbp['CODETEAM'].notna())
        ]
        # Opponent stats when we are away (opponent is at their HOME):
        opp_at_away = pbp[
            (pbp['Gamecode'].isin(away_gcs)) &
            (pbp['CODETEAM'] != team) &
            (pbp['CODETEAM'].notna())
        ]

        oh = count_plays(opp_at_home)
        oa = count_plays(opp_at_away)
        oh_pg = oh / n_home
        oa_pg = oa / n_away

        # Defensive squeeze = how much LESS the opponent scores at OUR home
        # vs when we visit THEIR home
        # Positive = opponent scores less at our place = 
        opp_pts_at_our_home = 2 * oh_pg['FGM_2'] + 3 * oh_pg['FGM_3'] + oh_pg['FTM']
        opp_pts_at_their_home = 2 * oa_pg['FGM_2'] + 3 * oa_pg['FGM_3'] + oa_pg['FTM']
        defensive_squeeze = opp_pts_at_their_home - opp_pts_at_our_home

        # ── Actual Net HCA (point differential) ──────────────
        avg_home_score = np.mean([home_score_map.get(gc, 0) for gc in home_gcs])
        avg_away_score = np.mean([away_score_map.get(gc, 0) for gc in away_gcs])

        avg_opp_home_score = np.mean([away_score_map.get(gc, 0) for gc in home_gcs])
        avg_opp_away_score = np.mean([home_score_map.get(gc, 0) for gc in away_gcs])

        home_margin = avg_home_score - avg_opp_home_score
        away_margin = avg_away_score - avg_opp_away_score
        net_hca = home_margin - away_margin

        # ── Residual ─────────────────────────────────────────
        explained = shooting_boost + whistle_advantage + ball_security + oreb_boost + defensive_squeeze
        residual = net_hca - explained

        results.append({
            'Team': team,
            'HomeGames': n_home,
            'AwayGames': n_away,
            'NetHCA': round(net_hca, 1),
            'HomeMargin': round(home_margin, 1),
            'AwayMargin': round(away_margin, 1),
            'ShootingBoost': round(shooting_boost, 2),
            'WhistleAdvantage': round(whistle_advantage, 2),
            'BallSecurity': round(ball_security, 2),
            'OREBBoost': round(oreb_boost, 2),
            'DefensiveSqueeze': round(defensive_squeeze, 2),
            'Residual': round(residual, 2),
        })

    df_results = pd.DataFrame(results).sort_values('NetHCA', ascending=False)

    # ── Print summary ──────────────────────────────────────────
    print("=" * 80)
    print("  HOME COURT DECODER v2 — Euroleague 2025-26")
    print("=" * 80)
    print()

    league_hca = df_results['NetHCA'].mean()
    print(f"  League-Wide Net HCA: {league_hca:+.1f} pts/game")
    for col, label in [('ShootingBoost', 'Shooting Boost'),
                       ('WhistleAdvantage', 'Whistle Advantage'),
                       ('BallSecurity', 'Ball Security'),
                       ('OREBBoost', 'OREB Boost'),
                       ('DefensiveSqueeze', 'Defensive Squeeze'),
                       ('Residual', 'Residual')]:
        print(f"    {label:<20s} {df_results[col].mean():+.2f} pts")
    print()

    print(f"  {'Team':<6} {'NetHCA':>7} {'Shoot':>7} {'Whist':>7} {'Ball':>7} {'OREB':>7} {'DefSq':>7} {'Resid':>7}")
    print(f"  {'-'*6} {'-'*7} {'-'*7} {'-'*7} {'-'*7} {'-'*7} {'-'*7} {'-'*7}")
    for _, r in df_results.iterrows():
        print(f"  {r['Team']:<6} {r['NetHCA']:>+7.1f} {r['ShootingBoost']:>+7.2f} "
              f"{r['WhistleAdvantage']:>+7.2f} {r['BallSecurity']:>+7.2f} "
              f"{r['OREBBoost']:>+7.02f} {r['DefensiveSqueeze']:>+7.2f} {r['Residual']:>+7.02f}")

    # ── Save JSON ──────────────────────────────────────────────
    output = {
        'league_avg_hca': round(league_hca, 2),
        'components_avg': {
            'shooting_boost': round(df_results['ShootingBoost'].mean(), 2),
            'whistle_advantage': round(df_results['WhistleAdvantage'].mean(), 2),
            'ball_security': round(df_results['BallSecurity'].mean(), 2),
            'oreb_boost': round(df_results['OREBBoost'].mean(), 2),
            'defensive_squeeze': round(df_results['DefensiveSqueeze'].mean(), 2),
            'residual': round(df_results['Residual'].mean(), 2),
        },
        'teams': df_results.to_dict('records'),
    }
    with open('hca_decoder.json', 'w') as f:
        json.dump(output, f, indent=4)
    print(f"\n  Saved to hca_decoder.json")

    return df_results


if __name__ == '__main__':
    build_home_court_decoder()
