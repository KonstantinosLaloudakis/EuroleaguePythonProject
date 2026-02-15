import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import requests
from io import BytesIO
from euroleague_api import shot_data
import os
from PIL import Image

# --- Configuration ---
START_SEASON = 2007 
END_SEASON = 2025
# Define minimum shots per zone dynamically
MIN_SHOTS_CONFIG = {
    "Restricted Area": 30,
    "Paint (Non-RA)": 20,
    "Mid-Range Center": 10,
    "Mid-Range Right Elbow": 10,
    "Mid-Range Left Elbow": 10,
    "Mid-Range Right Baseline": 10,
    "Mid-Range Left Baseline": 10,
    "Top 3": 25,
    "Right Wing 3": 25,
    "Left Wing 3": 25,
    "Right Corner 3": 10,
    "Left Corner 3": 10
}
DEFAULT_MIN_SHOTS = 15

def fetch_shot_data(start_season, end_season):
    cache_file = f"shot_data_{start_season}_{end_season}.csv"
    
    if os.path.exists(cache_file):
        print(f"Loading cached shot data from {cache_file}...")
        try:
            # Low memory=False to avoid mixed type warnings if any
            return pd.read_csv(cache_file, low_memory=False)
        except Exception as e:
            print(f"Error reading cache: {e}. Fetching fresh data...")
            
    print(f"Fetching shot data from {start_season} to {end_season}...")
    try:
        shots = shot_data.ShotData()
        # Note: The library method name might vary slightly depending on version, 
        # but the previous code used get_game_shot_data_multiple_seasons and it worked.
        df = shots.get_game_shot_data_multiple_seasons(start_season, end_season)
        
        if not df.empty:
            print(f"Saving data to {cache_file}...")
            df.to_csv(cache_file, index=False)
            
        return df
    except Exception as e:
        print(f"Error fetching data: {e}")
        return pd.DataFrame()

def classify_zone(row):
    x = row['COORD_X']
    y = row['COORD_Y']
    action = row['ID_ACTION']
    
    # Dimensions in cm
    dist = np.sqrt(x**2 + y**2)
    
    # 1. Restricted Area (RA) - 1.25m radius
    if dist <= 125:
        return "Restricted Area"
        
    # 2. Paint (Non-RA)
    # Euroleague Paint: 4.9m wide (-245 to 245), 5.8m long (-157.5 to 422.5)
    in_paint_width = -245 <= x <= 245
    in_paint_length = -157.5 <= y <= 422.5
    if in_paint_width and in_paint_length:
        return "Paint (Non-RA)"

    # 3. Corner 3s
    # X > 660 (conceptually) AND Y < 300
    is_corner_area = abs(x) >= 660 and y <= 300
    
    if is_corner_area:
         if x < 0: return "Left Corner 3"
         else: return "Right Corner 3"
         
    # 3pt Line Logic for non-corners
    # Arc R = 675
    # If dist > 675 AND not corner -> Above Break
    
    # Check if 3pt shot (based on ID_ACTION or distance)
    # Be careful: long 2s exist. 
    # Use distance > 675 OR ID_ACTION == '3FGM'/'3FGA'
    is_3pt_action = '3FG' in action
    is_long_dist = dist >= 675
    
    if is_3pt_action or (is_long_dist and not is_corner_area):
        # Above Break Zones
        angle = np.degrees(np.arctan2(y, x))
        if angle < 0: angle += 360
        
        if angle < 70:
            return "Right Wing 3"
        elif angle < 110:
            return "Top 3"
        else:
            return "Left Wing 3"
            
    # 4. Mid-Range (Everything else)
    # Split into 5 zones based on angle
    angle = np.degrees(np.arctan2(y, x))
    if angle < 0: angle += 360
    
    if angle < 30:
        return "Mid-Range Right Baseline"
    elif angle < 70:
        return "Mid-Range Right Elbow"
    elif angle < 110:
        return "Mid-Range Center"
    elif angle < 150:
        return "Mid-Range Left Elbow"
    else:
        return "Mid-Range Left Baseline"

def get_zone_master(df):
    results = {}
    
    # Add 'Points' column
    # We need to manually calculate points or ensure it's there.
    # The previous code had df['Points'] calculated before calling this or inside.
    # Let's ensure it's calculated here just in case.
    
    def get_points(row):
        action = row['ID_ACTION']
        if '2FGM' in action or 'DUNK' in action or 'LAYUP' in action:
            return 2
        elif '3FGM' in action:
            return 3
        return 0

    # Ensure Points column exists (it might be calculated outside, but let's be safe)
    if 'Points' not in df.columns:
        df['Points'] = df.apply(get_points, axis=1) # Warning: slow for large DFs, but robust
        
    # Determine Team Column
    # Check what columns we have
    team_col = 'CODETEAM' if 'CODETEAM' in df.columns else 'TEAM'
    if team_col not in df.columns:
        # Fallback if neither exists (unlikely in this dataset)
        print("Warning: No Team column found (checked CODETEAM, TEAM)")
        # Create a dummy column to avoid error
        df['TEAM_DUMMY'] = 'UNK'
        team_col = 'TEAM_DUMMY'

    # Filter out empty zones
    zones = df['Zone'].unique()
    
    for zone in zones:
        if not isinstance(zone, str): continue
        
        # Filter for this zone
        zone_df = df[df['Zone'] == zone].copy()
        if zone_df.empty: continue
        
        # Calculate stats per player
        # Use simple aggregation
        # We group by Player and ID. We grab the team from the first row.
        stats = zone_df.groupby(['PLAYER', 'ID_PLAYER']).agg(
            Points=('Points', 'sum'),
            Attempt=('Points', 'count'),
            TEAM=(team_col, 'first')
        ).reset_index()
        
        # Threshold
        min_shots = MIN_SHOTS_CONFIG.get(zone, DEFAULT_MIN_SHOTS)
        qualified = stats[stats['Attempt'] >= min_shots]
        
        if qualified.empty:
            continue
            
        qualified['PPS'] = qualified['Points'] / qualified['Attempt']
        
        # Sort
        qualified = qualified.sort_values(by=['PPS', 'Attempt'], ascending=[False, False])
        top = qualified.iloc[0]
        
        results[zone] = {
            "Zone": zone,
            "PLAYER": top['PLAYER'],
            "ID_PLAYER": top['ID_PLAYER'],
            "Points": int(top['Points']),
            "Attempt": int(top['Attempt']),
            "TEAM": top['TEAM'],
            "PPS": top['PPS'],
            "PLAYER_ID": top['ID_PLAYER']
        }
        
    return results

def get_player_image(player_name, player_id):
    """
    Attempts to load a player image from the local 'player_cards/player_images' directory.
    Format is 'LASTNAME FIRSTNAME.webp' (uppercase).
    """
    if not player_name:
        return None

    # Cleaning and formatting the name
    # The dataset usually provides "First Last" or "Last, First". 
    # The filenames are "LAST FIRST.webp".
    
    # Expected format on disk: "PUNTER KEVIN.webp"
    # Input `player_name` example: "Kevin Punter"
    
    # Input `player_name` example: "Kevin Punter" or "PUNTER, KEVIN"
    
    # Sanitize input: remove commas immediately
    parts = player_name.upper().replace(',', '').split()
    if len(parts) >= 2:
        # Construct "LAST FIRST.webp"
        # Most simple case: parts[0] is First, parts[-1] is Last.
        # But we need "LAST FIRST".
        
        # Try 1: Last First (Standard 2 names)
        # Kevin Punter -> PUNTER KEVIN
        candidate1 = f"{parts[-1]} {parts[0]}.webp"
        
        # Try 2: First Last (Just in case)
        candidate2 = f"{parts[0]} {parts[-1]}.webp"
        
        # Try 3: Last First Middle (if 3 parts)
        # e.g. "Juancho Hernangomez" might be HERNANGOMEZ JUANCHO
        # "Nigel Hayes-Davis" -> HAYES-DAVIS NIGEL
        
        candidates = [candidate1, candidate2]
        
        # If there are more than 2 parts, it gets tricky.
        # e.g. "Van Rossom Sam" -> VAN ROSSOM SAM
        if len(parts) > 2:
            # Try combining last two as surname? or first two as firstname?
            # Let's try strict "Last First" using the list order logic
            # Assuming input is "First Middle Last" -> "Last First Middle"
            # Filenames seem to be "SURNAME FIRSTNAME"
            
            # Let's iterate through all files to find a fuzzy match? 
            # might be slow if done every time.
            pass

    else:
        # Single name?
        candidates = [f"{parts[0]}.webp"]

    image_dir = os.path.join(os.getcwd(), "player_cards", "player_images")
    
    # Check candidates
    found_path = None
    for c in candidates:
        p = os.path.join(image_dir, c)
        if "OKEKE" in player_name.upper():
            print(f"[DEBUG] Checking candidate for {player_name}: {p} | Exists: {os.path.exists(p)}")
            
        if os.path.exists(p):
            found_path = p
            # print(f"[DEBUG] Found exact match: {p}")
            break
            
    if not found_path:
        try:
            all_files = os.listdir(image_dir)
            # Remove commas from input name to ensure clean tokenization
            name_upper = player_name.upper().replace(',', '')
            input_tokens = set(name_upper.split())
            
            for f in all_files:
                if f.endswith(".webp"):
                    fname_no_ext = f[:-5]
                    file_tokens = set(fname_no_ext.split())
                    
                    if input_tokens.issubset(file_tokens):
                         found_path = os.path.join(image_dir, f)
                         break
        except Exception as e:
            print(f"Error searching directory: {e}")

    if found_path:
        try:
            img = Image.open(found_path)
            img.load() # Force load
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            return img
        except Exception as e:
            print(f"Error loading local image {found_path}: {e}")
            return None

    return None

def draw_court_map(results, season):
    plt.figure(figsize=(12, 12))
    ax = plt.gca()
    
    # Reuse drawing logic...
    lw = 2
    color = 'black'
    
    # (Simplified for brevity, assuming verify_coords.py logic)
    ax.add_line(plt.Line2D([-90, 90], [-37.5, -37.5], color=color, linewidth=lw))
    ax.add_line(plt.Line2D([-750, 750], [-157.5, -157.5], color=color, linewidth=lw))
    ax.plot([-245, -245], [-157.5, 422.5], color=color, linewidth=lw)
    ax.plot([245, 245], [-157.5, 422.5], color=color, linewidth=lw)
    ax.plot([-245, 245], [422.5, 422.5], color=color, linewidth=lw)
    ax.add_patch(patches.Arc((0, 0), 250, 250, theta1=0, theta2=180, linewidth=lw, color=color))
    ax.add_patch(patches.Circle((0, 0), radius=22.5, linewidth=lw, color=color, fill=False))
    
    corner_x = 660
    intersection_y = np.sqrt(675**2 - corner_x**2)
    ax.plot([corner_x, corner_x], [-157.5, intersection_y], color=color, linewidth=lw)
    ax.plot([-corner_x, -corner_x], [-157.5, intersection_y], color=color, linewidth=lw)
    theta = np.degrees(np.arctan2(intersection_y, corner_x))
    ax.add_patch(patches.Arc((0, 0), 1350, 1350, theta1=theta, theta2=180-theta, linewidth=lw, color=color))
    
    # Annotate Zones
    # Define approximate centroids for each zone to place text/image
    centroids = {
        "Restricted Area": (0, 50),     # Moved slightly down from 60
        "Paint (Non-RA)": (0, 320),     # Moved UP from 250 to separate from Restricted Area
        "Mid-Range Center": (0, 550),   # Moved up slightly from 500 to keep spacing
        "Mid-Range Right Elbow": (400, 300),
        "Mid-Range Left Elbow": (-400, 300),
        "Mid-Range Right Baseline": (400, 50),
        "Mid-Range Left Baseline": (-400, 50),
        "Top 3": (0, 800),
        "Right Wing 3": (600, 600),
        "Left Wing 3": (-600, 600),
        "Right Corner 3": (700, 0),
        "Left Corner 3": (-700, 0)
    }
    
    for zone, data in results.items():
        if zone not in centroids: continue
        x, y = centroids[zone]
        
        name = data['PLAYER'] 
        disp_name = name.split(',')[0] 
        
        pps = data['PPS']
        pid = data['PLAYER_ID']
        
        # Text
        text = f"{disp_name}\nPPS: {pps:.2f}"
        
        # Try Image
        img_obj = get_player_image(name, pid)
        if img_obj:
            try:
                # Resize image to a fixed height to ensure consistency
                
                # Default height
                target_height = 120
                
                # Paint zones are crowded, make them smaller?
                # Actually, 80 might be too small if we have space now.
                # Let's try 90 for paint.
                if zone in ["Restricted Area", "Paint (Non-RA)"]:
                    target_height = 90
                
                aspect_ratio = img_obj.width / img_obj.height
                target_width = int(target_height * aspect_ratio)
                
                img_resized = img_obj.resize((target_width, target_height), Image.Resampling.LANCZOS)
                
                imagebox = OffsetImage(img_resized, zoom=1.0) 
                ab = AnnotationBbox(imagebox, (x, y), frameon=False)
                ab.set_zorder(50)
                ax.add_artist(ab)
                print(f"Added image for {name} at {x},{y} (Size: {target_width}x{target_height})")
                
                # Dynamic Text Offset
                # Place text below the image.
                # Image extends from y - height/2 to y + height/2 (in display units roughly?)
                # Actually OffsetImage is in data coords if frameon=False? 
                # No, box is centered.
                # Let's use a dynamic offset based on height.
                # For 120px, offset ~80 was barely enough.
                # Let's try offset = target_height * 0.75
                
                text_offset = target_height * 0.75
                
                ax.text(x, y - text_offset, text, ha='center', va='top', fontsize=8, fontweight='bold', 
                        bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'), zorder=51)
            except Exception as e:
                print(f"Error adding image to plot: {e}")
                # Fallback to text only
                ax.text(x, y, text, ha='center', va='center', fontsize=9, fontweight='bold',
                        bbox=dict(facecolor='white', alpha=0.7, edgecolor='black'))
        else:
            # No image found, text only
            ax.text(x, y, text, ha='center', va='center', fontsize=9, fontweight='bold',
                    bbox=dict(facecolor='white', alpha=0.7, edgecolor='black'))

    plt.title(f"The Zone Master: Most Efficient Scorers by Zone ({season})\nVariable Min Attempts (10-30)", fontsize=14)
    plt.xlim(-800, 800)
    plt.ylim(-200, 1000)
    plt.gca().set_aspect('equal')
    plt.axis('off')
    
    plt.savefig(f"zone_master_{season}.png")
    print(f"Saved zone_master_{season}.png")


def main():
    for season in range(START_SEASON, END_SEASON + 1):
        print(f"\n--- Processing Season {season} ---")
        df = fetch_shot_data(season, season)
        if df.empty: 
            print(f"No data for {season}")
            continue
        
        # Ensure numeric
        df['COORD_X'] = pd.to_numeric(df['COORD_X'], errors='coerce')
        df['COORD_Y'] = pd.to_numeric(df['COORD_Y'], errors='coerce')
        df = df.dropna(subset=['COORD_X', 'COORD_Y'])
        
        df['Zone'] = df.apply(classify_zone, axis=1)
        
        results = get_zone_master(df)
        
        # Save JSON results specific to season
        import json
        with open(f"zone_master_{season}.json", "w") as f:
            json.dump(results, f, indent=4)
            
        print(f"Top Players by Zone ({season}):")
        for z, d in results.items():
            print(f"{z}: {d['PLAYER']} ({d['PPS']:.2f} PPS)")
            
        draw_court_map(results, season)

if __name__ == "__main__":
    main()
