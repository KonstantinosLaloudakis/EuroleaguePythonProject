import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

def classify_zone(x, y):
    # Dimensions in cm
    dist = np.sqrt(x**2 + y**2)
    
    # 1. Restricted Area (RA) - 1.25m radius
    if dist <= 125:
        return "Restricted Area", "red"
        
    # 2. Paint (Non-RA)
    # Euroleague Paint: 4.9m wide (-245 to 245), 5.8m long (-157.5 to 422.5)
    in_paint_width = -245 <= x <= 245
    in_paint_length = -157.5 <= y <= 422.5
    if in_paint_width and in_paint_length:
        return "Paint (Non-RA)", "orange"

    # 3. Corner 3s
    # X > 660 (conceptually, though line is at 660, so let's say > 650 for binning)
    # Y < 150 (approx where arc starts) - let's use 300cm as the visual cutoff for "Corner" stats usually
    # Standard break point is where arc becomes straight. y ~ 141.5
    # Let's say Corner is anything below Y=200 and outside 3pt line?
    # Or just strict geometry: |X| >= 660?
    
    # 3pt Line Logic
    # Straight lines at X = +/- 660
    # Arc R = 675
    
    is_3pt = False
    if abs(x) >= 660:
        is_3pt = True
    elif dist >= 675:
        is_3pt = True
        
    if is_3pt:
        # Corner vs Above Break
        # Usually Corner is defined by the straight line part.
        # Intersection is at Y ~ 141.5. 
        # Let's be generous for "Corner stats" and say Y < 300 (Standard visual cutoff)
        if y <= 300:
            if x < 0:
                return "Left Corner 3", "blue"
            else:
                return "Right Corner 3", "purple"
        else:
            # Split Above Break into: Right Wing, Top, Left Wing
            # Use same angles as mid-range
            # Right Wing: < 70 (since it starts above corner, > ~25 deg)
            # Top: 70 - 110
            # Left Wing: > 110
            
            angle = np.degrees(np.arctan2(y, x))
            if angle < 0: angle += 360
            
            if angle < 70:
                return "Right Wing 3", "cyan"
            elif angle < 110:
                return "Top 3", "lime"
            else:
                return "Left Wing 3", "teal"
            
    # 4. Mid-Range (Everything else)
    # Split into 5 zones based on angle
    # Angle 0 is Right Sideline, 90 is Center, 180 is Left Sideline
    angle = np.degrees(np.arctan2(y, x))
    if angle < 0:
        angle += 360
        
    # Correct angle logic:
    # Right side is X > 0. arc tan(y, x) -> (0, 1) is 90. (1, 0) is 0.
    # So 0 is Right (3 o'clock). 90 is Top (12 o'clock). 180 is Left (9 o'clock).
    
    # Zones:
    # 1. Right Baseline: < 30 degrees? (Includes negative Y/Baseline area)
    # 2. Right Elbow: 30 - 70
    # 3. Center: 70 - 110
    # 4. Left Elbow: 110 - 150
    # 5. Left Baseline: > 150
    
    # Handle wrap-around or negative angles for baseline shots?
    # Shots can be at Y=-50, X=500. Angle = -5 deg.
    # normalize angle? No, straight arctan2 allows -180 to 180.
    # Let's keep it simple.
    
    raw_angle = np.degrees(np.arctan2(y, x)) # -180 to 180
    
    if raw_angle < 30:
        return "Mid-Range Right Baseline", "yellow"
    elif 30 <= raw_angle < 70:
        return "Mid-Range Right Elbow", "gold"
    elif 70 <= raw_angle < 110:
        return "Mid-Range Center", "khaki"
    elif 110 <= raw_angle < 150:
        return "Mid-Range Left Elbow", "gold"
    else: # > 150
        return "Mid-Range Left Baseline", "yellow"

def main():
    plt.figure(figsize=(10, 10))
    ax = plt.gca()
    
    # Generate Grid
    xs = np.linspace(-750, 750, 150)
    ys = np.linspace(-157.5, 1200, 150)
    
    points_x = []
    points_y = []
    colors = []
    
    for x in xs:
        for y in ys:
            zone, color = classify_zone(x, y)
            points_x.append(x)
            points_y.append(y)
            colors.append(color)
            
    # Plot Zone Colors
    plt.scatter(points_x, points_y, c=colors, alpha=0.3, s=10, marker='s')
    
    # Draw Court Lines on top
    # ... (Reuse drawing logic from before)
    lw = 2
    color = 'black'
    
    # Backboard
    ax.add_line(plt.Line2D([-90, 90], [-37.5, -37.5], color=color, linewidth=lw))
    # Baseline
    ax.add_line(plt.Line2D([-750, 750], [-157.5, -157.5], color=color, linewidth=lw))
    # Paint
    ax.plot([-245, -245], [-157.5, 422.5], color=color, linewidth=lw)
    ax.plot([245, 245], [-157.5, 422.5], color=color, linewidth=lw)
    ax.plot([-245, 245], [422.5, 422.5], color=color, linewidth=lw)
    # RA
    ax.add_patch(patches.Arc((0, 0), 250, 250, theta1=0, theta2=180, linewidth=lw, color=color))
    # Hoop
    ax.add_patch(patches.Circle((0, 0), radius=22.5, linewidth=lw, color=color, fill=False))
    
    # 3pt Line
    corner_x = 660
    intersection_y = np.sqrt(675**2 - corner_x**2)
    current_y_for_corner = max(-157.5, intersection_y) # Ensure line draws
    
    # Right Corner
    ax.plot([corner_x, corner_x], [-157.5, intersection_y], color=color, linewidth=lw)
    # Left Corner
    ax.plot([-corner_x, -corner_x], [-157.5, intersection_y], color=color, linewidth=lw)
    
    # Arc
    theta = np.degrees(np.arctan2(intersection_y, corner_x))
    ax.add_patch(patches.Arc((0, 0), 1350, 1350, theta1=theta, theta2=180-theta, linewidth=lw, color=color))

    plt.title("The Zone Master: Analysis Zones")
    plt.xlim(-800, 800)
    plt.ylim(-200, 1000)
    plt.gca().set_aspect('equal')
    
    # Legend
    legend_elements = [
        patches.Patch(facecolor='red', label='Restricted Area'),
        patches.Patch(facecolor='orange', label='Paint (Non-RA)'),
        patches.Patch(facecolor='yellow', label='Mid-Range Baseline'),
        patches.Patch(facecolor='gold', label='Mid-Range Elbow'),
        patches.Patch(facecolor='khaki', label='Mid-Range Center'),
        patches.Patch(facecolor='blue', label='Left Corner 3'),
        patches.Patch(facecolor='teal', label='Left Wing 3'),
        patches.Patch(facecolor='lime', label='Top 3'),
        patches.Patch(facecolor='cyan', label='Right Wing 3'),
        patches.Patch(facecolor='purple', label='Right Corner 3')
    ]
    plt.legend(handles=legend_elements, loc='upper right')
    
    plt.savefig("zone_visualization.png")
    print("Saved zone_visualization.png")

if __name__ == "__main__":
    main()
