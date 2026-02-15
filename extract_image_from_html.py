import re

with open("profile.html", "r", encoding="utf-8") as f:
    content = f.read()

# Find images with Punter in alt/title or just nearby
# The player name in the profile might be 'Kevin Punter'
print("Searching for Kevin Punter images...")

# Regex for img tags with alt containing Punter (case insensitive)
img_tags = re.findall(r'<img [^>]*alt="[^"]*Punter[^"]*"[^>]*>', content, re.IGNORECASE)

for img in img_tags:
    print(f"\nFound IMG tag: {img}")
    # Extract src or data-srcset
    src = re.search(r'src="([^"]+)"', img)
    if src: print(f"Src: {src.group(1)}")
    srcset = re.search(r'data-srcset="([^"]+)"', img)
    if srcset: print(f"Data-SrcSet: {srcset.group(1)}")

# Also look for the main profile image class if known (often contains 'headshot' or 'hero')
print("\nSearching for any media-cdn images that might be the headshot...")
# We know the ID is P009862. Maybe the image file has this ID?
matches = re.findall(r'https://[^"]*media-cdn[^"]*', content)
for m in matches[:10]:
    print(m)
