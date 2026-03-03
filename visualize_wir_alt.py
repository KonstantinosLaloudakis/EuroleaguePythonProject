import pandas as pd
import matplotlib.pyplot as plt

def create_dumbbell_chart():
    df = pd.read_json('wir_ratings.json')
    
    # Top 15 players by WIR
    top_15 = df.sort_values('WIR_40', ascending=False).head(15)
    
    # Top 5 risers not in the top 15
    risers = df.sort_values('Rank_Diff', ascending=False)
    risers = risers[~risers['player.name'].isin(top_15['player.name'])].head(5)
    
    # Combine and sort for plotting (bottom to top)
    plot_df = pd.concat([top_15, risers]).sort_values('WIR_40', ascending=True)
    
    fig, ax = plt.subplots(figsize=(12, 11))
    fig.patch.set_facecolor('#0d1117')
    ax.set_facecolor('#161b22')
    
    y_positions = range(len(plot_df))
    
    for i, (_, row) in enumerate(plot_df.iterrows()):
        pir = row['PIR_40']
        wir = row['WIR_40']
        
        # Draw line connecting PIR and WIR
        color = '#39d353' if wir >= pir else '#f85149'
        ax.plot([pir, wir], [i, i], color=color, alpha=0.6, linewidth=3, zorder=1)
        
        # Draw PIR point (grey/reddish)
        ax.scatter(pir, i, color='#8b949e', s=100, zorder=2, edgecolors='#161b22', linewidths=1)
        
        # Draw WIR point (bright green if higher, red if lower)
        ax.scatter(wir, i, color=color, s=150, zorder=3, edgecolors='#161b22', linewidths=1.5)
        
        # Add labels to the dots
        # Determine alignments to avoid overlap
        if wir >= pir:
            ax.text(wir + 0.4, i, f"{wir:.1f}", color=color, va='center', fontweight='bold', fontsize=9)
            ax.text(pir - 0.4, i, f"{pir:.1f}", color='#8b949e', va='center', ha='right', fontsize=9)
        else:
            ax.text(wir - 0.4, i, f"{wir:.1f}", color=color, va='center', ha='right', fontweight='bold', fontsize=9)
            ax.text(pir + 0.4, i, f"{pir:.1f}", color='#8b949e', va='center', fontsize=9)
            
    # Format Y axis
    labels = []
    for _, row in plot_df.iterrows():
        # Clean name format "LASTNAME, FIRSTNAME"
        name_parts = row['player.name'].split(',')
        if len(name_parts) == 2:
            clean_name = f"{name_parts[1].strip().title()} {name_parts[0].strip().title()}"
        else:
            clean_name = row['player.name'].title()
            
        team = str(row['player.team.name']).split(' ')[0] if pd.notna(row['player.team.name']) else ""
        labels.append(f"{clean_name} ({team})")
        
    ax.set_yticks(y_positions)
    ax.set_yticklabels(labels, color='#e6edf3', fontsize=10, fontweight='bold')
    
    # Custom legend
    ax.scatter([], [], color='#39d353', s=100, label='WIR (Better Efficiency/Defense)')
    ax.scatter([], [], color='#f85149', s=100, label='WIR (Inefficient)')
    ax.scatter([], [], color='#8b949e', s=80, label='PIR (Old Metric)')
    ax.legend(loc='lower right', facecolor='#161b22', edgecolor='#30363d', labelcolor='#e6edf3')
    
    ax.set_title('WIR vs PIR: How the New Metric Re-Ranks Players\nTop 15 Players + Biggest Risers (per 40 mins)', 
                 fontsize=16, color='#e6edf3', fontweight='bold', pad=20)
                 
    ax.set_xlabel('Rating per 40 Minutes', fontsize=12, color='#8b949e', fontweight='bold')
    
    # Style
    ax.tick_params(colors='#8b949e', axis='x')
    ax.tick_params(left=False, axis='y')
    ax.spines['bottom'].set_color('#30363d')
    ax.spines['left'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='x', alpha=0.15, color='#30363d', linestyle='--')
    
    # Adjust x limits with padding
    min_x = plot_df[['PIR_40', 'WIR_40']].min().min() - 2
    max_x = plot_df[['PIR_40', 'WIR_40']].max().max() + 2
    ax.set_xlim(min_x, max_x)
    
    plt.tight_layout()
    outfile = 'wir_dumbbell.png'
    plt.savefig(outfile, dpi=150, facecolor=fig.get_facecolor(), bbox_inches='tight')
    print(f"Visualization saved to {outfile}")

if __name__ == '__main__':
    create_dumbbell_chart()
