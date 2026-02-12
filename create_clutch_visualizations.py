import json
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import os

def create_clutch_visualizations(rankings_file='clutch_rankings_all_seasons_2007_2024.json',
                                 shots_file='clutch_shots_2007_2024.json',
                                 output_dir='clutch_viz_2024_2024New'):
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Load Rankings
    try:
        with open(rankings_file, 'r', encoding='utf-8') as f:
            rankings = json.load(f)
    except FileNotFoundError:
        print(f"Rankings file {rankings_file} not found. Skipping rankings charts.")
        rankings = None

    # Load Shots
    try:
        with open(shots_file, 'r', encoding='utf-8') as f:
            shots_data = json.load(f)
    except FileNotFoundError:
        print(f"Shots file {shots_file} not found. Skipping shot charts.")
        shots_data = None

    if rankings:
        # Plot Efficiency Scatter (General)
        plot_efficiency_scatter(rankings, output_dir)
        
        # Plot Specific Category Rankings
        for category, players in rankings.items():
            plot_generic_ranking(category, players, output_dir)
    
    if shots_data:
        # Find top scorer from stats to plot
        top_scorer = "JAMES, MIKE" # Default
        if rankings and "Top Scorers (Best Single Season)" in rankings:
             top_scorer = rankings["Top Scorers (Best Single Season)"][0]['Player']
        
        plot_shot_chart(shots_data, top_scorer, output_dir)
        # Also plot 2nd place
        if rankings and "Top Scorers (Best Single Season)" in rankings and len(rankings["Top Scorers (Best Single Season)"]) > 1:
            second_scorer = rankings["Top Scorers (Best Single Season)"][1]['Player']
            plot_shot_chart(shots_data, second_scorer, output_dir)

def plot_generic_ranking(category, players, output_dir):
    print(f"Generating Chart for: {category}...")
    data = players[:10] # Top 10
    if not data: return
    
    # Determine Metric based on Category Name
    metric = 'ClutchPoints' # Default
    if 'Free Throw' in category: metric = 'FT%'
    elif 'FG%' in category: metric = 'FG%'
    elif 'Foul' in category: metric = 'ClutchFoulsDrawn'
    elif '3-Point' in category: metric = 'Clutch3PM'
    elif 'Turnover' in category: metric = 'ClutchTurnovers'
    elif 'Scorers' in category: metric = 'ClutchPoints'
    
    # Prepare Data
    names = [f"{p['Player']} '{str(p['Season'])[-2:]}" for p in data]
    
    # Handle Percentage Strings
    values = []
    for p in data:
        val = p.get(metric, 0)
        if isinstance(val, str) and '%' in val:
            try:
                val = float(val.strip('%'))
            except:
                val = 0
        values.append(val)
        
    # Plot Horizontal Bar Chart
    plt.figure(figsize=(10, 6))
    
    # Reverse to have top at top
    plt.barh(names[::-1], values[::-1], color='skyblue')
    
    plt.title(f"{category} (Top 10)")
    plt.xlabel(metric)
    plt.tight_layout()
    
    safe_cat = category.replace(" ", "_").replace("%", "Pct").replace("(", "").replace(")", "").replace("-", "_")
    plt.savefig(f"{output_dir}/ranking_{safe_cat}.png")
    plt.close()

def plot_efficiency_scatter(rankings, output_dir):
    print("Generating Efficiency Scatter Plot...")
    data = rankings.get("Top Scorers (Best Single Season)", [])
    if not data: return

    # We want a broader dataset, maybe use stats_file? 
    # But rankings has top 10. Let's start with Top 10 + Efficient Killers combined
    
    players = []
    seen = set()
    
    # Collect players from multiple lists for a better scatter
    source_lists = ["Top Scorers (Best Single Season)", "Efficient Killers FG% (Best Single Season)"]
    for key in source_lists:
        for p in rankings.get(key, []):
            try:
                # Identify uniquely by Player + Season
                pid = f"{p['Player']}_{p['Season']}"
                if pid not in seen:
                    # Calculate per game or just raw? Raw is fine for clutch totals
                    fg_pct = float(p.get('FG%', '0').strip('%'))
                    if fg_pct == 0 and p['ClutchFGA'] > 0:
                        fg_pct = (p['ClutchFGM'] / p['ClutchFGA']) * 100
                    
                    players.append({
                        'Player': p['Player'],
                        'Season': p['Season'],
                        'ClutchPoints': p['ClutchPoints'],
                        'FG%': fg_pct,
                        'Team': p['Team']
                    })
                    seen.add(pid)
            except Exception as e:
                continue

    df = pd.DataFrame(players)
    
    plt.figure(figsize=(12, 8))
    sns.scatterplot(data=df, x='ClutchPoints', y='FG%', hue='Team', s=100)
    
    # Annotate top players
    for i, row in df.iterrows():
        plt.text(row['ClutchPoints']+1, row['FG%'], 
                 f"{row['Player']} '{str(row['Season'])[-2:]}", 
                 fontsize=9)
        
    plt.title('Clutch Efficiency: Points vs FG% (Top Performers 2023-24)')
    plt.xlabel('Total Clutch Points')
    plt.ylabel('Field Goal Percentage (%)')
    plt.grid(True, linestyle='--', alpha=0.7)
    
    plt.savefig(f"{output_dir}/clutch_efficiency_scatter.png")
    plt.close()

def plot_scoring_breakdown(rankings, output_dir):
    print("Generating Scoring Breakdown Bar Chart...")
    top_scorers = rankings.get("Top Scorers (Best Single Season)", [])[:10]
    if not top_scorers: return
    
    names = [f"{p['Player']} '{str(p['Season'])[-2:]}" for p in top_scorers]
    points_2pt = [p['ClutchFGM'] * 2 for p in top_scorers] # Approx, logic is tricky if we don't have 2PM. 
    # Wait, data has 'ClutchFGM' (Total) and 'Clutch3PM'.
    # 2PM = FGM - 3PM
    
    p2_vals = []
    p3_vals = []
    ft_vals = []
    
    for p in top_scorers:
        fgm = p['ClutchFGM']
        pm3 = p['Clutch3PM']
        pm2 = fgm - pm3
        ftm = p['ClutchFTM']
        
        p2_vals.append(pm2 * 2)
        p3_vals.append(pm3 * 3)
        ft_vals.append(ftm)
        
    df = pd.DataFrame({
        'Player': names,
        '2-Point Pts': p2_vals,
        '3-Point Pts': p3_vals,
        'Free Throw Pts': ft_vals
    })
    
    df.set_index('Player').plot(kind='bar', stacked=True, figsize=(12, 6), colormap='viridis')
    plt.title('Clutch Scoring Breakdown (Top 10 Scorers)')
    plt.ylabel('Points')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(f"{output_dir}/clutch_scoring_breakdown.png")
    plt.close()

from matplotlib.patches import Circle, Rectangle, Arc

def draw_court(ax=None, color='black', lw=2):
    if ax is None:
        ax = plt.gca()
    
    # FIBA Court (Half Court)
    # Origin: Center of Hoop (0, 0)
    # units: cm
    
    # Hoop
    hoop = Circle((0, 0), radius=45/2, linewidth=lw, color=color, fill=False)
    
    # Backboard
    # 1.2m from baseline. Hoop is 1.575m from baseline.
    # So Backboard is 37.5cm behind hoop (relative to court).
    # Y = -37.5
    backboard = Rectangle((-90, -37.5), 180, 1, linewidth=lw, color=color)
    
    # The Paint (Key)
    # Width: 4.9m = 490cm. Height: 5.8m = 580cm.
    # Starts at baseline. Baseline is Y = -157.5
    outer_box = Rectangle((-245, -157.5), 490, 580, linewidth=lw, color=color, fill=False)
    
    # Free Throw Circle
    # Center is at top of key (5.8m from baseline).
    # Y = -157.5 + 580 = 422.5
    top_free_throw = Arc((0, 422.5), 360, 360, theta1=0, theta2=180, linewidth=lw, color=color, fill=False)
    bottom_free_throw = Arc((0, 422.5), 360, 360, theta1=180, theta2=0, linewidth=lw, color=color, linestyle='dashed')
    
    # Restricted Area
    # Semi-circle 1.25m radius from hoop center
    restricted = Arc((0, 0), 250, 250, theta1=0, theta2=180, linewidth=lw, color=color)
    
    # Three Point Line
    # Arc radius 6.75m from hoop center (0,0)
    # Straight lines convert to arc at 2.99m from baseline? 
    # Corners are 0.9m from sideline. Width 15m -> Sideline 7.5m. 
    # Corner line X = +/- (750 - 90) = +/- 660.
    # Intersection: sqrt(675^2 - 660^2) = sqrt(455625 - 435600) = sqrt(20025) = 141.5cm from hoop center?
    # Actually simpler: Straight lines extend from baseline to where arc starts.
    # Arc is valid for Y > something.
    
    three_point_arc = Arc((0, 0), 675*2, 675*2, theta1=0, theta2=180, linewidth=lw, color=color)
    
    # Center Circle (Midcourt) - 14m from baseline.
    # Y = -157.5 + 1400 = 1242.5
    center_outer_arc = Arc((0, 1242.5), 360, 360, theta1=180, theta2=360, linewidth=lw, color=color)
    
    court_elements = [hoop, backboard, outer_box, top_free_throw, bottom_free_throw, restricted, three_point_arc, center_outer_arc]
    
    for element in court_elements:
        ax.add_patch(element)
        
    return ax

def plot_shot_chart(shots_data, player_name, output_dir):
    print(f"Generating Shot Chart for {player_name}...")
    
    # Filter for player
    player_shots = [s for s in shots_data if s['Player'] == player_name]
    if not player_shots:
        print(f"No shots found for {player_name}")
        return

    df = pd.DataFrame(player_shots)
    
    # Create Court
    plt.figure(figsize=(12, 11))
    ax = plt.gca()
    draw_court(ax, color='gray', lw=2)
    
    # Set Limits (Standard Half Court)
    # Origin is hoop.
    # X: -800 to 800
    # Y: Baseline (-157.5) to Half Court (1242.5). Padding -> -200 to 1300
    plt.xlim(-800, 800)
    plt.ylim(-200, 1300)
    
    # Makes/Misses
    makes = df[df['Result'] == 'Make']
    misses = df[df['Result'] == 'Miss']
    
    if not makes.empty:
        plt.scatter(makes['CoordX'], makes['CoordY'], c='green', marker='o', s=100, label='Make', alpha=0.7, edgecolors='white')
    if not misses.empty:
        plt.scatter(misses['CoordX'], misses['CoordY'], c='red', marker='x', s=100, label='Miss', alpha=0.7)
    
    plt.title(f"Clutch Shot Chart: {player_name}")
    if not makes.empty or not misses.empty:
        plt.legend()
        
    plt.axis('off') # Hide axes
    
    # Add season to filename since data spans multiple
    seasons = df['Season'].unique()
    season_str = "_".join(map(str, seasons))
    
    safe_name = player_name.replace(" ", "_").replace(",", "")
    plt.savefig(f"{output_dir}/shot_chart_{safe_name}_{season_str}.png", bbox_inches='tight')
    plt.close()

if __name__ == "__main__":
    create_clutch_visualizations()
