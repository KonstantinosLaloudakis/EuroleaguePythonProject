"""
Lineup Chemistry Lab — Identify best and worst 2-man combinations per team.
Tracks who is on court together using IN/OUT substitution data from PBP.
"""

import pandas as pd
import numpy as np
import json
from itertools import combinations
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors


def build_lineup_lab(team_code):
    pbp = pd.read_csv('pbp_2025.csv', low_memory=False)
    games = pd.read_csv('data_cache/games_2025.csv', low_memory=False)
    games = games[games['played'] == True]

    home_map = dict(zip(games['gamenumber'], games['homecode']))
    away_map = dict(zip(games['gamenumber'], games['awaycode']))

    # Get gamecodes where this team played
    team_games = []
    for _, g in games.iterrows():
        gc = g['gamenumber']
        if g['homecode'] == team_code or g['awaycode'] == team_code:
            team_games.append(gc)

    print(f"\n  Processing {team_code}: {len(team_games)} games")

    # Accumulate 2-man combo stats across all games
    combo_stats = {}  # (player1, player2) -> {'plus': X, 'minus': Y, 'possessions': N}

    for gc in team_games:
        game_pbp = pbp[pbp['Gamecode'] == gc].sort_values('NUMBEROFPLAY')

        is_home = home_map.get(gc) == team_code

        # Track the on-court set for our team
        on_court = set()
        stint_start_score_a = 0
        stint_start_score_b = 0
        stint_initialized = False

        for _, row in game_pbp.iterrows():
            play_type = row['PLAYTYPE']
            play_team = row['CODETEAM']

            # Period boundaries reset the on-court tracking
            if play_type in ['BP']:
                on_court = set()
                stint_initialized = False
                continue

            if play_type in ['EP', 'EG']:
                # End of period/game: flush current stint
                if stint_initialized and len(on_court) == 5:
                    last_a = last_valid_a
                    last_b = last_valid_b
                    delta_a = last_a - stint_start_score_a
                    delta_b = last_b - stint_start_score_b
                    if is_home:
                        plus_minus = delta_a - delta_b
                    else:
                        plus_minus = delta_b - delta_a
                    # Credit this plus/minus to all 2-man combos on court
                    for duo in combinations(sorted(on_court), 2):
                        if duo not in combo_stats:
                            combo_stats[duo] = {'plus_minus': 0, 'stints': 0}
                        combo_stats[duo]['plus_minus'] += plus_minus
                        combo_stats[duo]['stints'] += 1
                on_court = set()
                stint_initialized = False
                continue

            # Track running score (use last valid score)
            if pd.notna(row.get('POINTS_A')) and pd.notna(row.get('POINTS_B')):
                last_valid_a = int(row['POINTS_A'])
                last_valid_b = int(row['POINTS_B'])

            # Substitution: IN/OUT for our team
            if play_type == 'IN' and play_team == team_code:
                # Before adding, flush current stint if we had 5 players
                if stint_initialized and len(on_court) == 5:
                    if pd.notna(row.get('POINTS_A')) or 'last_valid_a' in dir():
                        delta_a = last_valid_a - stint_start_score_a
                        delta_b = last_valid_b - stint_start_score_b
                        if is_home:
                            plus_minus = delta_a - delta_b
                        else:
                            plus_minus = delta_b - delta_a
                        for duo in combinations(sorted(on_court), 2):
                            if duo not in combo_stats:
                                combo_stats[duo] = {'plus_minus': 0, 'stints': 0}
                            combo_stats[duo]['plus_minus'] += plus_minus
                            combo_stats[duo]['stints'] += 1
                on_court.add(row['PLAYER'])
                # Start new stint
                if len(on_court) == 5:
                    stint_start_score_a = last_valid_a if 'last_valid_a' in dir() else 0
                    stint_start_score_b = last_valid_b if 'last_valid_b' in dir() else 0
                    stint_initialized = True

            elif play_type == 'OUT' and play_team == team_code:
                on_court.discard(row['PLAYER'])

            # At start of game/period, if we see scoring plays for our team
            # before any subs, we need to infer the starting lineup
            if not stint_initialized and play_team == team_code and play_type not in ['IN', 'OUT', 'BP', 'EP', 'EG']:
                player = row.get('PLAYER')
                if pd.notna(player):
                    on_court.add(player)
                    if len(on_court) == 5:
                        stint_start_score_a = last_valid_a if 'last_valid_a' in dir() else 0
                        stint_start_score_b = last_valid_b if 'last_valid_b' in dir() else 0
                        stint_initialized = True

    # ── Process results ──────────────────────────────────────
    # Filter to duos with meaningful sample (at least 5 stints)
    MIN_STINTS = 5
    results = []
    for duo, stats in combo_stats.items():
        if stats['stints'] >= MIN_STINTS:
            results.append({
                'Player1': duo[0],
                'Player2': duo[1],
                'PlusMinus': stats['plus_minus'],
                'Stints': stats['stints'],
                'AvgPM': round(stats['plus_minus'] / stats['stints'], 2),
            })

    df = pd.DataFrame(results).sort_values('AvgPM', ascending=False)

    # ── Print Top/Bottom Duos ────────────────────────────────
    print(f"\n  {'='*70}")
    print(f"  LINEUP CHEMISTRY LAB — {team_code}")
    print(f"  {'='*70}")
    print(f"\n  Total 2-man combos tracked: {len(df)}")

    print(f"\n  --- TOP 10 CHEMISTRY DUOS (Best +/-) ---")
    print(f"  {'Player 1':<24} {'Player 2':<24} {'Stints':>7} {'Total +/-':>10} {'Avg +/-':>8}")
    print(f"  {'-'*24} {'-'*24} {'-'*7} {'-'*10} {'-'*8}")
    for _, r in df.head(10).iterrows():
        print(f"  {r['Player1']:<24} {r['Player2']:<24} {r['Stints']:>7} {r['PlusMinus']:>+10} {r['AvgPM']:>+8.2f}")

    print(f"\n  --- BOTTOM 10 TOXIC PAIRS (Worst +/-) ---")
    print(f"  {'Player 1':<24} {'Player 2':<24} {'Stints':>7} {'Total +/-':>10} {'Avg +/-':>8}")
    print(f"  {'-'*24} {'-'*24} {'-'*7} {'-'*10} {'-'*8}")
    for _, r in df.tail(10).iterrows():
        print(f"  {r['Player1']:<24} {r['Player2']:<24} {r['Stints']:>7} {r['PlusMinus']:>+10} {r['AvgPM']:>+8.2f}")

    # ── Save JSON ────────────────────────────────────────────
    output = {
        'team': team_code,
        'duos': df.to_dict('records'),
    }
    outfile = f'chemistry_{team_code}.json'
    with open(outfile, 'w') as f:
        json.dump(output, f, indent=4)
    print(f"\n  Saved to {outfile}")

    # ── Visualize ────────────────────────────────────────────
    visualize_matrix(team_code, df)

    return df


def visualize_matrix(team_code, df):
    """Create a heatmap matrix of 2-man combo net ratings."""
    # Get core players (top 10 by total stints)
    player_stints = {}
    for _, r in df.iterrows():
        for p in [r['Player1'], r['Player2']]:
            player_stints[p] = player_stints.get(p, 0) + r['Stints']
    top_players = sorted(player_stints, key=lambda x: -player_stints[x])[:12]

    n = len(top_players)
    matrix = np.full((n, n), np.nan)

    # Build lookup
    pm_lookup = {}
    for _, r in df.iterrows():
        duo = tuple(sorted([r['Player1'], r['Player2']]))
        pm_lookup[duo] = r['AvgPM']

    for i in range(n):
        for j in range(i+1, n):
            duo = tuple(sorted([top_players[i], top_players[j]]))
            if duo in pm_lookup:
                matrix[i][j] = pm_lookup[duo]
                matrix[j][i] = pm_lookup[duo]

    # Short names (last name only)
    short = [p.split(',')[0].title() for p in top_players]

    fig, ax = plt.subplots(figsize=(12, 10))
    fig.patch.set_facecolor('#0f1117')
    ax.set_facecolor('#0f1117')

    vmax = np.nanmax(np.abs(matrix))
    if np.isnan(vmax) or vmax == 0:
        vmax = 5
    cmap = mcolors.LinearSegmentedColormap.from_list(
        'chemistry', ['#ef4444', '#1f2937', '#22c55e'], N=256
    )

    im = ax.imshow(matrix, cmap=cmap, vmin=-vmax, vmax=vmax, aspect='auto')

    # Annotate
    for i in range(n):
        for j in range(n):
            if i != j and not np.isnan(matrix[i][j]):
                val = matrix[i][j]
                ax.text(j, i, f'{val:+.1f}', ha='center', va='center',
                       fontsize=9, color='white', fontweight='bold')

    # Diagonal: show player name
    for i in range(n):
        ax.text(i, i, short[i], ha='center', va='center',
               fontsize=8, color='#9ca3af', fontweight='bold', style='italic')

    ax.set_xticks(range(n))
    ax.set_xticklabels(short, fontsize=10, color='white', fontweight='bold', rotation=45, ha='right')
    ax.set_yticks(range(n))
    ax.set_yticklabels(short, fontsize=10, color='white', fontweight='bold')

    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(axis='both', which='both', length=0)

    ax.set_title(f"Lineup Chemistry Lab — {team_code}",
                fontsize=18, color='white', fontweight='bold', pad=20, loc='left')
    fig.text(0.02, 0.96,
            "Average +/- per stint when two players share the court | Green = Chemistry | Red = Toxic",
            fontsize=10, color='#6b7280', style='italic')

    cbar = plt.colorbar(im, ax=ax, shrink=0.6, pad=0.05)
    cbar.set_label('Avg +/- Per Stint', fontsize=10, color='white')
    cbar.ax.tick_params(colors='white', labelsize=9)

    plt.tight_layout()
    out = f'chemistry_{team_code}.png'
    fig.savefig(out, dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor())
    print(f"  Saved chart to {out}")
    plt.close()


if __name__ == '__main__':
    import sys
    teams = sys.argv[1:] if len(sys.argv) > 1 else ['OLY', 'PAN']
    for team in teams:
        build_lineup_lab(team)
