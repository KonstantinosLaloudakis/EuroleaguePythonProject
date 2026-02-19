import requests
import json

url = "https://api-live.euroleague.net/v1/schedules?seasonCode=E2025"
try:
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    
    # Save to file for inspection
    with open('official_schedule_2025.json', 'w') as f:
        json.dump(data, f, indent=4)
        
    print(f"Successfully fetched {len(data)} rounds/games.")
    
    # Print sample to understand structure
    # Usually it's a list of rounds or games
    if isinstance(data, list):
        print("Sample Item:", json.dumps(data[0], indent=2))
        
except Exception as e:
    print(f"Error: {e}")
