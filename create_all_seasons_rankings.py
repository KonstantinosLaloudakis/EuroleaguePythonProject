import json

def create_all_seasons_rankings(input_file='clutch_stats_multiple_seasons.json', output_file='clutch_rankings_all_seasons.json'):
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {input_file} not found.")
        return

    # Flatten all players from all seasons into one list
    all_performances = []
    for season, players in data.items():
        for p in players:
            # ensure season is tracked
            p['Season'] = season 
            all_performances.append(p)

    # Calculate Percentages for sorting helper values
    for p in all_performances:
        # FG%
        if 'FG%' in p and p['FG%'] != 'N/A':
             p['_fg_pct_val'] = float(p['FG%'].strip('%'))
        else:
             p['_fg_pct_val'] = 0.0
             
        # FT%
        if 'FT%' in p and p['FT%'] != 'N/A':
             p['_ft_pct_val'] = float(p['FT%'].strip('%'))
        else:
             p['_ft_pct_val'] = 0.0

    rankings = {}

    # 1. Top Scorers (Points) - Best Single Season Performance
    top_scorers = sorted(all_performances, key=lambda x: x['ClutchPoints'], reverse=True)[:10]
    rankings["Top Scorers (Best Single Season)"] = [{k: v for k, v in p.items() if not k.startswith('_')} for p in top_scorers]

    # 2. Ice Cold Free Throw Shooters
    ft_shooters = [p for p in all_performances if p['ClutchFTA'] >= 15] # Threshold checks against single season volume
    best_ft = sorted(ft_shooters, key=lambda x: x['_ft_pct_val'], reverse=True)[:10]
    rankings["Ice Cold Free Throw Shooters (Best Single Season)"] = [{k: v for k, v in p.items() if not k.startswith('_')} for p in best_ft]

    # 3. Efficient Killers (FG%)
    fg_shooters = [p for p in all_performances if p['ClutchFGA'] >= 20] # Threshold
    best_fg = sorted(fg_shooters, key=lambda x: x['_fg_pct_val'], reverse=True)[:10]
    rankings["Efficient Killers FG% (Best Single Season)"] = [{k: v for k, v in p.items() if not k.startswith('_')} for p in best_fg]

    # 4. Foul Magnets
    foul_magnets = sorted(all_performances, key=lambda x: x['ClutchFoulsDrawn'], reverse=True)[:10]
    rankings["Foul Magnets (Best Single Season)"] = [{k: v for k, v in p.items() if not k.startswith('_')} for p in foul_magnets]

    # 5. 3-Point Snipers
    snipers = sorted(all_performances, key=lambda x: x['Clutch3PM'], reverse=True)[:10]
    rankings["3-Point Snipers (Best Single Season)"] = [{k: v for k, v in p.items() if not k.startswith('_')} for p in snipers]

    # 6. Turnover Prone
    turnovers = sorted(all_performances, key=lambda x: x['ClutchTurnovers'], reverse=True)[:10]
    rankings["Turnover Prone (Best Single Season)"] = [{k: v for k, v in p.items() if not k.startswith('_')} for p in turnovers]

    # Save to JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(rankings, f, indent=4, ensure_ascii=False)
    
    print(f"All-Seasons rankings saved to {output_file}")

if __name__ == "__main__":
    create_all_seasons_rankings()
