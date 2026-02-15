from euroleague_api import play_by_play_data
import pandas as pd

def inspect_assists():
    pbp = play_by_play_data.PlayByPlay()
    # Fetch a recent game (e.g. from 2024 season) to be safe
    df = pbp.get_game_play_by_play_data(season=2024, gamecode=1)
    
    with open("pbp_columns.txt", "w") as f:
        for col in df.columns:
            f.write(f"{col}\n")
            
    print("Columns written to pbp_columns.txt")
    
    assists = df[df['PLAYTYPE'] == 'AS']
    if not assists.empty:
        idx = assists.index[0]
        # Get surrounding rows
        start = max(0, idx - 2)
        end = min(len(df), idx + 3)
        context = df.iloc[start:end][['PLAYTYPE', 'PLAYER', 'PLAYER_ID', 'CODETEAM', 'MARKERTIME', 'MINUTE', 'POINTS_A', 'POINTS_B']]
        
        print("\nContext (surrounding rows):")
        print(context)
        
        with open("assist_context.txt", "w") as f:
            f.write(context.to_string())
            
    else:
        print("No assists found in this game!?")

if __name__ == "__main__":
    inspect_assists()
