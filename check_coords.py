from euroleague_api import play_by_play_data, shot_data
import pandas as pd

def check_coordinates():
    print("--- CHECKING PLAY BY PLAY ---")
    pbp = play_by_play_data.PlayByPlay()
    df_pbp = pbp.get_game_play_by_play_data(2023, 1)
    
    potential_coords_pbp = [col for col in df_pbp.columns if 'COORD' in col.upper() or 'X' in col.upper() or 'Y' in col.upper()]
    print(f"Potential coordinate columns in PBP: {potential_coords_pbp}")
    
    print("\n--- CHECKING SHOT DATA ---")
    shots = shot_data.ShotData()
    df_shots = shots.get_game_shot_data(2023, 1)
    
    potential_coords_shots = [col for col in df_shots.columns if 'COORD' in col.upper() or 'X' in col.upper() or 'Y' in col.upper()]
    print(f"Potential coordinate columns in Shot Data: {potential_coords_shots}")

if __name__ == "__main__":
    check_coordinates()
