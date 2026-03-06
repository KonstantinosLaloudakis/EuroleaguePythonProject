"""
Win Probability Game Replay — Replay any Euroleague game as a WP curve.
Outputs both PNG (static) and HTML (interactive Plotly).

Usage:
    python wp_replay.py <pbp_csv> <gamecode> [home_team_code]
    python wp_replay.py pbp_2011.csv 188 OLY
"""

import pandas as pd
import numpy as np
import sys
import math
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors


# ── Win Probability Model ──────────────────────────────────
def win_probability(margin, seconds_remaining, total_seconds=2400):
    """
    Estimate win probability for the leading team based on margin and time.
    Uses a logistic model calibrated to basketball dynamics.
    - margin: positive = home team leads
    - seconds_remaining: time left in regulation
    """
    if seconds_remaining <= 0:
        return 1.0 if margin > 0 else (0.0 if margin < 0 else 0.5)

    # Normalize time factor: how much of the game is remaining
    time_frac = seconds_remaining / total_seconds

    # Standard deviation of final margin scales with sqrt of remaining time
    # Calibrated empirically: ~11 point std for full game, shrinks toward 0
    sigma = 11.0 * math.sqrt(time_frac)

    if sigma == 0:
        return 1.0 if margin > 0 else (0.0 if margin < 0 else 0.5)

    # Logistic approximation of CDF
    z = margin / sigma
    wp = 1.0 / (1.0 + math.exp(-0.8 * z))

    return wp


def parse_marker_time(marker_str, period):
    """Convert MARKERTIME (MM:SS) + period to total seconds remaining."""
    if pd.isna(marker_str):
        return None
    try:
        parts = str(marker_str).split(':')
        minutes = int(parts[0])
        seconds = int(parts[1])
        # Seconds left in this period
        period_seconds_left = minutes * 60 + seconds
        # Periods remaining after this one (regulation = 4 periods of 10 min)
        if period <= 4:
            remaining_periods = 4 - period
            total_remaining = period_seconds_left + remaining_periods * 600
        else:
            # Overtime: 5 minutes
            total_remaining = period_seconds_left
        return total_remaining
    except (ValueError, IndexError):
        return None


def replay_game(pbp_file, gamecode, home_team=None):
    """Build the WP curve for a specific game."""
    df = pd.read_csv(pbp_file, low_memory=False)
    game = df[df['Gamecode'] == gamecode].sort_values('NUMBEROFPLAY').copy()

    if game.empty:
        print(f"  ERROR: No data for gamecode {gamecode}")
        return

    # Determine teams
    teams = [t for t in game['CODETEAM'].dropna().unique() if t != '']
    if len(teams) < 2:
        print(f"  ERROR: Could not find 2 teams. Found: {teams}")
        return

    # Determine home team (first team listed or user-specified)
    if home_team and home_team in teams:
        away_team = [t for t in teams if t != home_team][0]
    else:
        home_team = teams[0]
        away_team = teams[1]

    print(f"\n  Game Replay: {home_team} vs {away_team} (Gamecode {gamecode})")

    # ── Auto-detect which team is POINTS_A vs POINTS_B ─────
    # Find the first scoring play where a team's action changes a specific column
    scoring_plays = game[game['POINTS_A'].notna() & game['CODETEAM'].isin(teams)]
    team_a = None  # Which team maps to POINTS_A
    prev_a, prev_b = 0, 0
    for _, row in scoring_plays.iterrows():
        a, b = int(row['POINTS_A']), int(row['POINTS_B'])
        team = row['CODETEAM']
        if a > prev_a and b == prev_b:
            team_a = team
            break
        elif b > prev_b and a == prev_a:
            team_a = [t for t in teams if t != team][0]
            break
        prev_a, prev_b = a, b

    if team_a is None:
        team_a = teams[0]
    team_b = [t for t in teams if t != team_a][0]

    # Is home_team mapped to POINTS_A or POINTS_B?
    home_is_a = (home_team == team_a)
    print(f"  POINTS_A = {team_a}, POINTS_B = {team_b}")
    print(f"  Home team ({home_team}) is POINTS_{'A' if home_is_a else 'B'}")

    # ── Build WP timeline ──────────────────────────────────
    wp_data = []

    # Starting point: 50/50
    wp_data.append({
        'seconds_remaining': 2400,
        'elapsed': 0,
        'margin': 0,
        'wp': 0.5,
        'play_desc': 'Tip-Off',
        'player': '',
        'play_type': '',
        'score_home': 0,
        'score_away': 0,
        'period': 1,
    })

    last_score_a = 0
    last_score_b = 0

    for _, row in game.iterrows():
        pts_a = row.get('POINTS_A')
        pts_b = row.get('POINTS_B')

        # Only process rows where the score changes (scoring plays)
        if pd.isna(pts_a) or pd.isna(pts_b):
            continue

        pts_a = int(pts_a)
        pts_b = int(pts_b)

        # Skip if score hasn't changed
        if pts_a == last_score_a and pts_b == last_score_b:
            continue

        period = int(row['PERIOD']) if pd.notna(row['PERIOD']) else 1
        secs_remaining = parse_marker_time(row.get('MARKERTIME'), period)
        if secs_remaining is None:
            continue

        # Margin from home team's perspective
        if home_is_a:
            margin = pts_a - pts_b
            score_home, score_away = pts_a, pts_b
        else:
            margin = pts_b - pts_a
            score_home, score_away = pts_b, pts_a

        # Calculate WP for home team
        wp = win_probability(margin, secs_remaining)

        # Build play description
        play_type = row.get('PLAYTYPE', '')
        player = row.get('PLAYER', '')
        team = row.get('CODETEAM', '')
        play_info = row.get('PLAYINFO', '')

        desc = f"{player} ({team}) — {play_info}" if pd.notna(play_info) and pd.notna(player) else f"{player} ({team})"

        elapsed = 2400 - secs_remaining

        wp_data.append({
            'seconds_remaining': secs_remaining,
            'elapsed': elapsed,
            'margin': margin,
            'wp': wp,
            'play_desc': desc,
            'player': str(player) if pd.notna(player) else '',
            'play_type': str(play_type),
            'score_home': score_home,
            'score_away': score_away,
            'period': period,
        })

        last_score_a = pts_a
        last_score_b = pts_b

    # Add final point
    if home_is_a:
        final_home, final_away = last_score_a, last_score_b
    else:
        final_home, final_away = last_score_b, last_score_a
    final_wp = 1.0 if final_home > final_away else 0.0
    wp_data.append({
        'seconds_remaining': 0,
        'elapsed': 2400,
        'margin': final_home - final_away,
        'wp': final_wp,
        'play_desc': 'Final Buzzer',
        'player': '',
        'play_type': 'END',
        'score_home': final_home,
        'score_away': final_away,
        'period': 4,
    })

    wp_df = pd.DataFrame(wp_data)
    # Sort by elapsed time to prevent backward jumps in the graph
    wp_df = wp_df.sort_values('elapsed').reset_index(drop=True)
    print(f"  Total score changes: {len(wp_df)}")
    print(f"  Final Score: {home_team} {final_home} - {final_away} {away_team}")

    # ── Find biggest momentum swings ───────────────────────
    wp_df['wp_shift'] = wp_df['wp'].diff().fillna(0)
    biggest_swings = wp_df.nlargest(5, 'wp_shift', keep='first')
    biggest_drops = wp_df.nsmallest(5, 'wp_shift', keep='first')
    key_plays = pd.concat([biggest_swings, biggest_drops])
    key_plays = key_plays[key_plays['play_desc'] != 'Tip-Off']
    key_plays = key_plays.sort_values('elapsed')

    # ── Generate PNG ───────────────────────────────────────
    generate_png(wp_df, key_plays, home_team, away_team, gamecode)

    # ── Generate HTML ──────────────────────────────────────
    generate_html(wp_df, key_plays, home_team, away_team, gamecode)


def generate_png(wp_df, key_plays, home_team, away_team, gamecode):
    """Generate a static PNG chart."""
    fig, ax = plt.subplots(figsize=(16, 8))
    fig.patch.set_facecolor('#0f1117')
    ax.set_facecolor('#0f1117')

    elapsed = wp_df['elapsed'] / 60  # Convert to minutes
    wp = wp_df['wp'] * 100  # Convert to percentage

    # Fill above/below 50%
    ax.fill_between(elapsed, 50, wp, where=(wp >= 50),
                   color='#ef4444', alpha=0.2, interpolate=True)
    ax.fill_between(elapsed, 50, wp, where=(wp < 50),
                   color='#3b82f6', alpha=0.2, interpolate=True)

    # Main WP line
    ax.plot(elapsed, wp, color='white', linewidth=2, alpha=0.9)

    # 50% line
    ax.axhline(y=50, color='#4b5563', linewidth=1, linestyle='--', alpha=0.5)

    # Quarter markers
    for q_min in [10, 20, 30]:
        ax.axvline(x=q_min, color='#374151', linewidth=1, linestyle=':', alpha=0.5)

    # Annotate key plays (top 3 biggest swings only)
    top_annotations = key_plays.head(6)
    used_y = []
    for _, play in top_annotations.iterrows():
        x = play['elapsed'] / 60
        y = play['wp'] * 100
        shift = play['wp_shift'] * 100
        desc = play['play_desc']

        # Avoid overlapping annotations
        offset_y = 8 if y < 50 else -8
        for uy in used_y:
            if abs(y + offset_y - uy) < 10:
                offset_y = -offset_y

        if abs(shift) >= 3:  # Only annotate significant swings
            color = '#22c55e' if shift > 0 else '#ef4444'
            ax.annotate(f'{desc}\n({shift:+.1f}% WP)',
                       xy=(x, y), xytext=(x, y + offset_y),
                       fontsize=7, color=color, fontweight='bold',
                       ha='center', va='center',
                       arrowprops=dict(arrowstyle='->', color=color, lw=1),
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='#1f2937',
                                edgecolor=color, alpha=0.9))
            used_y.append(y + offset_y)

    # Labels
    ax.set_xlim(0, 40)
    ax.set_ylim(0, 100)
    ax.set_xlabel('Game Time (Minutes)', fontsize=12, color='#9ca3af', labelpad=10)
    ax.set_ylabel('Win Probability (%)', fontsize=12, color='#9ca3af', labelpad=10)
    ax.tick_params(axis='both', colors='#9ca3af', labelsize=10)

    # Quarter labels
    for q, xpos in enumerate([5, 15, 25, 35], 1):
        ax.text(xpos, 2, f'Q{q}', fontsize=10, color='#6b7280',
               ha='center', fontweight='bold')

    # Team labels on Y-axis
    ax.text(-1.5, 85, f'{home_team}', fontsize=14, color='#ef4444',
           fontweight='bold', ha='right', va='center')
    ax.text(-1.5, 15, f'{away_team}', fontsize=14, color='#3b82f6',
           fontweight='bold', ha='right', va='center')

    # Final score
    final = wp_df.iloc[-1]
    ax.text(40.5, 50, f'{int(final["score_home"])} - {int(final["score_away"])}',
           fontsize=16, color='white', fontweight='bold',
           ha='left', va='center',
           bbox=dict(boxstyle='round,pad=0.5', facecolor='#1f2937', edgecolor='#374151'))

    for spine in ax.spines.values():
        spine.set_visible(False)

    ax.grid(axis='y', color='#374151', linewidth=0.5, alpha=0.3)
    ax.set_axisbelow(True)

    ax.set_title(f"Win Probability Replay — {home_team} vs {away_team}",
                fontsize=20, color='white', fontweight='bold', pad=20, loc='left')

    plt.tight_layout()
    out = f'wp_replay_{gamecode}.png'
    fig.savefig(out, dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor())
    print(f"  Saved PNG to {out}")
    plt.close()


def generate_html(wp_df, key_plays, home_team, away_team, gamecode):
    """Generate an interactive Plotly HTML chart."""
    elapsed_min = wp_df['elapsed'] / 60
    wp_pct = wp_df['wp'] * 100

    # Helper to format seconds as MM:SS
    def fmt_time(secs):
        m, s = divmod(int(secs), 60)
        return f"{m}:{s:02d}"

    # Hover text
    hover_text = []
    for _, row in wp_df.iterrows():
        secs = row['seconds_remaining']
        time_str = fmt_time(secs) if secs > 0 else 'Final'
        txt = (f"<b>{row['play_desc']}</b><br>"
               f"Score: {int(row['score_home'])}-{int(row['score_away'])}<br>"
               f"WP: {row['wp']*100:.1f}%<br>"
               f"Q{int(row['period'])} — {time_str} remaining")
        hover_text.append(txt)

    fig = go.Figure()

    # Fill areas
    fig.add_trace(go.Scatter(
        x=elapsed_min, y=wp_pct,
        fill='tonexty', fillcolor='rgba(59,130,246,0.15)',
        line=dict(width=0), showlegend=False,
        hoverinfo='skip',
    ))
    fig.add_trace(go.Scatter(
        x=elapsed_min, y=[50]*len(elapsed_min),
        fill='tonexty', fillcolor='rgba(239,68,68,0.15)',
        line=dict(width=0), showlegend=False,
        hoverinfo='skip',
    ))

    # Main WP line
    fig.add_trace(go.Scatter(
        x=elapsed_min, y=wp_pct,
        mode='lines',
        line=dict(color='white', width=2.5),
        name='Win Probability',
        text=hover_text,
        hoverinfo='text',
    ))

    # Key plays as markers
    for _, play in key_plays.iterrows():
        shift = play['wp_shift'] * 100
        actual_wp = play['wp'] * 100
        if abs(shift) >= 3:
            color = '#22c55e' if shift > 0 else '#ef4444'
            player_short = play['player'].split(',')[0] if play['player'] else ''
            fig.add_trace(go.Scatter(
                x=[play['elapsed']/60],
                y=[actual_wp],
                mode='markers+text',
                marker=dict(size=10, color=color, symbol='circle'),
                text=[f"{player_short} — WP: {actual_wp:.1f}% ({shift:+.1f}%)"],
                textposition='top center',
                textfont=dict(size=9, color=color),
                showlegend=False,
                hovertext=f"<b>{play['play_desc']}</b><br>Win Prob: {actual_wp:.1f}%<br>WP Shift: {shift:+.1f}%<br>Score: {int(play['score_home'])}-{int(play['score_away'])}<br>Q{int(play['period'])} — {fmt_time(play['seconds_remaining'])} remaining",
                hoverinfo='text',
            ))

    # 50% line
    fig.add_hline(y=50, line_dash='dash', line_color='#4b5563', opacity=0.5)

    # Quarter lines
    for q_min in [10, 20, 30]:
        fig.add_vline(x=q_min, line_dash='dot', line_color='#374151', opacity=0.5)

    final = wp_df.iloc[-1]

    fig.update_layout(
        title=dict(
            text=f"Win Probability Replay — {home_team} vs {away_team} ({int(final['score_home'])}-{int(final['score_away'])})",
            font=dict(size=20, color='white'),
            x=0.02,
        ),
        xaxis=dict(
            title='Game Time (Minutes)',
            range=[0, 40],
            color='#9ca3af',
            gridcolor='#374151',
            tickvals=[0, 5, 10, 15, 20, 25, 30, 35, 40],
        ),
        yaxis=dict(
            title='Win Probability (%)',
            range=[0, 100],
            color='#9ca3af',
            gridcolor='#374151',
        ),
        plot_bgcolor='#0f1117',
        paper_bgcolor='#0f1117',
        font=dict(color='white'),
        showlegend=False,
        hovermode='closest',
        margin=dict(l=60, r=30, t=80, b=60),
        annotations=[
            dict(x=0, y=95, text=f'<b>{home_team}</b>', showarrow=False,
                 font=dict(size=16, color='#ef4444'), xanchor='left'),
            dict(x=0, y=5, text=f'<b>{away_team}</b>', showarrow=False,
                 font=dict(size=16, color='#3b82f6'), xanchor='left'),
        ],
    )

    out = f'wp_replay_{gamecode}.html'
    fig.write_html(out, include_plotlyjs='cdn')
    print(f"  Saved HTML to {out}")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python wp_replay.py <pbp_csv> <gamecode> [home_team]")
        print("Example: python wp_replay.py pbp_2011.csv 188 OLY")
        sys.exit(1)

    pbp_file = sys.argv[1]
    gamecode = int(sys.argv[2])
    home_team = sys.argv[3] if len(sys.argv) > 3 else None

    replay_game(pbp_file, gamecode, home_team)
