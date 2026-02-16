import euroleague_api
try:
    from euroleague_api import utils
    print("Found euroleague_api.utils")
    if hasattr(utils, 'get_pbp_lineups'):
        print("Found get_pbp_lineups in euroleague_api.utils")
    else:
        print("get_pbp_lineups NOT found in euroleague_api.utils")
except ImportError:
    print("euroleague_api.utils NOT found")

# Check top level
if hasattr(euroleague_api, 'get_pbp_lineups'):
    print("Found get_pbp_lineups in euroleague_api")
