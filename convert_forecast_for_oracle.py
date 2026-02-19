import json

def convert():
    try:
        with open('round_29_forecast.json', 'r') as f:
            data = json.load(f)
            
        converted = []
        for game in data:
            converted.append({
                'LocalTeam': game['Home'],
                'RoadTeam': game['Away']
            })
            
        with open('manual_round_29.json', 'w') as f:
            json.dump(converted, f, indent=4)
            
        print(f"Converted {len(converted)} games to manual_round_29.json")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    convert()
