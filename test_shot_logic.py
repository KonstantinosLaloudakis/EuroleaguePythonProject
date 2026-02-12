from euroleague_api import shot_data
import pandas as pd

def test_logic():
    shots = shot_data.ShotData()
    print("Searching for clutch shots in first 10 games of 2024...")
    
    for game_code in range(1, 11):
        try:
            df = shots.get_game_shot_data(2024, game_code)
            
            # Check if required columns exist
            req_cols = ['MINUTE', 'POINTS_A', 'POINTS_B', 'COORD_X', 'COORD_Y']
            if not all(col in df.columns for col in req_cols):
                print(f"Game {game_code}: Missing columns. Found: {df.columns.tolist()}")
                continue
                
            # Filter Logic
            # Metric: Clutch Time = 4th Quarter (Minute > 30? No, Minute starts at 1)
            # 4th Quarter starts at Minute 31. Clutch starts at Minute 36 (5 mins left).
            # OR use ID_PERIOD/QUARTER if available.
            
            # Let's verify QUARTER column exists
            if 'QUARTER' in df.columns:
                # 4th Q is 4. OT is 5.
                # If Q == 4, we need last 5 mins.
                # How to determine time remaining?
                # If CONSOLE exists:
                if 'CONSOLE' in df.columns:
                    # Parse "MM:SS"
                    def get_seconds(t_str):
                        try:
                            m, s = map(int, str(t_str).split(':'))
                            return m * 60 + s
                        except: return 999
                    
                    df['SecondsRemaining'] = df['CONSOLE'].apply(get_seconds)
                    
                    # Clutch: Q >= 4 AND (seconds <= 300 OR Q > 4) ??
                    # Actually standard clutch definition: 4th Q or OT, <= 5 mins left.
                    # In OT (Q5), it's always <= 5 mins. So Q>4 is always clutch time.
                    # In Q4, need Seconds <= 300.
                    
                    clutch_mask = (
                        ((df['QUARTER'] == 4) & (df['SecondsRemaining'] <= 300)) | 
                        (df['QUARTER'] > 4)
                    )
                else:
                    # Fallback to MINUTE
                    # Q4 starts min 31. Last 5 mins is > 35.
                    # Q5 starts min 41.
                    clutch_mask = df['MINUTE'] > 35
            else:
                 clutch_mask = df['MINUTE'] > 35 # Fallback
            
            # Score Margin
            df['ScoreMargin'] = abs(df['POINTS_A'] - df['POINTS_B'])
            stats_mask = df['ScoreMargin'] <= 5
            
            final_df = df[clutch_mask & stats_mask]
            
            if not final_df.empty:
                print(f"Game {game_code}: Found {len(final_df)} clutch shots!")
                print("Sample:", final_df[['PLAYER', 'MINUTE', 'POINTS_A', 'POINTS_B', 'COORD_X', 'COORD_Y']].head(1).to_dict('records'))
                break
            else:
                print(f"Game {game_code}: No clutch shots.")
                
        except Exception as e:
            print(f"Game {game_code} Error: {e}")

if __name__ == "__main__":
    test_logic()
