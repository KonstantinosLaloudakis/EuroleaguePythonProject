import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def plot_mvp_ladder():
    # Load rankings
    try:
        df = pd.read_json('mvp_rankings_2025.json')
    except Exception as e:
        print(f"Error loading rankings: {e}")
        return

    # Take Top 10
    top_10 = df.head(10).sort_values('MVP_Score', ascending=True) # Ascending for barh (bottom to top)
    
    # Setup Plot
    plt.figure(figsize=(12, 8))
    sns.set_theme(style="whitegrid")
    
    # Create Bar Chart
    bars = plt.barh(top_10['PlayerName'], top_10['MVP_Score'], color='#ff7f0e')
    
    # Custom Colors based on Team (Updated for Contrast)
    team_colors = {
        'OLY': '#E2001A', # Red (Olympiacos)
        'ULK': '#002B5C', # Navy (Fenerbahce)
        'PAN': '#007F3D', # Green
        'MAD': '#645486', # Purple (Real Madrid)
        'BAR': '#004D98', # Blue/Red
        'MCO': '#D4AF37', # Gold (Monaco)
        'ZAL': '#006233', # Green
        'DUB': '#000000', # Black
        'IST': '#003366', # Navy
        'HTA': '#000000', # Black
        'PAR': '#000000', # Black
        'RED': '#FFFFFF', # White (Crvena Zvezda)
        'TEL': '#F6C300', # Yellow
        'BAS': '#B50031', # Red/Blue
        'MUN': '#0066B2', # Blue
        'VIR': '#000000', # Black
        'PAM': '#EB7622', # Orange
        'ASV': '#000000'  # Black
    }
    
    # Add edgecolor for visibility of White bars
    for bar, team in zip(bars, top_10['TeamCode']):
        bar.set_color(team_colors.get(team, '#888888'))
        bar.set_edgecolor('black')
        bar.set_linewidth(1)
        
        # Special Hatching for Red Star (RED)
        if team == 'RED':
            bar.set_facecolor('white')
            bar.set_edgecolor('#E2001A')
            bar.set_hatch('///') # Red stripes on white
        
    # Add Titles and Labels
    plt.title('Euroleague 2025-26 MVP Ladder (Week 28)', fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('MVP Score (Weighted: Base + Team + Clutch)', fontsize=12)
    plt.ylabel('Player', fontsize=12)
    
    # Add Score Labels
    for bar, score, rank, team in zip(bars, top_10['MVP_Score'], top_10['MVP_Rank'], top_10['TeamCode']):
        plt.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2, 
                 f"{score:.1f} ({team})", 
                 va='center', fontsize=10, fontweight='bold')
                 
    # Adjust X axis
    plt.xlim(0, top_10['MVP_Score'].max() * 1.15)
    
    plt.tight_layout()
    plt.savefig('mvp_ladder_2025.png', dpi=300)
    print("Saved mvp_ladder_2025.png")

if __name__ == "__main__":
    plot_mvp_ladder()
