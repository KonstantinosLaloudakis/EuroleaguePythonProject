import euroleague_api
import pkgutil
import inspect

def search_package(package):
    for importer, modname, ispkg in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
        try:
            module = __import__(modname, fromlist="dummy")
            if hasattr(module, 'get_pbp_lineups'):
                print(f"FOUND: get_pbp_lineups in {modname}")
                return
        except Exception as e:
            # print(f"Error importing {modname}: {e}")
            pass
            
    print("NOT FOUND in euroleague_api")

search_package(euroleague_api)
