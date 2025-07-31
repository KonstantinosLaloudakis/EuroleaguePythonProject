"""
Test script to explore EuroLeague API capabilities
"""

from euroleague_api.player_stats import PlayerStats
from euroleague_api.standings import Standings
import pandas as pd

def explore_api():
    """Explore the EuroLeague API to understand available data."""
    
    print("🔍 Exploring EuroLeague API...")
    
    # Initialize API classes
    player_stats = PlayerStats("E")  # "E" for EuroLeague
    standings = Standings("E")
    
    # Test different stat categories
    stat_categories = ["traditional", "advanced", "misc", "scoring"]
    season = 2023
    
    for category in stat_categories:
        print(f"\n📊 Testing {category} stats for {season}-{season+1}...")
        try:
            params = {
                'SeasonCode': f'E{season}',  # E2023 for 2023-24 season
            }
            
            df = player_stats.get_player_stats(
                endpoint=category,
                params=params,
                phase_type_code="RS",  # Regular season
                statistic_mode="PerGame"
            )
            
            if df is not None and not df.empty:
                print(f"✅ Success! Got {len(df)} records")
                print(f"📋 Columns: {list(df.columns)}")
                
                # Show sample data
                if len(df) > 0:
                    print(f"📖 Sample data:")
                    sample = df.head(2)
                    for col in df.columns[:10]:  # Show first 10 columns
                        if col in sample.columns:
                            print(f"   {col}: {sample[col].tolist()}")
                break  # Just test the first working category
            else:
                print("⚠️ No data returned")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Test standings
    print(f"\n🏆 Testing standings...")
    for round_num in [34, 30, 1]:  # Try different rounds
        try:
            standings_df = standings.get_standings(season, round_num)
            if standings_df is not None and not standings_df.empty:
                print(f"✅ Standings for round {round_num}: {len(standings_df)} teams")
                print(f"📋 Columns: {list(standings_df.columns)}")
                break
        except Exception as e:
            print(f"❌ Standings round {round_num} error: {e}")


if __name__ == "__main__":
    explore_api()