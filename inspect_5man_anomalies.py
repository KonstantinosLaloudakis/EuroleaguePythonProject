import json

def inspect():
    try:
        with open('lineup_stats_5man_100_2025.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("5-man file not found.")
        return
        
    print(f"Loaded {len(data)} 5-man lineups.")
    
    # Just print them all, sorted by minutes desc
    data.sort(key=lambda x: x['Minutes'], reverse=True)
    
    for i, entry in enumerate(data):
        print(f"{i+1}. {entry['Lineup'][:50]}... | Min: {entry['Minutes']:.1f} | Net: {entry['NetRating']:.1f}")

if __name__ == "__main__":
    inspect()
