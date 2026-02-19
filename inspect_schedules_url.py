from euroleague_api.utils import get_requests
import pandas as pd
import json

def inspect_schedules():
    url = "https://api-live.euroleague.net/v1/schedules?seasonCode=E2025"
    print(f"Testing URL: {url}")
    
    try:
        r = get_requests(url)
        if r.ok:
            print(f"Response Text Sample: {r.text[:500]}")
            try:
                data = r.json()
            except:
                print("JSON Parse Failed. Attempting XML check...")
                import xmltodict
                data = xmltodict.parse(r.text)
                print("XML Parsed Successfully.")
            
                print("XML Parsed Successfully.")
            
            # Navigate XML structure
            if 'schedule' in data:
                schedule_data = data['schedule']
                print("Schedule Keys:", schedule_data.keys())
                
                # Check for list of games. XML lists are often under a singular key like 'item' or 'game'
                games = []
                if 'item' in schedule_data:
                    games = schedule_data['item']
                elif 'game' in schedule_data:
                    games = schedule_data['game']
                
                print(f"Total Games found in XML: {len(games)}")
                
                if len(games) > 0:
                    print("Sample Game 0:", json.dumps(games[0], indent=2))
                    
                    matches = []
                    for g in games:
                        # XML uses strings. 'round' is "RS". 'gameday' is the round number.
                        r_val = g.get('gameday', '0')
                        if str(r_val) == '29':
                            matches.append({
                                'GameCode': g.get('gamecode', 0),
                                'LocalTeam': g.get('homecode', g.get('hometeam')), 
                                'RoadTeam': g.get('awaycode', g.get('awayteam')),
                                'Winner': 'UNKNOWN'
                            })
                    
                    print(f"Round 29 Games Found: {len(matches)}")
                    if len(matches) > 0:
                        print(json.dumps(matches, indent=2))
                        with open('manual_round_29.json', 'w') as f:
                             json.dump(matches, f, indent=4)
                             print("Saved REAL manual_round_29.json")
        else:
            print(f"Error: {r.status_code}")
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    inspect_schedules()
