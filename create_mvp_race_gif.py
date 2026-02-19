import imageio
import os

def create_mvp_race_gif():
    image_folder = 'mvp_race_images'
    gif_name = 'mvp_race.gif'
    
    images = []
    # Sort files naturally
    filenames = sorted([f for f in os.listdir(image_folder) if f.endswith('.png')])
    
    if not filenames:
        print("No images found!")
        return

    print(f"Combining {len(filenames)} images into GIF...")
    
    for filename in filenames:
        images.append(imageio.imread(os.path.join(image_folder, filename)))
        
    # Duration: 1 second per frame? Or faster?
    # 28 rounds -> 28 seconds is too long.
    # 0.5s per frame -> 14s. OK.
    # Last frame longer.
    
    durations = [0.8] * (len(images) - 1) + [4.0] # 4 seconds for final image
    
    imageio.mimsave(gif_name, images, duration=durations, loop=0)
    print(f"Saved {gif_name}")

if __name__ == "__main__":
    create_mvp_race_gif()
