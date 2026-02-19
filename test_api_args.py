from euroleague_api import player_stats
import traceback

def test_args():
    p = player_stats.PlayerStats()
    
    # Test 1: Season as String
    print("\n--- Test 1: Season as String '2025' ---")
    try:
        df = p.get_player_stats(endpoint='traditional', season='2025')
        print(f"Success! Rows: {len(df)}")
        print(df.head(1).to_dict('records'))
    except Exception as e:
        print(f"Failed: {e}")

    # Test 2: Season as String 'E2025'
    print("\n--- Test 2: Season as String 'E2025' ---")
    try:
        df = p.get_player_stats(endpoint='traditional', season='E2025')
        print(f"Success! Rows: {len(df)}")
    except Exception as e:
        print(f"Failed: {e}")

    # Test 3: Standard 2024 (maybe 2025 is future?)
    print("\n--- Test 3: Season 2024 (Int) ---")
    try:
        df = p.get_player_stats(endpoint='traditional', season=2024)
        print(f"Success! Rows: {len(df)}")
        if not df.empty:
             print("Sample gamesPlayed:", df.iloc[0]['gamesPlayed'])
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    test_args()
