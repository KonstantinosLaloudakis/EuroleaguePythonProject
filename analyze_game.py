import argparse
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
import json
from teeter_totter import get_seconds_from_time, load_team_names

def load_game_data(season, game_code):
    """Loads PBP data and filters for the specific game"""
    pbp_file = f'pbp_{season}.csv'
    if not os.path.exists(pbp_file):
        print(f"Error: {pbp_file} not found. Run fetch_pbp.py first.")
        return None, None

    try:
        df = pd.read_csv(pbp_file, low_memory=False)
        game_df = df[df['Gamecode'] == game_code].copy()
        
        if game_df.empty:
            print(f"Error: Game {game_code} not found in {season} season data.")
            return None, None
            
        # Add seconds remaining and sort    
        if 'MARKERTIME' in game_df.columns:
             game_df['SecondsRemaining'] = game_df['MARKERTIME'].apply(get_seconds_from_time)
             # Periods usually are numbers 1-4, but could be E1, E2 for OT.
             game_df = game_df.sort_values(by=['PERIOD', 'SecondsRemaining'], ascending=[True, False])
        
        game_df['POINTS_A'] = pd.to_numeric(game_df['POINTS_A'], errors='coerce').ffill().fillna(0)
        game_df['POINTS_B'] = pd.to_numeric(game_df['POINTS_B'], errors='coerce').ffill().fillna(0)
        
        return df, game_df
    except Exception as e:
        print(f"Error loading PBP data: {e}")
        return None, None

def get_game_metadata(game_code):
    """Gets the team names and final score from mvp_game_results.json"""
    try:
        with open('mvp_game_results.json', 'r', encoding='utf-8') as f:
             games = json.load(f)
             
        for g in games:
            if g.get('GameCode') == game_code:
                return g
    except Exception as e:
        print(f"Error reading game results: {e}")
        
    return None

def get_continuous_time(period_str, seconds_remaining):
    """Converts Period and SecondsRemaining to a continuous game minute float."""
    period_str = str(period_str)
    period_map = {'1': 0, '2': 10, '3': 20, '4': 30, 'E1': 40, 'E2': 45, 'E3': 50}
    start_minute = period_map.get(period_str, 0)
    
    if period_str.startswith('E'):
         elapsed_in_period = 300 - seconds_remaining
    else:
         elapsed_in_period = 600 - seconds_remaining
         
    return start_minute + (elapsed_in_period / 60)

def generate_wp_flow(game_df, meta):
    """Generates the Win Probability / Game Flow Chart"""
    print("Generating Game Flow Visualization...")
    
    game_df = game_df.copy()
    game_df['GameTimeMinute'] = game_df.apply(lambda row: get_continuous_time(row['PERIOD'], row['SecondsRemaining']), axis=1)
    
    # Calculate Margin (Home - Away)
    game_df['Margin'] = game_df['POINTS_A'] - game_df['POINTS_B']
    
    # Determine team names
    team_names = load_team_names()
    team_a_code = game_df['CODETEAM'].dropna().unique()[0] if not game_df['CODETEAM'].dropna().empty else "Home"
    team_b_code = "Away"
    
    # Extract away team code
    away_events = game_df[game_df['CODETEAM'] != team_a_code]
    if not away_events['CODETEAM'].dropna().empty:
         team_b_code = away_events['CODETEAM'].dropna().unique()[0]
         
    # Override from meta if available
    if meta:
        team_a_code = meta.get('LocalTeam', team_a_code)
        team_b_code = meta.get('RoadTeam', team_b_code)
        
    team_a_name = team_names.get(team_a_code, team_a_code)
    team_b_name = team_names.get(team_b_code, team_b_code)
    
    final_score_a = int(game_df.iloc[-1]['POINTS_A'])
    final_score_b = int(game_df.iloc[-1]['POINTS_B'])
    
    # Setup aesthetic plot
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(16, 9))
    fig.patch.set_facecolor('#0f172a')
    ax.set_facecolor('#0f172a')
    
    # Plot areas
    ax.fill_between(game_df['GameTimeMinute'], game_df['Margin'], 0, where=(game_df['Margin'] >= 0), 
                    interpolate=True, color='#ef4444', alpha=0.3, label=f'{team_a_name} Lead')
    ax.fill_between(game_df['GameTimeMinute'], game_df['Margin'], 0, where=(game_df['Margin'] <= 0), 
                    interpolate=True, color='#3b82f6', alpha=0.3, label=f'{team_b_name} Lead')
    
    # Main line
    ax.plot(game_df['GameTimeMinute'], game_df['Margin'], color='white', linewidth=2)
    ax.axhline(0, color='white', linestyle='-', linewidth=0.5, alpha=0.4)
    
    # Add vertical lines for quarters
    for q in [10, 20, 30, 40]:
        ax.axvline(q, color='#475569', linestyle='--', alpha=0.5)
        
    # Annotate max leads
    max_lead_a = game_df['Margin'].max()
    max_lead_b = game_df['Margin'].min()
    
    if max_lead_a > 0:
        idx_a = game_df['Margin'].idxmax()
        time_a = game_df.loc[idx_a, 'GameTimeMinute']
        ax.plot(time_a, max_lead_a, marker='o', color='#ef4444', markersize=8)
        ax.text(time_a, max_lead_a + 1, f'+{int(max_lead_a)}', color='#ef4444', ha='center', fontweight='bold')
        
    if max_lead_b < 0:
        idx_b = game_df['Margin'].idxmin()
        time_b = game_df.loc[idx_b, 'GameTimeMinute']
        ax.plot(time_b, max_lead_b, marker='o', color='#3b82f6', markersize=8)
        ax.text(time_b, max_lead_b - 1.5, f'+{abs(int(max_lead_b))}', color='#3b82f6', ha='center', fontweight='bold')

    # Styling
    ax.set_title(f"{team_a_name} vs {team_b_name}\nGame Flow & Momentum", fontsize=24, color='white', fontname='Impact', pad=20)
    ax.text(0.5, 0.94, f"Final Score: {final_score_a} - {final_score_b}", transform=fig.transFigure, ha='center', color='#94a3b8', fontsize=14)
    
    ax.set_xlabel("Game Minute", fontsize=14, color='#cbd5e1', labelpad=10)
    ax.set_ylabel(f"Point Differential", fontsize=14, color='#cbd5e1', labelpad=10)
    
    # Customize tick labels
    ax.set_xticks([0, 10, 20, 30, 40])
    ax.set_xticklabels(['Q1', 'Q2', 'Q3', 'Q4', 'END'], color='#cbd5e1', fontsize=12)
    ax.tick_params(axis='y', colors='#cbd5e1')
    
    # Grid
    ax.grid(axis='y', color='#334155', linestyle=':', alpha=0.6)
    
    # Legend
    legend = ax.legend(loc='upper right', frameon=True, facecolor='#1e293b', edgecolor='#334155', fontsize=12)
    for text in legend.get_texts():
        text.set_color('white')
        
    # Add number of lead changes
    lead_changes = ((game_df['Margin'] * game_df['Margin'].shift(1)) < 0).sum()
    ax.text(0.02, 0.05, f"Lead Changes: {lead_changes}", transform=ax.transAxes, color='#fbbf24', fontsize=14, fontweight='bold',
            bbox=dict(facecolor='#1e293b', edgecolor='#fbbf24', boxstyle='round,pad=0.5'))

    plt.tight_layout()
    output_path = f"game_{meta.get('GameCode', 'X')}_flow.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"-> Saved {output_path}")

def generate_clutch_breakdown(game_df, meta):
    """Generates the Clutch Time Execution Breakdown"""
    print("Generating Clutch Execution Breakdown...")
    
    # Filter for last 5 minutes of 4th quarter or OT and score diff <= 5 AT ANY POINT in that frame
    # A simplified clutch definition: 4th Q, < 5 mins
    clutch_df = game_df[(game_df['PERIOD'].astype(str) >= '4') & (game_df['SecondsRemaining'] <= 300)].copy()
    
    if clutch_df.empty:
        print("-> No clutch time events found (game was likely a blowout).")
        return
        
    # Calculate Margin
    clutch_df['Margin'] = clutch_df['POINTS_A'] - clutch_df['POINTS_B']
    
    # Check if ever within 5 points
    if abs(clutch_df['Margin']).min() > 5:
        print("-> Game was never within 5 points during the final 5 minutes.")
        return
        
    # We have clutch time! Track key plays.
    team_names = load_team_names()
    team_a_code = meta.get('LocalTeam') if meta else clutch_df['CODETEAM'].dropna().unique()[0]
    team_a_name = team_names.get(team_a_code, team_a_code)
    
    # Extract Scoring Events in Clutch
    scoring_events = clutch_df[(clutch_df['PLAYTYPE'].str.contains('FGM', na=False)) | (clutch_df['PLAYTYPE'] == 'FTM')]
    
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(12, 8))
    fig.patch.set_facecolor('#0f172a')
    ax.set_facecolor('#0f172a')
    
    # Plot Margin over the final 5 minutes
    clutch_df['DisplayTime'] = 300 - clutch_df['SecondsRemaining'] # 0 to 300 seconds elapsed in clutch
    
    ax.plot(clutch_df['DisplayTime'], clutch_df['Margin'], color='#fbbf24', linewidth=3, zorder=2)
    ax.axhline(0, color='white', linestyle='--', linewidth=1, alpha=0.5, zorder=1)
    
    # Highlight scoring events
    for _, row in scoring_events.iterrows():
        display_time = 300 - row['SecondsRemaining']
        margin = row['Margin']
        player = str(row['PLAYER']).split(',')[0].title() if pd.notna(row['PLAYER']) else "Team"
        
        # Color based on team
        color = '#ef4444' if row['CODETEAM'] == team_a_code else '#3b82f6'
        
        ax.scatter(display_time, margin, color=color, s=100, zorder=3, edgecolor='white', linewidth=1)
        
        # Add player name context (avoiding clutter by alternating text position)
        offset = 0.5 if margin >= 0 else -0.5
        ax.annotate(f"{player}", (display_time, margin), 
                    xytext=(0, offset * 20), textcoords='offset points',
                    ha='center', va='bottom' if offset > 0 else 'top',
                    color=color, fontsize=9, rotation=45 if display_time > 200 else 0)

    # Styling
    ax.set_title(f"Clutch Time Execution (Final 5 Mins)\nGame {meta.get('GameCode', 'X')}", fontsize=22, color='white', fontname='Impact')
    
    # Convert X axis to Minute:Second format (countdown)
    labels = []
    ticks = np.linspace(0, 300, 6)
    for t in ticks:
        rem = 300 - int(t)
        m = rem // 60
        s = rem % 60
        labels.append(f"{m}:{s:02d}")
        
    ax.set_xticks(ticks)
    ax.set_xticklabels(labels, color='#cbd5e1', fontsize=11)
    ax.set_xlim(-10, 310)
    
    ax.set_xlabel("Time Remaining", fontsize=12, color='#cbd5e1')
    ax.set_ylabel(f"Point Differential ({team_a_name} +)", fontsize=12, color='#cbd5e1')
    ax.grid(alpha=0.2)

    plt.tight_layout()
    output_path = f"game_{meta.get('GameCode', 'X')}_clutch_breakdown.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"-> Saved {output_path}")

def generate_player_impact(game_df, meta):
    """Generates the Single-Game Player Impact Quadrant"""
    print("Generating Player Impact Quadrant...")
    
    player_events = game_df[pd.notna(game_df['PLAYER'])].copy()
    if player_events.empty:
        return
        
    team_names = load_team_names()
    team_a_code = meta.get('LocalTeam') if meta else game_df['CODETEAM'].dropna().unique()[0]
    
    stats = []
    
    for player, pdf in player_events.groupby('PLAYER'):
        pts = 0
        hustle = 0
        team_code = pdf['CODETEAM'].iloc[0]
        
        # Calculate Points
        pts += len(pdf[pdf['PLAYTYPE'] == '2FGM']) * 2
        pts += len(pdf[pdf['PLAYTYPE'] == '3FGM']) * 3
        pts += len(pdf[pdf['PLAYTYPE'] == 'FTM']) * 1
        
        # Calculate Hustle/Playmaking (Rebounds, Assists, Steals)
        hustle += len(pdf[pdf['PLAYTYPE'] == 'D'])
        hustle += len(pdf[pdf['PLAYTYPE'] == 'O'])
        hustle += len(pdf[pdf['PLAYTYPE'] == 'AS'])
        hustle += len(pdf[pdf['PLAYTYPE'] == 'ST'])
        
        name_parts = str(player).split(',')
        clean_name = name_parts[0].title() if len(name_parts) > 0 else str(player)
        
        if pts > 0 or hustle > 0:
            stats.append({
                'Player': clean_name,
                'Team': team_code,
                'Points': pts,
                'Hustle': hustle
            })
            
    if not stats:
        return
        
    stats_df = pd.DataFrame(stats)
    
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(12, 10))
    fig.patch.set_facecolor('#0f172a')
    ax.set_facecolor('#0f172a')
    
    # Calculate medians for quadrant lines
    median_pts = stats_df['Points'].median()
    median_hustle = stats_df['Hustle'].median()
    
    ax.axhline(median_hustle, color='#475569', linestyle='--', alpha=0.5)
    ax.axvline(median_pts, color='#475569', linestyle='--', alpha=0.5)
    
    # Plot points
    for _, row in stats_df.iterrows():
        color = '#ef4444' if row['Team'] == team_a_code else '#3b82f6'
        
        ax.scatter(row['Points'], row['Hustle'], color=color, s=150, zorder=3, edgecolor='white', linewidth=1, alpha=0.8)
        
        # Jitter text slightly to avoid overlap
        jitter_x = np.random.uniform(-0.3, 0.3)
        jitter_y = np.random.uniform(0.1, 0.4)
        ax.annotate(row['Player'], (row['Points'] + jitter_x, row['Hustle'] + jitter_y), 
                    color='white', fontsize=10, ha='center')

    # Add quadrant labels
    ax.text(ax.get_xlim()[1]*0.95, ax.get_ylim()[1]*0.95, 'High Volume / High Hustle', 
            color='#10b981', ha='right', va='top', fontsize=12, alpha=0.6, fontweight='bold')
    ax.text(ax.get_xlim()[1]*0.95, ax.get_ylim()[0] + 0.5, 'Scoring Specialists', 
            color='#fbbf24', ha='right', va='bottom', fontsize=12, alpha=0.6, fontweight='bold')
    ax.text(ax.get_xlim()[0] + 0.5, ax.get_ylim()[1]*0.95, 'Role Players / Glue Guys', 
            color='#fbbf24', ha='left', va='top', fontsize=12, alpha=0.6, fontweight='bold')
            
    # Title & Labels
    team_a_name = team_names.get(team_a_code, team_a_code)
    team_b_code = stats_df[stats_df['Team'] != team_a_code]['Team'].iloc[0] if len(stats_df['Team'].unique()) > 1 else "Opponent"
    team_b_name = team_names.get(team_b_code, team_b_code)
    
    ax.set_title(f"Player Impact Quadrant\n{team_a_name} vs {team_b_name} (Game {meta.get('GameCode', 'X')})", fontsize=20, color='white', fontname='Impact', pad=20)
    ax.set_xlabel("Offensive Production (Points)", fontsize=14, color='#cbd5e1')
    ax.set_ylabel("Playmaking & Hustle (REB + AST + STL)", fontsize=14, color='#cbd5e1')
    
    # Custom legend
    from matplotlib.lines import Line2D
    custom_lines = [Line2D([0], [0], marker='o', color='w', markerfacecolor='#ef4444', markersize=10),
                    Line2D([0], [0], marker='o', color='w', markerfacecolor='#3b82f6', markersize=10)]
    ax.legend(custom_lines, [team_a_name, team_b_name], loc='upper left', frameon=True, facecolor='#1e293b', edgecolor='#334155', fontsize=12)

    ax.grid(alpha=0.2)
    plt.tight_layout()
    output_path = f"game_{meta.get('GameCode', 'X')}_player_impact.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"-> Saved {output_path}")

def generate_quarter_momentum(game_df, meta):
    """Generates the Quarter-by-Quarter Momentum Surge chart"""
    print("Generating Quarter-by-Quarter Momentum...")
    
    # Calculate end of period scores
    q_scores = game_df.groupby('PERIOD')[['POINTS_A', 'POINTS_B']].max().reset_index()
    
    # Calculate diffs (points scored in that quarter)
    q_scores['Q_PTS_A'] = q_scores['POINTS_A'].diff().fillna(q_scores['POINTS_A'])
    q_scores['Q_PTS_B'] = q_scores['POINTS_B'].diff().fillna(q_scores['POINTS_B'])
    
    # Need to distinguish regular periods from OT
    q_scores['Period_Name'] = q_scores['PERIOD'].apply(lambda x: f"Q{x}" if str(x).isdigit() else x)
    
    q_scores['Margin'] = q_scores['Q_PTS_A'] - q_scores['Q_PTS_B']
    
    team_names = load_team_names()
    team_a_code = meta.get('LocalTeam') if meta else game_df['CODETEAM'].dropna().unique()[0]
    
    # Extract opponent Code
    away_events = game_df[game_df['CODETEAM'] != team_a_code]
    team_b_code = "Away"
    if not away_events['CODETEAM'].dropna().empty:
         team_b_code = away_events['CODETEAM'].dropna().unique()[0]
    
    team_a_name = team_names.get(team_a_code, team_a_code)
    team_b_name = team_names.get(team_b_code, team_b_code)

    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(12, 7))
    fig.patch.set_facecolor('#0f172a')
    ax.set_facecolor('#0f172a')

    # Create bars
    colors = ['#ef4444' if m >= 0 else '#3b82f6' for m in q_scores['Margin']]
    bars = ax.bar(q_scores['Period_Name'], q_scores['Margin'], color=colors, width=0.6, edgecolor='white', linewidth=1)
    
    # Add text labels
    for bar, m, a_pts, b_pts in zip(bars, q_scores['Margin'], q_scores['Q_PTS_A'], q_scores['Q_PTS_B']):
        y_pos = bar.get_height()
        offset = 1 if y_pos >= 0 else -2
        
        # Quarter score label
        score_text = f"{int(a_pts)}-{int(b_pts)}"
        
        # Margin label
        margin_text = f"+{int(abs(m))}"
        
        ax.text(bar.get_x() + bar.get_width()/2., y_pos + offset, f"{margin_text}\n({score_text})", 
                ha='center', va='bottom' if y_pos >=0 else 'top', color='white', fontsize=11, fontweight='bold')

    ax.axhline(0, color='white', linestyle='-', linewidth=2)
    
    # Title & Labels
    ax.set_title(f"Quarter-by-Quarter Momentum\n{team_a_name} vs {team_b_name} (Game {meta.get('GameCode', 'X')})", fontsize=20, color='white', fontname='Impact', pad=20)
    ax.set_ylabel(f"Quarter Net Margin ({team_a_name} +)", fontsize=14, color='#cbd5e1')
    
    # Limit y axis to avoid cutting off text
    max_abs_margin = abs(q_scores['Margin']).max()
    if pd.notna(max_abs_margin):
        ax.set_ylim(-max_abs_margin - 5, max_abs_margin + 5)
    
    # Custom legend
    from matplotlib.lines import Line2D
    custom_lines = [Line2D([0], [0], color='#ef4444', lw=8),
                    Line2D([0], [0], color='#3b82f6', lw=8)]
    ax.legend(custom_lines, [team_a_name, team_b_name], loc='upper right', frameon=True, facecolor='#1e293b', edgecolor='#334155', fontsize=12)

    plt.tight_layout()
    output_path = f"game_{meta.get('GameCode', 'X')}_quarter_momentum.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"-> Saved {output_path}")

def generate_rotation_timeline(game_df, meta):
    """Generates the Player Rotation Timeline (Gantt Chart) overlaid with Score Margin"""
    print("Generating Player Rotation Timeline...")
    
    # 1. Determine Team Names & Codes
    team_names = load_team_names()
    team_a_code = meta.get('LocalTeam') if meta else game_df['CODETEAM'].dropna().unique()[0]
    away_events = game_df[game_df['CODETEAM'] != team_a_code]
    team_b_code = "Away"
    if not away_events['CODETEAM'].dropna().empty:
         team_b_code = away_events['CODETEAM'].dropna().unique()[0]
         
    team_a_name = team_names.get(team_a_code, team_a_code)
    team_b_name = team_names.get(team_b_code, team_b_code)

    # 2. Extract Sub Events
    sub_df = game_df[game_df['PLAYTYPE'].isin(['IN', 'OUT'])].copy()
    
    if sub_df.empty:
        print("-> No IN/OUT substitution data found in PBP.")
        return
        
    sub_df['GameTimeMinute'] = sub_df.apply(lambda row: get_continuous_time(row['PERIOD'], row['SecondsRemaining']), axis=1)
    
    # Calculate Margin at every point in the game
    game_df_cont = game_df.copy()
    game_df_cont['GameTimeMinute'] = game_df_cont.apply(lambda row: get_continuous_time(row['PERIOD'], row['SecondsRemaining']), axis=1)
    game_df_cont['Margin'] = game_df_cont['POINTS_A'] - game_df_cont['POINTS_B']
    
    # 3. Build Player Shifts
    shifts = []
    
    # We need to figure out who started. 
    # Let's find all players who have a stat (or OUT event) before their first IN event, or are IN at minute 0.
    players_seen = set()
    active_shifts = {} # player: start_time
    
    for _, row in game_df_cont.iterrows():
        player = str(row['PLAYER']) if pd.notna(row['PLAYER']) else None
        if not player: continue
        
        team = row['CODETEAM']
        time = row['GameTimeMinute']
        ptype = row['PLAYTYPE']
        
        # Format name
        name_parts = player.split(',')
        clean_name = name_parts[0].title() if len(name_parts) > 0 else player
        
        # If this is a substitution
        if ptype == 'IN':
            active_shifts[clean_name] = time
            players_seen.add(clean_name)
        elif ptype == 'OUT':
            # If they were out but we didn't see an IN, they were starters.
            start_time = active_shifts.get(clean_name, 0.0) 
            shifts.append({
                'Player': clean_name,
                'Team': team,
                'Start': start_time,
                'End': time
            })
            if clean_name in active_shifts:
                del active_shifts[clean_name]
            players_seen.add(clean_name)
        else:
            # A normal stat. If not seen, they are a starter.
            if clean_name not in players_seen and clean_name not in active_shifts:
                active_shifts[clean_name] = 0.0
                players_seen.add(clean_name)
                
    # Close any open shifts at the end of the game
    max_time = game_df_cont['GameTimeMinute'].max()
    for player, start_time in active_shifts.items():
        # Need to find team for this player
        team = game_df_cont[game_df_cont['PLAYER'].str.contains(player.upper(), na=False)]['CODETEAM'].iloc[0] if len(game_df_cont[game_df_cont['PLAYER'].str.contains(player.upper(), na=False)]) > 0 else "Unknown"
        shifts.append({
            'Player': player,
            'Team': team,
            'Start': start_time,
            'End': max_time
        })
        
    shifts_df = pd.DataFrame(shifts)
    if shifts_df.empty:
        return
        
    # Standardize names and order by team then by total minutes
    shifts_df['Duration'] = shifts_df['End'] - shifts_df['Start']
    player_totals = shifts_df.groupby(['Player', 'Team'])['Duration'].sum().reset_index()
    player_totals = player_totals.sort_values(by=['Team', 'Duration'], ascending=[True, True])
    
    ordered_players = player_totals['Player'].tolist()
    
    # 4. Plot
    plt.style.use('dark_background')
    fig, (ax_gantt, ax_margin) = plt.subplots(2, 1, figsize=(16, 14), gridspec_kw={'height_ratios': [3, 1]}, sharex=True)
    fig.patch.set_facecolor('#0f172a')
    ax_gantt.set_facecolor('#0f172a')
    ax_margin.set_facecolor('#0f172a')
    
    # Plot Gantt lines
    for _, row in shifts_df.iterrows():
        y_pos = ordered_players.index(row['Player'])
        color = '#ef4444' if row['Team'] == team_a_code else '#3b82f6'
        
        ax_gantt.barh(y_pos, row['Duration'], left=row['Start'], color=color, alpha=0.8, edgecolor='white', height=0.6)

    ax_gantt.set_yticks(range(len(ordered_players)))
    ax_gantt.set_yticklabels(ordered_players, color='#cbd5e1', fontsize=11)
    
    # Draw quarter markers on Gantt
    for q in [10, 20, 30, 40]:
        ax_gantt.axvline(q, color='#475569', linestyle=':', alpha=0.5)
        ax_margin.axvline(q, color='#475569', linestyle=':', alpha=0.5)

    ax_gantt.set_title(f"Player Rotation Timeline\n{team_a_name} vs {team_b_name} (Game {meta.get('GameCode', 'X')})", fontsize=22, color='white', fontname='Impact')
    ax_gantt.grid(axis='x', alpha=0.2)
    
    # Plot Margin on bottom axis
    ax_margin.fill_between(game_df_cont['GameTimeMinute'], game_df_cont['Margin'], 0, where=(game_df_cont['Margin'] >= 0), 
                    interpolate=True, color='#ef4444', alpha=0.4)
    ax_margin.fill_between(game_df_cont['GameTimeMinute'], game_df_cont['Margin'], 0, where=(game_df_cont['Margin'] <= 0), 
                    interpolate=True, color='#3b82f6', alpha=0.4)
    ax_margin.plot(game_df_cont['GameTimeMinute'], game_df_cont['Margin'], color='white', linewidth=1.5)
    ax_margin.axhline(0, color='white', linestyle='--', linewidth=0.8)
    
    ax_margin.set_xlabel("Game Minute", fontsize=14, color='#cbd5e1')
    ax_margin.set_ylabel("Score Margin", fontsize=12, color='#cbd5e1')
    ax_margin.set_xticks([0, 10, 20, 30, 40])
    ax_margin.set_xticklabels(['Q1', 'Q2', 'Q3', 'Q4', 'END'], color='#cbd5e1', fontsize=12)
    ax_margin.grid(alpha=0.2)
    
    # Alignment lines between subplots
    from matplotlib.transforms import Bbox
    
    plt.tight_layout()
    plt.subplots_adjust(hspace=0.05)
    output_path = f"game_{meta.get('GameCode', 'X')}_rotation_timeline.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"-> Saved {output_path}")

def generate_scoring_runs(game_df, meta):
    """Pinpoints massive scoring runs (e.g. 10-0 run over 3 minutes)"""
    print("Generating Scoring Runs Heatmap...")
    
    game_df = game_df.copy()
    game_df['GameTimeMinute'] = game_df.apply(lambda row: get_continuous_time(row['PERIOD'], row['SecondsRemaining']), axis=1)
    
    # Determine team names
    team_names = load_team_names()
    team_a_code = meta.get('LocalTeam') if meta else game_df['CODETEAM'].dropna().unique()[0]
    away_events = game_df[game_df['CODETEAM'] != team_a_code]
    team_b_code = away_events['CODETEAM'].dropna().unique()[0] if not away_events['CODETEAM'].dropna().empty else "Away"
         
    team_a_name = team_names.get(team_a_code, team_a_code)
    team_b_name = team_names.get(team_b_code, team_b_code)

    # State Machine to track unanswered runs
    runs = []
    
    current_run_team = None
    run_pts = 0
    run_start_time = 0.0
    run_start_margin = 0
    
    for i in range(len(game_df)):
        row = game_df.iloc[i]
        
        # Get point delta
        pt_a_diff = row['POINTS_A'] - (game_df.iloc[i-1]['POINTS_A'] if i > 0 else 0)
        pt_b_diff = row['POINTS_B'] - (game_df.iloc[i-1]['POINTS_B'] if i > 0 else 0)
        
        scoring_team = None
        pts = 0
        if pt_a_diff > 0:
            scoring_team = team_a_code
            pts = pt_a_diff
        elif pt_b_diff > 0:
            scoring_team = team_b_code
            pts = pt_b_diff
            
        if scoring_team:
            if current_run_team == scoring_team:
                run_pts += pts
            else:
                # Run broken! Save previous run if it's significant (>= 8 points)
                if run_pts >= 8:
                    margin = game_df.iloc[i-1]['POINTS_A'] - game_df.iloc[i-1]['POINTS_B']
                    runs.append({
                        'Team': current_run_team,
                        'Start': run_start_time,
                        'End': game_df.iloc[i-1]['GameTimeMinute'],
                        'Points': run_pts,
                        'StartMargin': run_start_margin,
                        'EndMargin': margin
                    })
                # Start new run
                current_run_team = scoring_team
                run_pts = pts
                run_start_time = game_df.iloc[i-1]['GameTimeMinute'] if i > 0 else row['GameTimeMinute']
                run_start_margin = (game_df.iloc[i-1]['POINTS_A'] - game_df.iloc[i-1]['POINTS_B']) if i > 0 else 0
                
    # Check end of game run
    if run_pts >= 8:
        runs.append({
            'Team': current_run_team,
            'Start': run_start_time,
            'End': game_df.iloc[-1]['GameTimeMinute'],
            'Points': run_pts,
            'StartMargin': run_start_margin,
            'EndMargin': game_df.iloc[-1]['POINTS_A'] - game_df.iloc[-1]['POINTS_B']
        })
        
    runs_df = pd.DataFrame(runs)
    
    if runs_df.empty:
        print("-> No significant scoring runs (8+ points unanswered) detected.")
        return
        
    # Plot
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(14, 8))
    fig.patch.set_facecolor('#0f172a')
    ax.set_facecolor('#0f172a')
    
    game_df['Margin'] = game_df['POINTS_A'] - game_df['POINTS_B']
    
    # Plot Flow in background
    ax.plot(game_df['GameTimeMinute'], game_df['Margin'], color='#475569', linewidth=2, alpha=0.5)
    ax.axhline(0, color='white', linestyle='--', linewidth=0.8, alpha=0.5)
    
    # Highlight Runs
    for _, run in runs_df.iterrows():
        color = '#ef4444' if run['Team'] == team_a_code else '#3b82f6'
        
        # Draw bounding box for the run
        width = max(run['End'] - run['Start'], 0.5) # ensure visible width
        min_y = min(run['StartMargin'], run['EndMargin'])
        max_y = max(run['StartMargin'], run['EndMargin'])
        height = max(max_y - min_y, 2)
        
        from matplotlib.patches import Rectangle
        rect = Rectangle((run['Start'], min_y), width, height, 
                         facecolor=color, alpha=0.3, edgecolor=color, linewidth=2)
        ax.add_patch(rect)
        
        # Add Text
        run_text = f"{int(run['Points'])}-0 Run"
        text_y = max_y + 1 if run['Team'] == team_a_code else min_y - 2
        ax.text((run['Start'] + run['End']) / 2, text_y, run_text, 
                color=color, ha='center', fontweight='bold', fontsize=12,
                bbox=dict(facecolor='#1e293b', edgecolor=color, boxstyle='round,pad=0.3'))
                
    # Title & Format
    ax.set_title(f"Major Scoring Runs (8+ Unanswered Points)\n{team_a_name} vs {team_b_name} (Game {meta.get('GameCode', 'X')})", fontsize=22, color='white', fontname='Impact')
    
    ax.set_xlabel("Game Minute", fontsize=14, color='#cbd5e1')
    ax.set_ylabel(f"Point Differential ({team_a_name} +)", fontsize=14, color='#cbd5e1')
    
    ax.set_xticks([0, 10, 20, 30, 40])
    ax.set_xticklabels(['Q1', 'Q2', 'Q3', 'Q4', 'END'], color='#cbd5e1', fontsize=12)
    ax.grid(alpha=0.1)

    plt.tight_layout()
    output_path = f"game_{meta.get('GameCode', 'X')}_scoring_runs.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"-> Saved {output_path}")

def generate_top_lineups(game_df, meta):
    """Calculates and visualizes the best and worst 5-man lineups for the game"""
    print("Generating Top 5-Man Lineups Tracker...")
    
    # 1. Determine Team Names
    team_names = load_team_names()
    team_a_code = meta.get('LocalTeam') if meta else game_df['CODETEAM'].dropna().unique()[0]
    away_events = game_df[game_df['CODETEAM'] != team_a_code]
    team_b_code = away_events['CODETEAM'].dropna().unique()[0] if not away_events['CODETEAM'].dropna().empty else "Away"
         
    team_a_name = team_names.get(team_a_code, team_a_code)
    team_b_name = team_names.get(team_b_code, team_b_code)

    game_df_cont = game_df.copy()
    game_df_cont['GameTimeMinute'] = game_df_cont.apply(lambda row: get_continuous_time(row['PERIOD'], row['SecondsRemaining']), axis=1)
    
    # We will track the exact 5 guys on the floor for each team at any given time.
    active_lineups = {team_a_code: set(), team_b_code: set()}
    lineup_stints = [] # {team, lineup_tuple, start_time, start_pts_for, start_pts_against}
    
    # We must deduce starters first exactly like the Gantt chart
    players_seen = set()
    active_shifts = {}
    starters = set()
    
    # Store the exact team mapping per parsed player name
    player_teams = {}
    
    for i in range(len(game_df_cont)):
        row = game_df_cont.iloc[i]
        player = str(row['PLAYER']) if pd.notna(row['PLAYER']) else None
        if not player: continue
        
        team = row['CODETEAM']
        time = row['GameTimeMinute']
        ptype = row['PLAYTYPE']
        name_parts = player.split(',')
        clean_name = name_parts[0].title() if len(name_parts) > 0 else player
        
        player_teams[clean_name] = team
        
        if ptype == 'IN':
            active_shifts[clean_name] = time
            players_seen.add(clean_name)
        elif ptype == 'OUT':
            if clean_name not in active_shifts:
                # Was a starter
                starters.add(clean_name)
            else:
                del active_shifts[clean_name]
            players_seen.add(clean_name)
        else:
            if clean_name not in players_seen and clean_name not in active_shifts:
                starters.add(clean_name)
                active_shifts[clean_name] = 0.0
                players_seen.add(clean_name)
                
    # Now we know exactly who the 10 starters were
    for p in starters:
        p_team = player_teams.get(p)
        if p_team in active_lineups:
            active_lineups[p_team].add(p)
                
    # Track the stints
    current_stint_a = {'lineup': frozenset(active_lineups[team_a_code]), 'start_time': 0.0, 'pts_for': 0, 'pts_against': 0}
    current_stint_b = {'lineup': frozenset(active_lineups[team_b_code]), 'start_time': 0.0, 'pts_for': 0, 'pts_against': 0}
    
    stints_log = []
    
    for i in range(len(game_df_cont)):
        row = game_df_cont.iloc[i]
        time = row['GameTimeMinute']
        ptype = row['PLAYTYPE']
        team = row['CODETEAM']
        pts_a = row['POINTS_A']
        pts_b = row['POINTS_B']
        
        player = str(row['PLAYER']) if pd.notna(row['PLAYER']) else None
        if not player: continue
        name_parts = player.split(',')
        clean_name = name_parts[0].title() if len(name_parts) > 0 else player
        
        if ptype in ['IN', 'OUT']:
            # Close out current stint for this team
            if team == team_a_code:
                stints_log.append({
                    'Team': team_a_code,
                    'Lineup': current_stint_a['lineup'],
                    'Duration': time - current_stint_a['start_time'],
                    'PtsFor': pts_a - current_stint_a['pts_for'],
                    'PtsAgainst': pts_b - current_stint_a['pts_against']
                })
                
                # Update on-floor personnel
                if ptype == 'IN': active_lineups[team_a_code].add(clean_name)
                if ptype == 'OUT' and clean_name in active_lineups[team_a_code]: active_lineups[team_a_code].remove(clean_name)
                
                # Start new stint
                current_stint_a = {'lineup': frozenset(active_lineups[team_a_code]), 'start_time': time, 'pts_for': pts_a, 'pts_against': pts_b}
                
            elif team == team_b_code:
                stints_log.append({
                    'Team': team_b_code,
                    'Lineup': current_stint_b['lineup'],
                    'Duration': time - current_stint_b['start_time'],
                    'PtsFor': pts_b - current_stint_b['pts_for'],
                    'PtsAgainst': pts_a - current_stint_b['pts_against']
                })
                
                if ptype == 'IN': active_lineups[team_b_code].add(clean_name)
                if ptype == 'OUT' and clean_name in active_lineups[team_b_code]: active_lineups[team_b_code].remove(clean_name)
                
                current_stint_b = {'lineup': frozenset(active_lineups[team_b_code]), 'start_time': time, 'pts_for': pts_b, 'pts_against': pts_a}

        # Update scores continuously so the end-of-game stint records correctly
        if team == team_a_code or team == team_b_code: # Basically any event
            if 'pts_a_rolling' not in locals(): pts_a_rolling = pts_a; pts_b_rolling = pts_b
            pts_a_rolling = pts_a
            pts_b_rolling = pts_b

    # Close the final stints at the final buzzer
    final_time = game_df_cont['GameTimeMinute'].iloc[-1]
    stints_log.append({
        'Team': team_a_code, 'Lineup': current_stint_a['lineup'],
        'Duration': final_time - current_stint_a['start_time'],
        'PtsFor': pts_a_rolling - current_stint_a['pts_for'],
        'PtsAgainst': pts_b_rolling - current_stint_a['pts_against']
    })
    stints_log.append({
        'Team': team_b_code, 'Lineup': current_stint_b['lineup'],
        'Duration': final_time - current_stint_b['start_time'],
        'PtsFor': pts_b_rolling - current_stint_b['pts_for'],
        'PtsAgainst': pts_a_rolling - current_stint_b['pts_against']
    })
    
    stints_df = pd.DataFrame(stints_log)
    if stints_df.empty: return
    
    # Aggregate by unique exact lineup
    stints_df['LineupStr'] = stints_df['Lineup'].apply(lambda x: " + ".join(sorted(list(x))))
    
    lineups_agg = stints_df.groupby(['Team', 'LineupStr']).agg({
        'Duration': 'sum', 'PtsFor': 'sum', 'PtsAgainst': 'sum'
    }).reset_index()
    
    lineups_agg['NetMargin'] = lineups_agg['PtsFor'] - lineups_agg['PtsAgainst']
    
    # Filter for lineups that played at least 2 minutes (120 seconds = 2.0 float)
    lineups_agg = lineups_agg[lineups_agg['Duration'] >= 2.0]
    
    if lineups_agg.empty:
        print("-> No lineups met the 2 minute minimum threshold.")
        return
        
    lineups_agg = lineups_agg.sort_values(by='NetMargin', ascending=True)
    
    top_lineups = pd.concat([lineups_agg.head(5), lineups_agg.tail(5)]).drop_duplicates()
    
    # Export to JSON
    json_path = f"game_{meta.get('GameCode', 'X')}_top_lineups.json"
    json_export_df = top_lineups.copy()
    
    # Convert lineup items into arrays instead of long string
    json_export_df['Lineup'] = json_export_df['LineupStr'].apply(lambda x: x.split(" + "))
    
    # Only keep essential fields
    json_export_df = json_export_df[['Team', 'Lineup', 'Duration', 'PtsFor', 'PtsAgainst', 'NetMargin']]
    # Rename to be more JSON friendly
    json_export_df = json_export_df.rename(columns={'Duration': 'MinutesPlayed'})
    
    # Round minutes to 1 decimal
    json_export_df['MinutesPlayed'] = json_export_df['MinutesPlayed'].round(1)
    
    # Convert explicitly to primitive types to ensure clean JSON format
    json_dict = json_export_df.to_dict(orient='records')
    
    import json
    with open(json_path, 'w') as f:
        json.dump(json_dict, f, indent=4)
    print(f"-> Saved {json_path}")
    
    # Plotting
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(14, 10))
    fig.patch.set_facecolor('#0f172a')
    ax.set_facecolor('#0f172a')
    
    colors = ['#3b82f6' if team==team_b_code else '#ef4444' for team in top_lineups['Team']]
    
    # Make names shorter by taking only last names if possible to fit
    def shorten_lineup(l_str):
        names = l_str.split(' + ')
        # Some euroleague names have multiple parts, safely take the last word
        short = [n.split(' ')[-1][:7] for n in names] # Trim to 7 chars max per name
        
        # Split into two lines: 3 players on top, 2 on the bottom
        top_line = " + ".join(short[:3])
        bottom_line = " + ".join(short[3:])
        return f"{top_line}\n+ {bottom_line}"
        
    y_labels = top_lineups['LineupStr'].apply(shorten_lineup)
    
    # Adjust axes spacing dynamically to fit longer names
    plt.subplots_adjust(left=0.20)
    
    bars = ax.barh(y_labels, top_lineups['NetMargin'], color=colors, edgecolor='white', linewidth=1, alpha=0.9)
    
    ax.axvline(0, color='white', linestyle='-', linewidth=2)
    
    # We want to dynamically scale the x-axis to ensure labels don't get cutoff
    max_margin = top_lineups['NetMargin'].abs().max() + 5
    ax.set_xlim(-max_margin, max_margin)
    
    # Add labels
    for bar, duration, team in zip(bars, top_lineups['Duration'], top_lineups['Team']):
        width = bar.get_width()
        x_offset = max_margin * 0.02 if width >= 0 else -max_margin * 0.02
        
        metrics = f"{int(width)} ({int(duration)}m)"
        ax.text(width + x_offset, bar.get_y() + bar.get_height()/2, metrics, 
                ha='left' if width >= 0 else 'right', va='center', color='white', fontweight='bold', fontsize=11)
                
    # Title & Labels
    ax.set_title(f"Top 5-Man Lineups by Net Margin (Min. 2 mins)\n{team_a_name} vs {team_b_name} (Game {meta.get('GameCode', 'X')})", fontsize=20, color='white', fontname='Impact', pad=20)
    ax.set_xlabel("Net Margin (+/-) while on floor", fontsize=14, color='#cbd5e1')
    
    # Custom legend
    from matplotlib.lines import Line2D
    custom_lines = [Line2D([0], [0], color='#ef4444', lw=8),
                    Line2D([0], [0], color='#3b82f6', lw=8)]
    ax.legend(custom_lines, [team_a_name, team_b_name], loc='lower right', frameon=True, facecolor='#1e293b', edgecolor='#334155', fontsize=12)

    ax.grid(axis='x', alpha=0.2)
    plt.tight_layout()
    output_path = f"game_{meta.get('GameCode', 'X')}_top_lineups.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"-> Saved {output_path}")

def generate_four_factors(game_df, meta):
    """Calculates and visualizes the Four Factors on an overlapping Radar Chart"""
    print("Generating The Four Factors Radar Battle...")
    
    # 1. Determine Team Names
    team_names = load_team_names()
    team_a_code = meta.get('LocalTeam') if meta else game_df['CODETEAM'].dropna().unique()[0]
    away_events = game_df[game_df['CODETEAM'] != team_a_code]
    team_b_code = away_events['CODETEAM'].dropna().unique()[0] if not away_events['CODETEAM'].dropna().empty else "Away"
         
    team_a_name = team_names.get(team_a_code, team_a_code)
    team_b_name = team_names.get(team_b_code, team_b_code)

    stats = {
        team_a_code: {'2FGM': 0, '2FGA': 0, '3FGM': 0, '3FGA': 0, 'FTA': 0, 'TO': 0, 'ORB': 0, 'DRB': 0},
        team_b_code: {'2FGM': 0, '2FGA': 0, '3FGM': 0, '3FGA': 0, 'FTA': 0, 'TO': 0, 'ORB': 0, 'DRB': 0}
    }
    
    # Simple aggregates
    for _, row in game_df.iterrows():
        team = row['CODETEAM']
        ptype = row['PLAYTYPE']
        
        if team not in stats: continue
        
        if ptype == '2FGM': stats[team]['2FGM'] += 1; stats[team]['2FGA'] += 1
        elif ptype == '2FGA': stats[team]['2FGA'] += 1
        elif ptype == '3FGM': stats[team]['3FGM'] += 1; stats[team]['3FGA'] += 1
        elif ptype == '3FGA': stats[team]['3FGA'] += 1
        elif ptype == 'FTA': stats[team]['FTA'] += 1
        elif ptype == 'FTM': stats[team]['FTA'] += 1 # Some leagues count misses and makes, we count both as attempts
        elif ptype == 'TO': stats[team]['TO'] += 1
        elif ptype == 'O': stats[team]['ORB'] += 1
        elif ptype == 'D': stats[team]['DRB'] += 1
        
    # We must fix FTA duplicates. In PBP, an FTM implies an attempt. 
    # Usually in Euroleague Data, FTM and FTA represent makes and misses separately.
    # Therefore Total FTA = FTM + FTA events. We already did this above.
    
    factors = {team_a_code: {}, team_b_code: {}}
    
    for team in [team_a_code, team_b_code]:
        s = stats[team]
        opp_team = team_b_code if team == team_a_code else team_a_code
        opp_s = stats[opp_team]
        
        FGA = s['2FGA'] + s['3FGA']
        
        # 1. Effective Field Goal Percentage (eFG%)
        factors[team]['eFG%'] = ((s['2FGM'] + 1.5 * s['3FGM']) / FGA) * 100 if FGA > 0 else 0
        
        # 2. Turnover Percentage (TOV%) 
        # Formula: TOV / (FGA + 0.44 * FTA + TOV)
        possessions = FGA + 0.44 * s['FTA'] + s['TO']
        factors[team]['TOV%'] = (s['TO'] / possessions) * 100 if possessions > 0 else 0
        
        # 3. Offensive Rebound Percentage (ORB%)
        # Formula: ORB / (ORB + Opp_DRB)
        total_possible_orb = s['ORB'] + opp_s['DRB']
        factors[team]['ORB%'] = (s['ORB'] / total_possible_orb) * 100 if total_possible_orb > 0 else 0
        
        # 4. Free Throw Rate (FTR)
        # Formula: FTA / FGA
        factors[team]['FTR'] = (s['FTA'] / FGA) * 100 if FGA > 0 else 0

    # PLOTTING RADAR
    from math import pi
    plt.style.use('dark_background')
    
    categories = ['Effective FG% (eFG%)', 'Turnover%\n(Lower is Better)', 'Offensive Reb% (ORB%)', 'Free Throw Rate (FTR)']
    N = len(categories)
    
    angles = [n / float(N) * 2 * pi for n in range(N)]
    angles += angles[:1]
    
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor('#0f172a')
    ax.set_facecolor('#0f172a')
    
    # We want to normalize the values so they plot nicely on the same axis (0 to 1) 
    # BUT we want to display the real percentages on the tooltips/labels.
    # Or we can just use a shared percentage axis (0 to 60ish) since all of these naturally fall into 10% - 60% ranges.
    
    ax.set_theta_offset(pi / 4)
    ax.set_theta_direction(-1)
    
    plt.xticks(angles[:-1], categories, color='white', size=14, fontweight='bold')
    
    ax.set_rlabel_position(0)
    plt.yticks([15, 30, 45, 60], ["15%", "30%", "45%", "60%"], color="#94a3b8", size=10)
    plt.ylim(0, 75)
    
    val_a = [factors[team_a_code]['eFG%'], factors[team_a_code]['TOV%'], factors[team_a_code]['ORB%'], factors[team_a_code]['FTR']]
    val_a += val_a[:1]
    
    val_b = [factors[team_b_code]['eFG%'], factors[team_b_code]['TOV%'], factors[team_b_code]['ORB%'], factors[team_b_code]['FTR']]
    val_b += val_b[:1]
    
    # Plot Team A
    ax.plot(angles, val_a, linewidth=3, linestyle='solid', color='#ef4444', label=team_a_name)
    ax.fill(angles, val_a, '#ef4444', alpha=0.25)
    
    # Plot Team B
    ax.plot(angles, val_b, linewidth=3, linestyle='solid', color='#3b82f6', label=team_b_name)
    ax.fill(angles, val_b, '#3b82f6', alpha=0.25)
    
    # Add real values as text near the points
    for i, angle in enumerate(angles[:-1]):
        val = val_a[i]
        ax.text(angle, val + 5, f"{val:.1f}%", color='#fca5a5', fontweight='bold', ha='center', va='center')
        
        val2 = val_b[i]
        ax.text(angle, val2 - 5 if abs(val-val2) < 5 else val2 + 5, f"{val2:.1f}%", color='#93c5fd', fontweight='bold', ha='center', va='center')

    plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), facecolor='#1e293b', edgecolor='#334155', fontsize=12)
    plt.title(f"The Four Factors Battle\n{team_a_name} vs {team_b_name} (Game {meta.get('GameCode', 'X')})", size=22, color='white', fontname='Impact', y=1.1)

    # Spine colors
    ax.spines['polar'].set_color('#334155')
    ax.grid(color='#334155', linestyle='--', alpha=0.7)

    plt.tight_layout()
    output_path = f"game_{meta.get('GameCode', 'X')}_four_factors.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"-> Saved {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Deep dive single-game analytics generator")
    parser.add_argument('--gamecode', type=int, required=True, help="The Euroleague GameCode (e.g., 300)")
    parser.add_argument('--season', type=int, default=2025, help="The season year (default: 2025)")
    args = parser.parse_args()
    
    print(f"Analyzing Season {args.season}, Game {args.gamecode}...")
    
    # 1. Load Data
    all_pbp, game_df = load_game_data(args.season, args.gamecode)
    if game_df is None or game_df.empty:
        return
        
    game_meta = get_game_metadata(args.gamecode)
    if not game_meta:
        print(f"Warning: Could not find metadata for Game {args.gamecode}")
        # Build dummy
        game_meta = {'GameCode': args.gamecode}
        
    print(f"Successfully loaded {len(game_df)} play-by-play events.")
    
    # 2. Generate Visualizations
    generate_wp_flow(game_df, game_meta)
    generate_clutch_breakdown(game_df, game_meta)
    generate_player_impact(game_df, game_meta)
    generate_quarter_momentum(game_df, game_meta)
    generate_rotation_timeline(game_df, game_meta)
    generate_scoring_runs(game_df, game_meta)
    generate_top_lineups(game_df, game_meta)
    generate_four_factors(game_df, game_meta)
    
    print(f"\nAnalysis complete for Game {args.gamecode}!")

if __name__ == "__main__":
    main()
