"""
Quarter-by-Quarter Performance Heatmap
Calculates net rating per quarter per team to identify Fast Starters vs Closers.
"""

import pandas as pd
import numpy as np
import json
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors


def build_quarter_heatmap():
    pbp = pd.read_csv('pbp_2025.csv', low_memory=False)
    games = pd.read_csv('data_cache/games_2025.csv', low_memory=False)
    games = games[games['played'] == True]

    # Map gamecodes
    home_map = dict(zip(games['gamenumber'], games['homecode']))
    away_map = dict(zip(games['gamenumber'], games['awaycode']))

    pbp = pbp[pbp['CODETEAM'].notna()].copy()
    # Only regulation quarters (1-4), skip OT
    pbp = pbp[pbp['PERIOD'].isin([1, 2, 3, 4])]

    # Calculate points per play
    def pts_for_play(row):
        pt = row['PLAYTYPE']
        if pt == '2FGM':
            return 2
        elif pt == '3FGM':
            return 3
        elif pt == 'FTM':
            return 1
        return 0

    pbp['PTS'] = pbp.apply(pts_for_play, axis=1)

    # Tag home/away
    pbp['IS_HOME'] = pbp.apply(
        lambda r: r['CODETEAM'] == home_map.get(r['Gamecode']), axis=1
    )

    all_teams = sorted(pbp['CODETEAM'].unique())
    results = []

    for team in all_teams:
        team_pbp = pbp[pbp['CODETEAM'] == team]
        team_gamecodes = team_pbp['Gamecode'].unique()
        n_games = len(team_gamecodes)

        if n_games == 0:
            continue

        for q in [1, 2, 3, 4]:
            # Team's points in this quarter across all games
            team_q = team_pbp[team_pbp['PERIOD'] == q]
            team_pts = team_q['PTS'].sum()

            # Opponent's points in this quarter across this team's games
            opp_q = pbp[
                (pbp['Gamecode'].isin(team_gamecodes)) &
                (pbp['CODETEAM'] != team) &
                (pbp['PERIOD'] == q)
            ]
            opp_pts = opp_q['PTS'].sum()

            # Per-game averages
            team_ppg = team_pts / n_games
            opp_ppg = opp_pts / n_games
            net = team_ppg - opp_ppg

            results.append({
                'Team': team,
                'Quarter': q,
                'TeamPPG': round(team_ppg, 1),
                'OppPPG': round(opp_ppg, 1),
                'NetRating': round(net, 1),
                'Games': n_games,
            })

    df = pd.DataFrame(results)

    # Pivot for heatmap
    pivot_net = df.pivot(index='Team', columns='Quarter', values='NetRating')
    pivot_team = df.pivot(index='Team', columns='Quarter', values='TeamPPG')
    pivot_opp = df.pivot(index='Team', columns='Quarter', values='OppPPG')

    # Sort teams by overall net rating (sum of Q1-Q4 net)
    pivot_net['Total'] = pivot_net.sum(axis=1)
    pivot_net = pivot_net.sort_values('Total', ascending=False)

    # Also add Q4 minus Q1 as "Closer Score"
    pivot_net['CloserScore'] = pivot_net[4] - pivot_net[1]

    # ── Print summary ──────────────────────────────────────────
    print("=" * 70)
    print("  QUARTER-BY-QUARTER PERFORMANCE — Euroleague 2025-26")
    print("=" * 70)
    print()
    print(f"  {'Team':<6} {'Q1':>6} {'Q2':>6} {'Q3':>6} {'Q4':>6} {'Total':>7} {'Closer':>7}")
    print(f"  {'-'*6} {'-'*6} {'-'*6} {'-'*6} {'-'*6} {'-'*7} {'-'*7}")
    for team in pivot_net.index:
        r = pivot_net.loc[team]
        print(f"  {team:<6} {r[1]:>+6.1f} {r[2]:>+6.1f} {r[3]:>+6.1f} {r[4]:>+6.1f} {r['Total']:>+7.1f} {r['CloserScore']:>+7.1f}")

    # ── Save JSON ──────────────────────────────────────────────
    output = {
        'teams': []
    }
    for team in pivot_net.index:
        output['teams'].append({
            'Team': team,
            'Q1': pivot_net.loc[team, 1],
            'Q2': pivot_net.loc[team, 2],
            'Q3': pivot_net.loc[team, 3],
            'Q4': pivot_net.loc[team, 4],
            'Total': pivot_net.loc[team, 'Total'],
            'CloserScore': pivot_net.loc[team, 'CloserScore'],
        })
    with open('quarter_performance.json', 'w') as f:
        json.dump(output, f, indent=4)
    print(f"\n  Saved data to quarter_performance.json")

    # ── Visualize ──────────────────────────────────────────────
    visualize(pivot_net)

    return pivot_net


def visualize(pivot_net):
    teams = list(pivot_net.index)
    quarters = [1, 2, 3, 4]
    n_teams = len(teams)

    # Build the data matrix
    data_matrix = np.array([[pivot_net.loc[t, q] for q in quarters] for t in teams])

    # Color scale: diverging red-white-green
    vmax = max(abs(data_matrix.min()), abs(data_matrix.max()))
    vmin = -vmax

    fig, ax = plt.subplots(figsize=(10, 12))
    fig.patch.set_facecolor('#0f1117')
    ax.set_facecolor('#0f1117')

    # Custom diverging colormap: red → dark → green
    cmap = mcolors.LinearSegmentedColormap.from_list(
        'net_rating',
        ['#ef4444', '#1f2937', '#22c55e'],
        N=256
    )

    im = ax.imshow(data_matrix, cmap=cmap, vmin=vmin, vmax=vmax, aspect='auto')

    # Annotate cells
    for i in range(n_teams):
        for j in range(4):
            val = data_matrix[i, j]
            color = 'white'
            ax.text(j, i, f'{val:+.1f}', ha='center', va='center',
                   fontsize=11, color=color, fontweight='bold')

    # Add Closer Score as a 5th column visually
    # Draw it as text to the right
    for i, team in enumerate(teams):
        closer = pivot_net.loc[team, 'CloserScore']
        total = pivot_net.loc[team, 'Total']
        color = '#22c55e' if closer > 0 else '#ef4444' if closer < 0 else '#9ca3af'
        ax.text(4.3, i, f'{closer:+.1f}', ha='center', va='center',
               fontsize=10, color=color, fontweight='bold')
        ax.text(5.3, i, f'{total:+.1f}', ha='center', va='center',
               fontsize=10, color='white', fontweight='bold')

    # Labels
    ax.set_xticks([0, 1, 2, 3, 4.3, 5.3])
    ax.set_xticklabels(['Q1', 'Q2', 'Q3', 'Q4', 'Closer\nScore', 'Total\nNet'],
                       fontsize=11, color='white', fontweight='bold')
    ax.set_yticks(range(n_teams))
    ax.set_yticklabels(teams, fontsize=12, color='white', fontweight='bold')

    # Move x-axis to top
    ax.xaxis.set_ticks_position('top')
    ax.xaxis.set_label_position('top')

    # Remove spines
    for spine in ax.spines.values():
        spine.set_visible(False)

    ax.tick_params(axis='both', which='both', length=0)

    # Title
    ax.set_title("Quarter-by-Quarter Performance — Who Are the Closers?",
                fontsize=18, color='white', fontweight='bold', pad=40, loc='left')
    fig.text(0.02, 0.96,
            "Net Rating per quarter (pts scored − pts allowed per game) | Closer Score = Q4 − Q1",
            fontsize=10, color='#6b7280', style='italic')

    # Colorbar
    cbar = plt.colorbar(im, ax=ax, shrink=0.5, pad=0.15)
    cbar.set_label('Net Rating', fontsize=10, color='white')
    cbar.ax.tick_params(colors='white', labelsize=9)

    plt.tight_layout()
    out = 'quarter_heatmap.png'
    fig.savefig(out, dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor())
    print(f"  Saved chart to {out}")
    plt.close()


if __name__ == '__main__':
    build_quarter_heatmap()
