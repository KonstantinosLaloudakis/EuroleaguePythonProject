from euroleague_clutch_analysis import ClutchAnalysis

if __name__ == "__main__":
    print("Analyzing Clutch Season 2024...")
    # Instantiate class
    clutch = ClutchAnalysis(2024, 2024)
    clutch.fetch_and_calculate_stats()
