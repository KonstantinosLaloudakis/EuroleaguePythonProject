import inspect
from euroleague_api import player_stats

try:
    sig = inspect.signature(player_stats.PlayerStats.get_player_stats)
    print(f"Signature: {sig}")
except Exception as e:
    print(f"Error: {e}")
