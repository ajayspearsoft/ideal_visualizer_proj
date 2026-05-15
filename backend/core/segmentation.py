import cv2
import numpy as np
import os
from ultralytics import YOLO
from typing import Dict, List, Tuple, Optional

class SegmentationEngine:
    """
    Production-grade Architectural Protection & Masking Engine.
    Uses YOLOv11-seg (Nano) for high-speed, lightweight segmentation.
    """
    def __init__(
        self,
        yolov11_model=None,
        scene_model=None,
        scene_processor=None,
        device: Optional[str] = None,
    ):
        """
        Hybrid Segmentation Engine.
        Uses YOLO for objects/furniture and SegFormer for architectural structure.
        """
        self.yolo = yolov11_model
        self.scene_model = scene_model
        self.scene_processor = scene_processor
        if device is not None:
            self.device = str(device)
        elif scene_model is not None:
            import torch
            try:
                p = next(scene_model.parameters())
                self.device = str(p.device)
            except StopIteration:
                self.device = "cpu"
        elif yolov11_model is not None:
            import torch
            try:
                p = next(yolov11_model.model.parameters())
                self.device = str(p.device)
            except (StopIteration, AttributeError):
                self.device = "cpu"
        else:
            self.device = "cpu"
        
        # SegFormer ADE20K indices for structural elements
        # 1: wall, 3: floor, 4: ceiling, 9: window, 15: door
        self.ADE_STRUCTURAL_IDS = [1, 4, 9, 15] 

        # YOLO COCO labels for editable objects
        self.EDITABLE_LABELS = [
            'chair', 'couch', 'bed', 'dining table', 'refrigerator', 'sink', 'toilet'
        ]

    def generate_masks(self, image: np.ndarray, room_type: str = "living room", skeleton: np.ndarray = None) -> Dict[str, np.ndarray]:
        """
        Generates hybrid masks using SegFormer + YOLO + Canny Skeleton.
        """
        h, w = image.shape[:2]
        protected_mask = np.zeros((h, w), dtype=np.uint8)
        
        # 1. HARD GEOMETRY LOCK (via Canny Skeleton)
        if skeleton is not None:
            print("[CANNY] Geometry lock applied to protected mask.", flush=True)
            # Dilate edges slightly to create a safety 'buffer' around junctions
            dilated_skeleton = cv2.dilate(skeleton, np.ones((3, 3), np.uint8), iterations=1)
            protected_mask = cv2.bitwise_or(protected_mask, dilated_skeleton)
        
        # 1. ARCHITECTURAL PROTECTION (via SegFormer)
        if self.scene_model and self.scene_processor:
            import torch
            inputs = self.scene_processor(images=image, return_tensors="pt").to(self.device)
            with torch.no_grad():
                outputs = self.scene_model(**inputs)
                logits = outputs.logits.cpu()
                upsampled_logits = torch.nn.functional.interpolate(
                    logits, size=image.shape[:2], mode='bilinear', align_corners=False
                )
                seg_map = upsampled_logits.argmax(dim=1)[0].numpy()
                
                # Protect: Ceiling (4), Windows (9), Doors (15)
                # Walls (1) are partially protected (we lock the junction but allow face editing)
                for ade_id in [4, 9, 15]:
                    protected_mask[seg_map == ade_id] = 255

        # 2. OBJECT DETECTION (via YOLO)
        if self.yolo:
            results = self.yolo.predict(image, conf=0.25, verbose=False, device=self.device)
            if results[0].masks is not None:
                for i, mask_data in enumerate(results[0].masks.xy):
                    cls_id = int(results[0].boxes.cls[i])
                    label = self.yolo.names[cls_id].lower()
                    
                    # If YOLO detects something that should be protected (like a permanent sink)
                    if 'sink' in label or 'toilet' in label:
                        mask_poly = np.array(mask_data, dtype=np.int32)
                        temp_mask = np.zeros((h, w), dtype=np.uint8)
                        cv2.fillPoly(temp_mask, [mask_poly], 255)
                        protected_mask = cv2.bitwise_or(protected_mask, temp_mask)

        # 3. THE INVERSE STRATEGY (The AI Playground)
        editable_mask = np.ones((h, w), dtype=np.uint8) * 255
        editable_mask[protected_mask > 0] = 0
        
        # Safety Margin: Protect the very top of the room (Ceiling)
        protected_mask[:int(h*0.08), :] = 255
        editable_mask[:int(h*0.08), :] = 0

        # 1. Base Editable Zone (Start with almost full room)
        editable_mask = np.ones((h, w), dtype=np.uint8) * 255
        
        # 2. Subtract Structural Boundaries
        editable_mask[protected_mask > 0] = 0
        
        # 3. Create 'Furniture Placement Zone' (Central Focus)
        # We allow more creativity in the bottom-middle of the room
        creative_margin_w = int(w * 0.1)
        creative_margin_h = int(h * 0.15)
        central_zone = np.zeros((h, w), dtype=np.uint8)
        cv2.rectangle(central_zone, (creative_margin_w, creative_margin_h), (w - creative_margin_w, h), 255, -1)
        
        # Combine masks
        editable_mask = cv2.bitwise_or(editable_mask, central_zone)
        editable_mask[protected_mask > 0] = 0 # Final architectural safety check

        # 4. REFINEMENT
        editable_mask = cv2.erode(editable_mask, np.ones((7, 7), np.uint8), iterations=1)
        editable_mask = self._apply_room_type_prior(editable_mask, room_type)
        editable_mask_final = cv2.GaussianBlur(editable_mask, (13, 13), 0)

        # 5. Metrics & Diagnostics
        total_pixels = h * w
        prot_perc = (np.sum(protected_mask == 255) / total_pixels) * 100
        edit_perc = (np.sum(editable_mask > 0) / total_pixels) * 100

        print(f"\n--- [GEOMETRY ENGINE METRICS] ---")
        print(f"[PROTECTED AREA %]: {prot_perc:.1f}%")
        print(f"[EDITABLE AREA %]: {edit_perc:.1f}%")
        print(f"[MASK COVERAGE]: {edit_perc:.1f}%")

        # 6. Distance Transform (Structural Blending)
        dist_transform = cv2.distanceTransform(editable_mask, cv2.DIST_L2, 5)
        cv2.normalize(dist_transform, dist_transform, 0, 1.0, cv2.NORM_MINMAX)
        alpha_mask = cv2.GaussianBlur(dist_transform, (15, 15), 0)

        return {
            'protected': protected_mask,
            'editable': editable_mask_final,
            'alpha': alpha_mask,
            'debug': self._create_visual_debug(image, protected_mask, editable_mask)
        }

    def _apply_room_type_prior(self, editable_mask: np.ndarray, room_type: str) -> np.ndarray:
        """
        Soft spatial guidance for bedroom layout.
        No restrictive binary AND - returns the mask largely open so the model
        can actually furnish an empty room. Guidance comes from the prompt, not the mask.
        """
        room_key = (room_type or "").strip().lower()
        if room_key != "bedroom":
            return editable_mask
        return editable_mask

    def apply_restoration(self, original: np.ndarray, ai_generated: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """
        The 'Architectural Anchor' step.
        Pastes original windows/doors back onto AI image using seamless blending.
        """
        # Ensure identical sizes
        ai_generated = cv2.resize(ai_generated, (original.shape[1], original.shape[0]))
        
        # Simple Alpha Composite for structural elements
        # Higher performance for SaaS workers than cv2.seamlessClone
        mask_inv = cv2.bitwise_not(mask)
        
        # Restoration: Take original pixels where mask is white (protected)
        # Note: In our system, 'protected' is what we KEEP from original.
        restored = cv2.bitwise_and(original, original, mask=mask)
        ai_part = cv2.bitwise_and(ai_generated, ai_generated, mask=mask_inv)
        
        combined = cv2.add(restored, ai_part)
        
        # Final polish: Soft blur on edges only to hide the seam
        return combined

    def _create_fallback_masks(self, h, w):
        # Default to editing the whole image if CV fails
        return {
            'protected': np.zeros((h, w), dtype=np.uint8),
            'editable': np.ones((h, w), dtype=np.uint8) * 255,
            'alpha': np.ones((h, w), dtype=np.float32),
            'debug': np.zeros((h, w, 3), dtype=np.uint8) # Empty black debug image
        }

    def _create_visual_debug(self, image: np.ndarray, protected: np.ndarray, editable: np.ndarray) -> np.ndarray:
        """
        Creates a high-visibility diagnostic image.
        RED = Protected (Strict Lock)
        CYAN = Editable (AI Playground)
        """
        debug = image.copy()
        
        # Overlay Protected (Red tint)
        red_overlay = np.zeros_like(image)
        red_overlay[:] = (0, 0, 255)
        debug = np.where(protected[:, :, np.newaxis] == 255, 
                         cv2.addWeighted(debug, 0.7, red_overlay, 0.3, 0), 
                         debug)
        
        # Overlay Editable (Cyan tint)
        cyan_overlay = np.zeros_like(image)
        cyan_overlay[:] = (255, 255, 0) # BGR Cyan
        debug = np.where(editable[:, :, np.newaxis] == 255, 
                         cv2.addWeighted(debug, 0.7, cyan_overlay, 0.3, 0), 
                         debug)
        
        # Add labels
        cv2.putText(debug, "RED: PROTECTED | CYAN: EDITABLE", (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        return debug
