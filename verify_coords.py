import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from euroleague_api import shot_data

def draw_court(ax=None, color='black', lw=2):
    if ax is None:
        ax = plt.gca()
        
    # Euroleague Court Dimensions (cm)
    # Hoop is at (0, 0) usually in these APIs, but let's see.
    # If Y goes to 1400 (14m), then 0,0 is likely the center of the hoop projected on floor.
    
    # 3pt Arc
    # Radius 675cm
    # Corner width?
    
    # Let's draw circles at critical distances to see alignment
    
    # Rim
    rim = patches.Circle((0, 0), radius=22.5, linewidth=lw, color=color, fill=False)
    ax.add_patch(rim)
    
    # Backboard (approx 1.2m behind hoop center? No, hoop comes out 1.2m from baseline usually)
    # If (0,0) is hoop, baseline is at Y = -120?? Or is Y=0 the baseline?
    # Previous check: Y min was -1. Y max 740.
    # This suggests Y=0 is Hoop, and it goes "up" towards halfcourt.
    # Backboard
    # 1.2m from baseline. Hoop center is 0.375m in front of backboard.
    # So Backboard Y = -37.5 cm.
    # Width 1.8m (180cm) -> -90 to 90
    backboard = plt.Line2D([-90, 90], [-37.5, -37.5], color=color, linewidth=lw, alpha=0.8)
    ax.add_line(backboard)
    
    # Stem/Connector to Baseline (optional)
    ax.plot([0, 0], [-37.5, -157.5], color=color, linewidth=lw*0.5, linestyle='--')

    # Baseline
    # Hoop is 1.575m from endline. Y = -157.5
    baseline = plt.Line2D([-750, 750], [-157.5, -157.5], color=color, linewidth=lw)
    ax.add_line(baseline)
    
    # Restricted Area (1.25m radius semi-circle)
    ra = patches.Arc((0, 0), 250, 250, theta1=0, theta2=180, linewidth=lw, color=color)
    ax.add_patch(ra)
    
    # Paint (Rectangular 4.9m wide)
    # Width 490, so -245 to 245
    # Length: Baseline to Free Throw (5.8m from endline = 4.225m from hoop center)
    ax.plot([-245, -245], [-157.5, 422.5], color=color, linewidth=lw)
    ax.plot([245, 245], [-157.5, 422.5], color=color, linewidth=lw)
    ax.plot([-245, 245], [422.5, 422.5], color=color, linewidth=lw)
    
    import numpy as np
    
    # 3pt Line
    # Euroleague: R=675cm. Corners min 0.9m from sideline.
    # Sideline X = 750 (15m width). Corner 3 X = 750 - 90 = 660cm.
    # Intersection: 660^2 + y^2 = 675^2  => y approx 141.5
    corner_x = 660
    intersection_y = np.sqrt(675**2 - corner_x**2) # ~141.5
    
    # Right Corner Line
    ax.plot([corner_x, corner_x], [-157.5, intersection_y], color=color, linewidth=lw)
    # Left Corner Line
    ax.plot([-corner_x, -corner_x], [-157.5, intersection_y], color=color, linewidth=lw)
    
    # Arc
    # Angle calculation
    # theta = arctan(y/x)
    theta = np.degrees(np.arctan2(intersection_y, corner_x))
    
    # Arc goes from theta to 180-theta
    three_arc = patches.Arc((0, 0), 1350, 1350, theta1=theta, theta2=180-theta, linewidth=lw, color=color)
    ax.add_patch(three_arc)
    
    return ax

def main():
    try:
        print("Fetching shot data for verification...")
        shots = shot_data.ShotData()
        # Get shots for one game
        df = shots.get_game_shot_data(2024, 1)
        
        if df.empty:
            print("No data found.")
            return

        plt.figure(figsize=(10, 10))
        draw_court()
        
        # Plot Misses
        misses = df[~df['ID_ACTION'].isin(['2FGM', '3FGM', 'FTM'])] # FTM usually no coords
        plt.scatter(misses['COORD_X'], misses['COORD_Y'], c='red', alpha=0.5, label='Miss', s=20)
        
        # Plot Makes
        makes = df[df['ID_ACTION'].isin(['2FGM', '3FGM'])]
        plt.scatter(makes['COORD_X'], makes['COORD_Y'], c='green', alpha=0.5, label='Make', s=20)
        
        plt.legend()
        plt.title("Shot Coordinates Verification (Season 2024, Game 1)")
        plt.xlim(-800, 800)
        plt.ylim(-200, 1400)
        plt.gca().set_aspect('equal')
        
        plt.savefig("court_verification.png")
        print("Saved court_verification.png")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
