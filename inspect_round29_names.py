import xml.etree.ElementTree as ET

def inspect_names():
    try:
        tree = ET.parse('official_schedule_2025.xml')
        root = tree.getroot()
        r29 = [i for i in root.findall('item') if i.find('gameday').text == '29']
        
        print(f"Found {len(r29)} games in Round 29:")
        for g in r29:
            h = g.find('hometeam').text
            a = g.find('awayteam').text
            print(f'Home: "{h}" | Away: "{a}"')
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_names()
