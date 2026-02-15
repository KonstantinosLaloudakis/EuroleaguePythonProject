from euroleague_api import shot_data
try:
    df = shot_data.ShotData().get_game_shot_data(2024, 1)
    for col in df.columns:
        print(col)
except Exception as e:
    print(e)
