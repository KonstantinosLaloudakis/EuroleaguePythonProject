import json

def parse_column_string(col_str):
    """Parses a dataframe-like string into a dict {index: value}"""
    result = {}
    lines = col_str.strip().split('\n')
    fail_count = 0
    for i, line in enumerate(lines):
        parts = line.strip().split(None, 1)
        if len(parts) >= 2:
            idx_str = parts[0]
            val = parts[1]
            try:
                idx = int(idx_str)
                result[idx] = val
            except ValueError:
                if fail_count < 5:
                    print(f"Failed to parse int from line {i}: {line!r}")
                fail_count += 1
                continue
        else:
            if fail_count < 5:
                print(f"Failed split line {i}: {line!r}")
            fail_count += 1
            continue
    print(f"Parsed {len(result)} items. Failed {fail_count} lines.")
    return result

def load_and_parse_teams():
    with open("teamNames.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    codes_map = parse_column_string(data['team1'])
    names_map = parse_column_string(data['team2'])
    
    # Iterate through indices that exist in both
    common_indices = set(codes_map.keys()) & set(names_map.keys())

    print(f"Codes map size: {len(codes_map)}")
    print(f"Names map size: {len(names_map)}")
    print(f"Common indices: {len(common_indices)}")
    
    mapping = {}

    
    # Check specific indices
    if 30 in codes_map: print(f"Code[30]: {codes_map[30]!r} -> Name[30]: {names_map.get(30)!r}")
    if 14 in codes_map: print(f"Code[14]: {codes_map[14]!r} -> Name[14]: {names_map.get(14)!r}")
    if 86 in codes_map: print(f"Code[86]: {codes_map[86]!r} -> Name[86]: {names_map.get(86)!r}")

    pan_updates = []
    
    for idx in sorted(common_indices):
        code_entry = codes_map[idx].strip()
        name_entry = names_map[idx].strip()
        
        # Handle multiple codes separated by ;
        # The code entry might be "ULK;IST"
        sub_codes = code_entry.split(';')
        for sc in sub_codes:
            sc = sc.strip()
            if sc:
                 mapping[sc] = name_entry
                 if sc == "PAN":
                     pan_updates.append((idx, name_entry))
                     
    return mapping, pan_updates

m, pan_updates = load_and_parse_teams()
print(f"Loaded {len(m)} mappings.")
print("PAN updates:")
for p in pan_updates:
    print(p)

print(f"Final PAN -> {m.get('PAN')}")

