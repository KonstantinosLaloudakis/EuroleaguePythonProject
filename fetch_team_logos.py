import requests
import os
import json

def fetch_logos():
    url = "https://api-live.euroleague.net/v2/clubs?seasonCode=E2025"
    try:
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Error fetching clubs: {response.status_code}")
            return
            
        data = response.json()
        
        if isinstance(data, dict):
            print(f"DEBUG: Root keys: {list(data.keys())}")
            # Try to find the list
            if 'results' in data:
                clubs = data['results']
            elif 'data' in data:
                clubs = data['data']
            elif 'clubs' in data:
                clubs = data['clubs']
            else:
                 # Check if it's just the dict itself? unlikely based on "total"
                 print("Could not find list of clubs in response.")
                 return
        elif isinstance(data, list):
            clubs = data
        else:
            print("Unknown response format.")
            return

        # Ensure directory exists
        if not os.path.exists('logos'):
            os.makedirs('logos')
            
        print(f"Found {len(clubs)} clubs. Downloading logos...")
        
        for club in clubs:
            code = club.get('code')
            images = club.get('images', {})
            crest_url = images.get('crest')
            
            if code and crest_url:
                try:
                    img_data = requests.get(crest_url).content
                    file_path = f"logos/{code}.png"
                    with open(file_path, 'wb') as f:
                        f.write(img_data)
                    print(f"Downloaded {code}.png")
                except Exception as e:
                    print(f"Failed to download {code}: {e}")
            else:
                print(f"Skipping {code}: No crest URL found.")
                
    except Exception as e:
        print(f"API Error: {e}")

if __name__ == "__main__":
    fetch_logos()
