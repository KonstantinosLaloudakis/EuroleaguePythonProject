from euroleague_api.game_stats import GameStats
import pandas as pd

def inspect_report():
    print("Checking Season 2024 Game 1...")
    try:
        # Season 2024 (Current)
        df = GameStats().get_game_report(season=2024, game_code=1)
        if not df.empty:
            print("Columns:", df.columns.tolist())
            if 'Round' in df.columns:
                print(f"Game 1 Round: {df['Round'].iloc[0]}")
                print(df[['Gamecode', 'Round', 'LocalTeam', 'RoadTeam']].head(1))
            else:
                print("Round column MISSING in 2024.")
        else:
            print("DataFrame Empty for 2024.")
    except Exception as e:
        print(f"Error 2024: {e}")

    print("\nChecking Season 2025 Game 1...")
    try:
        # Season 2025 (Future/Expansion?)
        df = GameStats().get_game_report(season=2025, game_code=1)
        if not df.empty:
            print("Columns:", df.columns.tolist())
            if 'Round' in df.columns:
                print(f"Game 1 Round: {df['Round'].iloc[0]}")
                print(df[['Gamecode', 'Round', 'LocalTeam', 'RoadTeam']].head(1))
            else:
                print("Round column MISSING in 2025.")
        else:
            print("DataFrame Empty for 2025.")
    except Exception as e:
        print(f"Error 2025: {e}")

if __name__ == "__main__":
    inspect_report()
