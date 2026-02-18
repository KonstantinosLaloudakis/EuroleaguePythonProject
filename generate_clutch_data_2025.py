from clutchStats import analyze_clutch_stats
import json
import os

def generate_2025_data():
    print("Generating clutch data for 2025 season...")
    # This will save to 'clutch_stats_multiple_seasons.json' by default
    analyze_clutch_stats(start_season=2025, end_season=2025)
    
    # Rename for clarity if needed, or just use the generated file
    if os.path.exists('clutch_stats_multiple_seasons.json'):
        print("Data generation complete. File 'clutch_stats_multiple_seasons.json' created.")
        
        # specific check
        with open('clutch_stats_multiple_seasons.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            if "2025" in data:
                print(f"Verified: Found {len(data['2025'])} players for season 2025.")
            else:
                print("Warning: Season 2025 not found in output file.")

if __name__ == "__main__":
    generate_2025_data()
