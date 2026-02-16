import pandas as pd
from the_lineup_analyzer import analyze_lineups, save_results

import sys

def verify():
    with open("verify_output_internal.txt", "w", encoding='utf-8') as f:
        sys.stdout = f
        sys.stderr = f
        
        cache_file = "data_cache/pbp_lineups_2024.csv"
        try:
            df = pd.read_csv(cache_file, low_memory=False)
            print(f"Loaded {len(df)} rows from cache.")
            print(f"Columns: {df.columns.tolist()}")
            lineup_cols = [c for c in df.columns if 'Lineup_' in c]
            print(f"Lineup Cols: {lineup_cols}")
            
            if lineup_cols:
                val = df[lineup_cols[0]].iloc[0]
                print(f"Sample Lineup Value: {val} (Type: {type(val)})")
                
            if 'Team' in df.columns:
                print(f"Unique Teams: {df['Team'].unique()}")
                
            if 'MARKERTIME' in df.columns:
                print(f"Sample MARKERTIME (valid): {df['MARKERTIME'].dropna().iloc[0]}")
                
            if 'MINUTE' in df.columns:
                 print(f"Sample MINUTE (valid): {df['MINUTE'].dropna().iloc[0]}")
            
            if 'POINTS_A' in df.columns:
                print(f"Sample POINTS_A (valid): {df['POINTS_A'].dropna().iloc[0]}")
                
            if 'POINTS_B' in df.columns:
                print(f"Sample POINTS_B (valid): {df['POINTS_B'].dropna().iloc[0]}")

            # Run Analysis
            s5, s2, sa = analyze_lineups(df)
            
            # Check results
            print(f"\nTotal 5-Man Lineups found: {len(s5)}")
            print(f"Total 2-Man Pairs found: {len(s2)}")
            print(f"Total Players tracked (Anchor): {len(sa)}")
            
            # Print top 3 for each to verify numbers
            # Use save_results logic (but simplify)
            
            # 5-Man
            sorted_5 = sorted(s5.items(), key=lambda x: x[1]['Minutes'], reverse=True)[:3]
            print("\nTop 3 5-Man Lineups by Minutes:")
            for k, v in sorted_5:
                print(f"  {k}: {v['Minutes']:.2f} mins, {v['PF']}-{v['PA']}")
                
            # 2-Man
            sorted_2 = sorted(s2.items(), key=lambda x: x[1]['Minutes'], reverse=True)[:3]
            print("\nTop 3 2-Man Pairs by Minutes:")
            for k, v in sorted_2:
                print(f"  {k}: {v['Minutes']:.2f} mins, {v['PF']}-{v['PA']}")
                
            # Anchor
            sorted_a = sorted(sa.items(), key=lambda x: x[1]['On_Min'], reverse=True)[:3]
            print("\nTop 3 Players by On-Minutes:")
            for k, v in sorted_a:
                print(f"  {k}: On: {v['On_Min']:.2f}m ({v['On_PF']}-{v['On_PA']}), Off: {v['Off_Min']:.2f}m")

        except Exception as e:
            print(f"Verification Failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    verify()
