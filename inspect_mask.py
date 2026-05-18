import cv2
import numpy as np
import glob
import os

mask_files = glob.glob("d:/Ideal_trendzzz_visuals/ideal_visualizer_proj/backend/uploads/debug_mask_*.png")
if not mask_files:
    print("No debug masks found!")
    exit(0)

latest_mask = max(mask_files, key=os.path.getctime)
print(f"Latest mask path: {latest_mask}")

img = cv2.imread(latest_mask)
h, w, c = img.shape
print(f"Mask resolution: {w}x{h}")

# Print unique colors
unique_colors = np.unique(img.reshape(-1, c), axis=0)
print("Unique BGR colors in the debug mask:")
for color in unique_colors:
    print(color)
