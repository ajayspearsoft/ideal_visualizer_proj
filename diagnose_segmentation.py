import cv2
import numpy as np
import os
import sys
import torch
from transformers import SegformerImageProcessor, SegformerForSemanticSegmentation

# Add backend to path
sys.path.append(os.path.abspath("backend"))

try:
    from backend.core.segmentation import SegmentationEngine
    print("Successfully imported SegmentationEngine!")
except Exception as e:
    print(f"Import error: {e}")
    sys.exit(1)

import glob
room_images = glob.glob("backend/uploads/debug_canny_*.png")
if not room_images:
    print("No room images found in uploads folder!")
    sys.exit(0)

sample_img_path = max(room_images, key=os.path.getctime)
print(f"Analyzing sample image: {sample_img_path}")

img = cv2.imread(sample_img_path)
if img is None:
    print("Failed to load image!")
    sys.exit(1)

# Let's initialize SegFormer
print("Loading SegFormer model...")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model_id = "nvidia/segformer-b0-finetuned-ade-512-512"
processor = SegformerImageProcessor.from_pretrained(model_id)
model = SegformerForSemanticSegmentation.from_pretrained(model_id).to(device)
model.eval()

# Let's initialize the engine
engine = SegmentationEngine(
    yolov11_model=None,
    scene_model=model,
    scene_processor=processor,
    device=device
)

print("Running generate_masks...")
masks = engine.generate_masks(img, room_type="bedroom")

editable = masks.get('editable')
protected = masks.get('protected')

print(f"Editable mask shape: {editable.shape if editable is not None else 'None'}")
print(f"Protected mask shape: {protected.shape if protected is not None else 'None'}")

if editable is not None:
    non_zero = np.sum(editable > 0)
    total = editable.size
    print(f"Editable non-zero pixels: {non_zero} ({non_zero / total * 100:.2f}%)")
    # Print the range of values in editable mask
    print(f"Editable mask values min: {editable.min()}, max: {editable.max()}")

if protected is not None:
    non_zero_prot = np.sum(protected > 0)
    total_prot = protected.size
    print(f"Protected non-zero pixels: {non_zero_prot} ({non_zero_prot / total_prot * 100:.2f}%)")
