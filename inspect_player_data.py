from euroleague_api import player_stats
import pandas as pd

try:
    print("Checking help for get_player_stats...")
    help(player_stats.PlayerStats.get_player_stats)
    
    # Try calling without season to see what happens
    # df = player_stats.PlayerStats().get_player_stats(endpoint='traditional')
    
    if not df.empty:
        print("\nColumns:", list(df.columns))
        # Check first row for any URL-like string
        row = df.iloc[0]
        print("\nSample Row:")
        print(row)
        
        # Check for 'Image' or 'Url' columns
        url_cols = [c for c in df.columns if 'url' in c.lower() or 'image' in c.lower() or 'photo' in c.lower()]
        if url_cols:
            print(f"\nFound potential URL columns: {url_cols}")
            print(df[url_cols].head())
        else:
             print("\nNo obvious image columns found.")
             
except Exception as e:
    print(f"Error: {e}")
