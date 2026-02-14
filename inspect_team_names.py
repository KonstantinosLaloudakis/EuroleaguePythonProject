import json
import pandas as pd
import io

def inspect_names():
    try:
        with open('teamNames.json', 'r') as f:
            data = json.load(f)
        
        # Check keys
        print("Keys:", data.keys())
        
        # It seems the values are strings representing DataFrames?
        # Let's try to parse 'team1' and 'team2'
        
        # 'team1' string looks like: "0      AEK\n1      BAM..."
        # This is fixed width or space separated.
        
        t1_str = data.get('team1', '')
        t2_str = data.get('team2', '')
        
        # Let's try to parse into lines and simple split
        # We assume the first token is index, second is Code/Name?
        # For Name it might be multiple words.
        
        codes = {}
        names = {}
        
        print("\n--- Parse Team 1 (Codes) ---")
        for line in t1_str.split('\n'):
            parts = line.split(maxsplit=1)
            if len(parts) == 2:
                idx, code = parts
                codes[idx] = code.strip()
        
        print(f"Found {len(codes)} codes. Sample: {list(codes.items())[:5]}")
        
        print("\n--- Parse Team 2 (Names) ---")
        for line in t2_str.split('\n'):
            parts = line.split(maxsplit=1)
            if len(parts) == 2:
                idx, name = parts
                names[idx] = name.strip()
                
        print(f"Found {len(names)} names. Sample: {list(names.items())[:5]}")
        
        # Merge
        mapping = {}
        for idx, code in codes.items():
            if idx in names:
                mapping[code] = names[idx]
        
        print(f"\nFinal Mapping Count: {len(mapping)}")
        print("Sample Mapping:", list(mapping.items())[:5])
        
        # Save a clean version if successful
        if len(mapping) > 10:
            with open('team_code_mapping.json', 'w') as f:
                json.dump(mapping, f, indent=4)
            print("Saved clean mapping to team_code_mapping.json")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_names()
