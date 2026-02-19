import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def plot_mvp_ladder_2024():
    # Load rankings
    try:
        df = pd.read_json('mvp_rankings_2024.json')
    except Exception as e:
        print(f"Error loading rankings 2024: {e}")
        return

    # Take Top 10
    top_10 = df.head(10).sort_values('MVP_Score', ascending=True) 
    
    # Setup Plot
    plt.figure(figsize=(12, 8))
    sns.set_theme(style="whitegrid")
    
    # Create Bar Chart
    bars = plt.barh(top_10['PlayerName'], top_10['MVP_Score'], color='#ff7f0e')
    
    # Custom Colors (Same map)
    team_colors = {
        'OLY': '#E2001A', 'ULK': '#F6C300', 'PAN': '#007F3D', 
        'MAD': '#6C3B2A', 'BAR': '#004D98', 'MCO': '#E30613',
        'ZAL': '#006233', 'DUB': '#000000', 'IST': '#003366',
        'HTA': '#CC0000', 'PAR': '#000000', 'RED': '#CC0000',
        'TEL': '#F6C300', 'BAS': '#B50031', 'MUN': '#DC052D',
        'VIR': '#000000', 'PAM': '#EB7622', 'ASV': '#000000'
    }
    
    for bar, team in zip(bars, top_10['TeamCode']):
        bar.set_color(team_colors.get(team, '#888888'))
        
    # Add Titles and Labels
    plt.title('Euroleague 2024-25 MVP Validation (RETROSPECTIVE)', fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('MVP Score (Weighted: Base 65% + Team 20% + Clutch 15%)', fontsize=12)
    plt.ylabel('Player', fontsize=12)
    
    # Add Score Labels
    for bar, score, rank, team in zip(bars, top_10['MVP_Score'], top_10['MVP_Rank'], top_10['TeamCode']):
        plt.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2, 
                 f"{score:.1f} ({team})", 
                 va='center', fontsize=10, fontweight='bold')
                 
    # Adjust X axis
    plt.xlim(0, top_10['MVP_Score'].max() * 1.15)
    
    plt.tight_layout()
    plt.savefig('mvp_ladder_2024_validation.png', dpi=300)
    print("Saved mvp_ladder_2024_validation.png")

if __name__ == "__main__":
    plot_mvp_ladder_2024()
