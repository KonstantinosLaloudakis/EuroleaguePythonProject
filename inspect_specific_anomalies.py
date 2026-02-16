import json

def inspect():
    with open('lineup_stats_2man_100_2025.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    # Sort by NetRating ascending (worst first)
    data.sort(key=lambda x: x['NetRating'])
    
    print("Bottom 5 Net Ratings:")
    for entry in data[:5]:
        print(json.dumps(entry, indent=2))

if __name__ == "__main__":
    inspect()
