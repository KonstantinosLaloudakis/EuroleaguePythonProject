from euroleague_api import play_by_play_data
methods = dir(play_by_play_data.PlayByPlay)
for m in methods:
    print(m)
