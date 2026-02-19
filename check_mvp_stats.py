from euroleague_api import game_stats

def check_stat_columns():
    # Get stats for a single game in 2025
    df = game_stats.GameStats().get_game_stats(2025, 1)
    print("Available Columns:", df.columns.tolist())
    
    # Print a sample row to see data format
    if not df.empty:
        print("Sample Row:", df.iloc[0].to_dict())

if __name__ == "__main__":
    check_stat_columns()
