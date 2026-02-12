from euroleague_api import shot_data
import pandas as pd

def debug_shots():
    print("--- CHECKING SHOT DATA (2024) ---")
    shots = shot_data.ShotData()
    try:
        df = shots.get_game_shot_data(2024, 1)
        print("Shot Data Columns:", sorted(df.columns.tolist()))
        
        # Print sample of time related columns
        time_cols = [c for c in df.columns if 'TIM' in c.upper() or 'MIN' in c.upper() or 'CON' in c.upper() or 'QUAR' in c.upper() or 'PER' in c.upper()]
        print("Time Cols:", time_cols)
        if time_cols:
            print(df[time_cols].head(3))

        # Print sample of score related columns
        score_cols = [c for c in df.columns if 'POINT' in c.upper() or 'SCOR' in c.upper()]
        print("Score Cols:", score_cols)
        if score_cols:
            print(df[score_cols].head(3))
            
    except Exception as e:
        print(f"Error fetching shots: {e}")

if __name__ == "__main__":
    debug_shots()
