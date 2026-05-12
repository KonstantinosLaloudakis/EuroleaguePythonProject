from lineup_utils import parse_lineup, extract_stints, FGA_TYPES, TO_TYPES, FTA_TYPES, OREB_TYPES
import pandas as pd
import numpy as np

# parse_lineup: valid input
val = "['LLULL, SERGIO', 'CAUSEUR, FABIEN', 'WILLIAMS-GOSS, NIGEL', 'TAVARES, WALTER', 'POIRIER, VINCENT']"
result = parse_lineup(val)
assert result is not None, "should parse valid lineup"
assert len(result) == 5, "should return 5 players"
assert isinstance(result, tuple), "should return tuple"
assert result == tuple(sorted(result)), "should be sorted"

# parse_lineup: invalid inputs
assert parse_lineup(None) is None, "None → None"
assert parse_lineup(float('nan')) is None, "nan → None"
assert parse_lineup("['A', 'B']") is None, "< 5 players → None"
assert parse_lineup("['A, B', 'C, D', 'E, F', 'A, B', 'G, H']") is None, "duplicate player → None"

# constants exported
assert '2FGM' in FGA_TYPES
assert 'TO' in TO_TYPES

print("OK: lineup_utils validation passed")
