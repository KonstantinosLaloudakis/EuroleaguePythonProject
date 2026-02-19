import xml.etree.ElementTree as ET

def extract():
    try:
        tree = ET.parse('official_schedule_2025.xml')
        root = tree.getroot()
        r29 = [i for i in root.findall('item') if i.find('gameday').text == '29']
        
        with open('r29_matchups.txt', 'w', encoding='utf-8') as f:
            for g in r29:
                h = g.find('hometeam').text
                a = g.find('awayteam').text
                line = f"Home: {h} | Away: {a}\n"
                f.write(line)
                print(line.strip())
                
        print(f"Saved {len(r29)} matchups to r29_matchups.txt")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    extract()
