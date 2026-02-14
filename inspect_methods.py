from euroleague_api import shot_data, boxscore_data, play_by_play_data

print("\n--- ShotData Methods ---")
shots = shot_data.ShotData()
for m in dir(shots):
    if not m.startswith('_'):
        print(m)

print("--- BoxScoreData Methods ---")
# box = boxscore_data.BoxScoreData()
# print([m for m in dir(box) if not m.startswith('_')])
