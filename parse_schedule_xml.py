import xml.etree.ElementTree as ET
import json
import re

def parse_schedule():
    try:
        tree = ET.parse('official_schedule_2025.xml')
        root = tree.getroot()
        
        mapping = {}
        
        # XML structure seems to be <schedule><item>...</item>...</schedule>
        # Based on snippet: <item><gameday>1</gameday>...<gamecode>E2025_7</gamecode>
        
        print(f"Root tag: {root.tag}")
        
        for item in root.findall('item'):
            gameday = item.find('gameday').text
            gamecode_str = item.find('gamecode').text
            
            # Extract number from E2025_7 -> 7
            match = re.search(r'E\d+_(\d+)', gamecode_str)
            if match:
                game_num = int(match.group(1))
                mapping[str(game_num)] = int(gameday)
            else:
                print(f"Skipping malformed gamecode: {gamecode_str}")
                
        # Save mapping
        with open('game_code_to_round.json', 'w') as f:
            json.dump(mapping, f, indent=4)
            
        print(f"Successfully mapped {len(mapping)} games to rounds.")
        print("Sample mappings:")
        for k in list(mapping.keys())[:5]:
            print(f"Game {k} -> Round {mapping[k]}")
            
    except Exception as e:
        print(f"Error parsing XML: {e}")

if __name__ == "__main__":
    parse_schedule()
