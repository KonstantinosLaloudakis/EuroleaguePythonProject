from euroleague_api.standings import Standings
import pandas as pd

def get_2025_teams():
    try:
        df = Standings().get_standings(season=2025, round_number=1)
        if not df.empty:
            teams = df['club.code'].tolist()
            print(f"Teams found: {len(teams)}")
            for t in teams:
                print(t)
        else:
            print("Empty standings.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_2025_teams()
