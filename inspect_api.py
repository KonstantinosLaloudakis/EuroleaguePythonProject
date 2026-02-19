from euroleague_api import standings, player_stats
import inspect
from euroleague_api import player_stats

def inspect_api():
    print("--- Standings.get_standings ---")
    try:
        print(inspect.signature(standings.Standings.get_standings))
        print(standings.Standings.get_standings.__doc__)
    except Exception as e:
        print(e)
    
    print("--- Standings.__init__ ---")
    try:
        print(inspect.signature(standings.Standings.__init__))
    except Exception as e:
        print(e)

    # print("\n--- PlayerStats.get_player_stats ---")
    try:
        print(inspect.signature(player_stats.PlayerStats.get_player_stats))
        print(player_stats.PlayerStats.get_player_stats.__doc__)
    except Exception as e:
        print(e)
        
    # Also check the module level functions if class ones fail
    # print("\n--- Module Level Checks ---")
    # print(dir(standings))

if __name__ == "__main__":
    inspect_api()
