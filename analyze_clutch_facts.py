import json

def analyze_json_for_facts(filename='clutch_stats_multiple_seasons.json'):
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    for season, players in data.items():
        print(f"\n--- INTERESTING FACTS FOR SEASON {season} ---")
        
        # 1. "Ice Cold" - Best FT% (min 10 attempts)
        ft_shooters = [p for p in players if p['ClutchFTA'] >= 10]
        best_ft = sorted(ft_shooters, key=lambda x: (x['ClutchFTM']/x['ClutchFTA']), reverse=True)[:3]
        print("\nFree Throws (Ice Cold):")
        for p in best_ft:
            print(f"- {p['Player']}: {p['FT%']} ({p['ClutchFTM']}/{p['ClutchFTA']})")

        # 2. "Efficient Killer" - Best FG% (min 10 attempts)
        fg_shooters = [p for p in players if p['ClutchFGA'] >= 10]
        best_fg = sorted(fg_shooters, key=lambda x: (x['ClutchFGM']/x['ClutchFGA']), reverse=True)[:3]
        print("\nField Goals (Efficient Killers):")
        for p in best_fg:
            print(f"- {p['Player']}: {p['FG%']} ({p['ClutchFGM']}/{p['ClutchFGA']}) - {p['ClutchPoints']} pts")

        # 3. "Foul Magnet" - Most Fouls Drawn 
        fouls_drawn = sorted(players, key=lambda x: x['ClutchFoulsDrawn'], reverse=True)[:3]
        print("\nFoul Magnets:")
        for p in fouls_drawn:
            print(f"- {p['Player']}: {p['ClutchFoulsDrawn']} fouls drawn")

        # 4. "3-Point Sniper" - Most Clutch 3s
        threes = sorted(players, key=lambda x: x['Clutch3PM'], reverse=True)[:3]
        print("\nClutch 3-Point Snipers:")
        for p in threes:
            print(f"- {p['Player']}: {p['Clutch3PM']} made 3s")
            
        # 5. "Turnover Prone" - Most Turnovers in Clutch
        tos = sorted(players, key=lambda x: x['ClutchTurnovers'], reverse=True)[:3]
        print("\nTurnover Prone (Needs to be careful):")
        for p in tos:
            print(f"- {p['Player']}: {p['ClutchTurnovers']} turnovers")

if __name__ == "__main__":
    analyze_json_for_facts()
