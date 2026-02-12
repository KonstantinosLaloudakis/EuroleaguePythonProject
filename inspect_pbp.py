from euroleague_api import play_by_play_data
import pandas as pd

pbp = play_by_play_data.PlayByPlay()
# Get one game from 2023 season, gamecode 1 (just a guess for a valid game)
data = pbp.get_game_play_by_play_data(2023, 1)
df = pd.DataFrame(data)
print(df.columns)
print(df[['pbp.markTime', 'pbp.type', 'pbp.score']].head(10))
