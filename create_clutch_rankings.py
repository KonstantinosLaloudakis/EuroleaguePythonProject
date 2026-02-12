import json

def create_rankings(input_file='clutch_stats_multiple_seasons.json', output_file='clutch_rankings.json'):
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {input_file} not found.")
        return

    rankings = {}

    for season, players in data.items():
        season_rankings = {}

        # 1. Top Scorers (Points)
        top_scorers = sorted(players, key=lambda x: x['ClutchPoints'], reverse=True)[:10]
        season_rankings["Top Scorers"] = top_scorers

        # 2. Ice Cold Free Throw Shooters (Best FT%, min 10 attempts)
        ft_shooters = [p for p in players if p['ClutchFTA'] >= 10]
        # Calculate percentage float for sorting if not present or parse string
        for p in ft_shooters:
            if 'FT%' in p and p['FT%'] != 'N/A':
                 p['_ft_pct_val'] = float(p['FT%'].strip('%'))
            else:
                 p['_ft_pct_val'] = 0.0
        
        best_ft = sorted(ft_shooters, key=lambda x: x['_ft_pct_val'], reverse=True)[:10]
        # Remove temporary helper key
        for p in best_ft:
            if '_ft_pct_val' in p: del p['_ft_pct_val']
        season_rankings["Ice Cold Free Throw Shooters"] = best_ft

        # 3. Efficient Killers (Best FG%, min 15 attempts)
        fg_shooters = [p for p in players if p['ClutchFGA'] >= 15]
        for p in fg_shooters:
            if 'FG%' in p and p['FG%'] != 'N/A':
                 p['_fg_pct_val'] = float(p['FG%'].strip('%'))
            else:
                 p['_fg_pct_val'] = 0.0
                 
        best_fg = sorted(fg_shooters, key=lambda x: x['_fg_pct_val'], reverse=True)[:10]
        for p in best_fg:
            if '_fg_pct_val' in p: del p['_fg_pct_val']
        season_rankings["Efficient Killers (FG%)"] = best_fg

        # 4. Foul Magnets (Most Fouls Drawn)
        foul_magnets = sorted(players, key=lambda x: x['ClutchFoulsDrawn'], reverse=True)[:10]
        season_rankings["Foul Magnets"] = foul_magnets

        # 5. 3-Point Snipers (Most 3PM)
        snipers = sorted(players, key=lambda x: x['Clutch3PM'], reverse=True)[:10]
        season_rankings["3-Point Snipers"] = snipers

        # 6. Turnover Prone
        turnovers = sorted(players, key=lambda x: x['ClutchTurnovers'], reverse=True)[:10]
        season_rankings["Turnover Prone"] = turnovers

        rankings[season] = season_rankings

    # Save to JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(rankings, f, indent=4, ensure_ascii=False)
    
    print(f"Rankings saved to {output_file}")

if __name__ == "__main__":
    create_rankings()
