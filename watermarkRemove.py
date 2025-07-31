import cv2
import numpy as np

# Load the image
image_path = "C:/Users/klalo/Desktop/Downloaded_Images/image_1.jpg"
image = cv2.imread(image_path)

# Convert to grayscale
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

# Use adaptive thresholding to create a more precise mask
mask = cv2.adaptiveThreshold(
    gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 10
)

# Morphological operations to clean up the mask
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
mask = cv2.dilate(mask, kernel, iterations=1)
mask = cv2.erode(mask, kernel, iterations=1)

# Separate processing for each watermark (optional step for improvement)
# You can split the mask into regions based on contours and process each region separately.

# Apply inpainting with TELEA method
inpainted_image = cv2.inpaint(image, mask, inpaintRadius=5, flags=cv2.INPAINT_TELEA)

# Save the improved result
output_path = "C:/Users/klalo/Desktop/Downloaded_Images/image_1B.jpg"
cv2.imwrite(output_path, inpainted_image)

print(f"Improved watermark removal. Image saved to {output_path}")
