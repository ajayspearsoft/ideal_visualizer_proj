import cv2
import numpy as np
import torch
import os
import time

class DepthEngine:
    def __init__(self, model=None, transform=None):
        """
        Encapsulates MiDaS Depth Estimation logic.
        Uses the globally loaded MiDaS instance from app.py.
        """
        self.model = model
        self.transform = transform
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        if self.model:
            self.model.to(self.device)
            self.model.eval()

    def generate_depth_map(self, image: np.ndarray) -> np.ndarray:
        """
        Generates a high-quality normalized depth map from a BGR image.
        """
        if self.model is None or self.transform is None:
            print("[DEPTH ERROR] MiDaS model not initialized.")
            return np.zeros(image.shape[:2], dtype=np.uint8)

        start_time = time.time()
        print("[DEPTH] MiDaS inference started...", flush=True)

        # 1. Pre-process (BGR -> RGB -> Transform)
        img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        input_batch = self.transform(img_rgb).to(self.device)

        # 2. Inference
        with torch.no_grad():
            prediction = self.model(input_batch)

            # Resize to original resolution
            prediction = torch.nn.functional.interpolate(
                prediction.unsqueeze(1),
                size=image.shape[:2],
                mode="bicubic",
                align_corners=False,
            ).squeeze()

        depth_raw = prediction.cpu().numpy()

        # 3. Normalization (0-255)
        depth_min = depth_raw.min()
        depth_max = depth_raw.max()
        
        if depth_max - depth_min > 0:
            depth_norm = (depth_raw - depth_min) / (depth_max - depth_min)
        else:
            depth_norm = depth_raw

        depth_uint8 = (depth_norm * 255).astype(np.uint8)

        # 4. Smoothing (Reduce noise for architectural stability)
        depth_uint8 = cv2.bilateralFilter(depth_uint8, 9, 75, 75)

        print(f"[DEPTH] Depth map generated in {(time.time() - start_time)*1000:.2f}ms", flush=True)
        return depth_uint8

    def analyze_spatial_zones(self, depth_map: np.ndarray) -> dict:
        """
        Uses depth information to extract architectural zones.
        Identifies: Floor Plane, Background Walls, Close Objects.
        """
        h, w = depth_map.shape
        
        # 1. Floor Detection (Usually high depth in center/bottom)
        # We sample the bottom 30% of the image
        bottom_strip = depth_map[int(h*0.7):, :]
        avg_floor_depth = np.mean(bottom_strip)
        
        # 2. Wall Detection (Usually mid-high depth in center)
        center_zone = depth_map[int(h*0.3):int(h*0.7), int(w*0.3):int(w*0.7)]
        avg_wall_depth = np.mean(center_zone)

        # 3. Detect "Deepest" point (Vanishing Point approximation)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(depth_map)

        print(f"[DEPTH] Spatial zones extracted. Max Depth Loc: {max_loc}", flush=True)

        return {
            "avg_floor_depth": float(avg_floor_depth),
            "avg_wall_depth": float(avg_wall_depth),
            "vanishing_point_approx": max_loc,
            "max_depth_val": float(max_val)
        }

    def create_depth_overlay(self, image: np.ndarray, depth_map: np.ndarray) -> np.ndarray:
        """
        Creates a JET colormap overlay for visual debugging.
        """
        depth_color = cv2.applyColorMap(depth_map, cv2.COLORMAP_JET)
        overlay = cv2.addWeighted(image, 0.6, depth_color, 0.4, 0)
        
        # Add labels
        cv2.putText(overlay, "DEPTH MAP (JET)", (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        return overlay
