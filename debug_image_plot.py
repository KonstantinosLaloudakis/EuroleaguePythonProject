import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import os
from PIL import Image
import numpy as np

def debug_plot():
    # Path to a known image
    image_dir = os.path.join(os.getcwd(), "player_cards", "player_images")
    test_file = "PUNTER KEVIN.webp"
    path = os.path.join(image_dir, test_file)
    
    print(f"Testing image: {path}")
    if not os.path.exists(path):
        print("File does not exist!")
        return

    try:
        img = Image.open(path)
        print(f"Image opened. Format: {img.format}, Mode: {img.mode}, Size: {img.size}")
        
        # Test 1: PIL Object
        fig, ax = plt.subplots(figsize=(5, 5))
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        
        try:
            print("Attempting OffsetImage with PIL object...")
            ib = OffsetImage(img, zoom=0.15)
            ab = AnnotationBbox(ib, (50, 50), frameon=False)
            ax.add_artist(ab)
            ax.text(50, 40, "PIL Test", ha='center')
            plt.savefig("debug_plot_pil.png")
            print("Saved debug_plot_pil.png")
        except Exception as e:
            print(f"PIL plotting failed: {e}")

        # Test 2: Numpy Array
        fig, ax = plt.subplots(figsize=(5, 5))
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        
        try:
            print("Attempting OffsetImage with Numpy Array...")
            arr = np.array(img)
            print(f"Array shape: {arr.shape}, dtype: {arr.dtype}")
            ib = OffsetImage(arr, zoom=0.15)
            ab = AnnotationBbox(ib, (50, 50), frameon=False)
            ax.add_artist(ab)
            ax.text(50, 40, "Numpy Test", ha='center')
            plt.savefig("debug_plot_numpy.png")
            print("Saved debug_plot_numpy.png")
        except Exception as e:
            print(f"Numpy plotting failed: {e}")
            
    except Exception as e:
        print(f"Image load failed: {e}")

if __name__ == "__main__":
    debug_plot()
