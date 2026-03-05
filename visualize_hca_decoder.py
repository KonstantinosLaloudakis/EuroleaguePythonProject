"""
Visualize HCA Decoder v2 — Stacked horizontal bar chart with 6 components.
Positive components stack rightward from 0, negative components stack leftward.
"""

import json
import matplotlib.pyplot as plt
import numpy as np


def visualize_hca():
    with open('hca_decoder.json', 'r') as f:
        data = json.load(f)

    teams_data = data['teams']
    teams_data.sort(key=lambda x: x['NetHCA'], reverse=True)

    teams = [t['Team'] for t in teams_data]
    n = len(teams)
    y_pos = np.arange(n)

    # 6 Components: 4 offensive + 1 defensive + 1 residual
    comp_keys = ['ShootingBoost', 'WhistleAdvantage', 'BallSecurity', 'OREBBoost',
                 'DefensiveSqueeze', 'Residual']
    comp_labels = ['Shooting Boost', 'Whistle Advantage',
                   'Ball Security', 'OREB Boost',
                   'Defensive Squeeze', 'Residual']
    comp_colors = ['#3b82f6', '#f59e0b', '#22c55e', '#06b6d4',
                   '#a855f7', '#6b7280']

    fig, ax = plt.subplots(figsize=(14, 10))
    fig.patch.set_facecolor('#0f1117')
    ax.set_facecolor('#0f1117')

    bar_height = 0.6

    for i in range(n):
        pos_left = 0
        neg_left = 0

        for j, key in enumerate(comp_keys):
            val = teams_data[i][key]
            if val >= 0:
                ax.barh(y_pos[i], val, height=bar_height, left=pos_left,
                        color=comp_colors[j], edgecolor='#1f2937', linewidth=0.5, alpha=0.9)
                if val >= 2.0:
                    ax.text(pos_left + val/2, y_pos[i], f'+{val:.1f}',
                           ha='center', va='center', fontsize=7.5,
                           color='white', fontweight='bold')
                pos_left += val
            else:
                ax.barh(y_pos[i], val, height=bar_height, left=neg_left,
                        color=comp_colors[j], edgecolor='#1f2937', linewidth=0.5, alpha=0.9)
                if abs(val) >= 2.0:
                    ax.text(neg_left + val/2, y_pos[i], f'{val:.1f}',
                           ha='center', va='center', fontsize=7.5,
                           color='white', fontweight='bold')
                neg_left += val

    # Net HCA label at the right edge
    for i in range(n):
        pos_total = sum(max(0, teams_data[i][k]) for k in comp_keys)
        net = teams_data[i]['NetHCA']
        ax.text(pos_total + 0.4, y_pos[i], f'{net:+.1f}',
               ha='left', va='center', fontsize=11, color='white', fontweight='bold')

    # Vertical line at 0
    ax.axvline(x=0, color='#9ca3af', linewidth=1, linestyle='-', alpha=0.6)

    # League average line
    league_avg = data['league_avg_hca']
    ax.axvline(x=league_avg, color='#ef4444', linewidth=1.5, linestyle='--', alpha=0.7)
    ax.text(league_avg + 0.3, -0.8, f'League Avg\n{league_avg:+.1f}',
           fontsize=9, color='#ef4444', fontweight='bold', va='top')

    # Y-axis
    ax.set_yticks(y_pos)
    ax.set_yticklabels(teams, fontsize=12, color='white', fontweight='bold')
    ax.invert_yaxis()

    # X-axis
    ax.set_xlabel('Net Home Court Advantage (Points Per Game)', fontsize=12,
                 color='#9ca3af', labelpad=10)
    ax.tick_params(axis='x', colors='#9ca3af', labelsize=10)

    # Dynamic x-axis limits
    all_neg = [sum(min(0, t[k]) for k in comp_keys) for t in teams_data]
    all_pos = [sum(max(0, t[k]) for k in comp_keys) for t in teams_data]
    ax.set_xlim(min(all_neg) - 2, max(all_pos) + 4)

    # Grid
    ax.grid(axis='x', color='#374151', linewidth=0.5, alpha=0.5)
    ax.set_axisbelow(True)

    for spine in ax.spines.values():
        spine.set_visible(False)

    # Title
    ax.set_title("Home Court Decoder — What Makes Home Court Work?",
                fontsize=18, color='white', fontweight='bold', pad=20, loc='left')
    ax.text(0.0, 1.02,
           "Full decomposition: Offense (Shooting + Whistle + Ball Security + OREB) · Defense · Residual",
           transform=ax.transAxes, fontsize=11, color='#6b7280', style='italic')

    # Legend — two rows
    legend_elements = [
        plt.Rectangle((0,0), 1, 1, facecolor=comp_colors[i], label=comp_labels[i])
        for i in range(6)
    ]
    legend = ax.legend(handles=legend_elements, loc='lower right',
                      fontsize=9, framealpha=0.9, facecolor='#1f2937',
                      edgecolor='#374151', labelcolor='white',
                      ncols=3)

    plt.tight_layout()
    out_png = 'hca_decoder.png'
    fig.savefig(out_png, dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor())
    print(f"Saved to {out_png}")
    plt.close()


if __name__ == '__main__':
    visualize_hca()
