from euroleague_api.standings import Standings
import pandas as pd

def inspect_standings():
    print("Fetching Standings 2025, Round 1...")
    try:
        df = Standings().get_standings(season=2025, round_number=1)
        if not df.empty:
            print(f"Teams found: {len(df)}")
            print(df['club.code'].tolist())
        else:
            print("2025 Round 1 Standings Empty.")
    except Exception as e:
        print(f"Error 2025: {e}")

    print("\nFetching Calendar Standings 2025...")
    try:
        df = Standings().get_standings(season=2025, round_number=1, endpoint='calendarstandings')
        if not df.empty:
             print("Calendar Columns:", df.columns.tolist())
    except Exception as e:
         print(f"Error Calendar: {e}")

if __name__ == "__main__":
    inspect_standings()
