import re
import json

with open("profile.html", "r", encoding="utf-8") as f:
    content = f.read()

# Extract __NEXT_DATA__
match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', content)

if match:
    json_str = match.group(1)
    try:
        data = json.loads(json_str)
        
        # Save to file
        with open("next_data.json", "w", encoding="utf-8") as outfile:
            json.dump(data, outfile, indent=4)
        print("Saved next_data.json")
        
        # Print PageProps keys
        props = data.get('props', {})
        pageProps = props.get('pageProps', {})
        print("PageProps Keys:", list(pageProps.keys()))

    except json.JSONDecodeError as e:
        print(f"JSON Error: {e}")
else:
    print("No __NEXT_DATA__ found.")
