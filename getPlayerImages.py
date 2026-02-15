import requests
import os

HEADERS = {"User-Agent": "Mozilla/5.0"}
LIMIT = 100
SEASONS = [f"E{year}" for year in range(2007, 2016)]
SAVE_FOLDER = "player_cards/player_images"

os.makedirs(SAVE_FOLDER, exist_ok=True)

for season in SEASONS:
    print(f"Processing season: {season}")
    OFFSET = 0

    while True:
        BASE_URL = f"https://feeds.incrowdsports.com/provider/euroleague-feeds/v2/competitions/E/seasons/{season}/people"
        params = {
            "personType": "J",
            "Limit": LIMIT,
            "Offset": OFFSET,
            "active": "true",
            "search": "",
            "sortBy": "name"
        }

        response = requests.get(BASE_URL, headers=HEADERS, params=params)
        data = response.json().get("data", [])

        if not data:
            break

        for player in data:
            player_name = player.get("person", {}).get("name", "").replace(",", "")
            if not player_name:
                continue

            filename = f"{player_name}.webp"
            filepath = os.path.join(SAVE_FOLDER, filename)

            if os.path.exists(filepath):
                continue  # Skip if image already exists

            image_url = player.get("images")
            if isinstance(image_url, str):  # Sometimes "images" is a string, not a dict
                continue
            image_url = image_url.get("headshot") if image_url else None

            if image_url:
                try:
                    img_data = requests.get(image_url).content
                    with open(filepath, "wb") as f:
                        f.write(img_data)
                    print(f"Downloaded: {filename}")
                except Exception as e:
                    print(f"Failed to download {filename}: {e}")

        OFFSET += LIMIT
