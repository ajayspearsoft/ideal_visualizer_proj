import requests
import time
import cv2
import numpy as np
import os
import logging
import json
from typing import Dict, Optional, Tuple, Any

# Configure production logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GenerationEngine")

class GenerationEngine:
    """
    Production-safe Leonardo AI Orchestrator with Geometric Restoration.
    """
    def __init__(self, api_key: str, model_id: str = "1e60896f-3c26-4296-8ecc-53e2afecc132"):
        if not api_key:
            raise ValueError("LEONARDO_API_KEY is required for the GenerationEngine.")
        
        self.api_key = api_key
        self.model_id = model_id
        self.base_url = "https://cloud.leonardo.ai/api/rest/v1"
        self.headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {self.api_key}"
        }

    def redesign_room(self, original_image: np.ndarray, style_prompt: str, masks: dict, image_strength: float = 0.2, depth_data: dict = None) -> Tuple[Optional[np.ndarray], Optional[str]]:
        """
        Production pipeline for depth-aware room redesign.
        """
        try:
            # 1. Image & Prompt Pre-processing
            h, w = original_image.shape[:2]
            
            # Incorporate depth cues into the prompt if available
            enhanced_style = style_prompt
            if depth_data:
                depth_cue = f"Perspective aligned with deep floor plane (depth: {depth_data.get('avg_floor_depth', 0):.0f}). "
                enhanced_style = f"{depth_cue} {style_prompt}"
            if max(h, w) > 1024:
                scale = 1024 / max(h, w)
                original_image = cv2.resize(original_image, (int(w * scale), int(h * scale)))
                logger.info(f"Resized image for API: {original_image.shape}")

            # 2. Upload Assets to Leonardo (Canvas Session)
            logger.info("[GENERATION] Uploading Canvas Assets (Init + Mask)...")
            init_image_id, mask_image_id, valid_w, valid_h = self._upload_canvas_assets(original_image, masks['editable'])
            
            if not init_image_id or not mask_image_id:
                return None, "Canvas asset upload failed"

            # 3. Start Generation
            full_prompt = self._build_production_prompt(enhanced_style)
            logger.info(f"[GENERATION] Triggering generation ({valid_w}x{valid_h}) with prompt: {full_prompt[:100]}...")
            generation_id = self._trigger_generation(init_image_id, mask_image_id, full_prompt, image_strength, width=valid_w, height=valid_h)
            if not generation_id:
                return None, "Generation trigger failed"

            # 4. Polling with Exponential Backoff
            logger.info(f"Generation started: {generation_id}. Polling...")
            image_url = self._poll_generation(generation_id)
            if not image_url:
                return None, "Generation timed out or failed on cloud"

            # 5. Download AI Result
            ai_gen = self._download_image(image_url)
            if ai_gen is None:
                return None, "Result download failed"

            # 6. SURGICAL RESTORATION (The 'Golden' Composite)
            final_composite = self._composite_structural_integrity(original_image, ai_gen, masks)
            
            return final_composite, None

        except Exception as e:
            logger.error(f"Redesign Engine Crash: {str(e)}")
            return None, f"Internal Pipeline Error: {str(e)}"

    def _build_production_prompt(self, user_prompt: str) -> str:
        """Enforces mandatory architectural preservation via silent backend append logic."""
        preservation = (
            "ARCHITECTURAL INTEGRITY: Maintain exact room dimensions and perspective. "
            "Preserve original window, door, and ceiling positions. "
            "Transform the interior with new furniture, wardrobes, lighting, and premium textures."
        )
        
        pos = f"(Masterpiece:1.2), {user_prompt}, {preservation}, photorealistic, sharp focus, 8k, realistic lighting"
        neg = "distorted walls, moving windows, shifted doors, curved lines, melting structure, blurry, extra furniture, messy layout"
        return f"{pos} --neg {neg}"

    def _upload_canvas_assets(self, image: np.ndarray, mask: np.ndarray) -> Tuple[Optional[str], Optional[str], int, int]:
        """Leonardo's specialized Canvas upload flow for linked Init/Mask assets."""
        try:
            # 1. PRE-VALIDATE DIMENSIONS (Must be multiples of 8 for Canvas)
            h, w = image.shape[:2]
            max_dim = 1024
            if w > max_dim or h > max_dim:
                scale = max_dim / max(w, h)
                w = int(w * scale)
                h = int(h * scale)
            
            # Snap to 8-pixel grid
            w = (w // 8) * 8
            h = (h // 8) * 8
            
            image = cv2.resize(image, (w, h))
            mask = cv2.resize(mask, (w, h))

            # Step A: Request dual presigned S3 URLs
            payload = {"initExtension": "png", "maskExtension": "png"}
            res = requests.post(f"{self.base_url}/canvas-init-image", json=payload, headers=self.headers)
            
            if res.status_code != 200:
                logger.error(f"Canvas Init Step A failed: {res.status_code} - {res.text}")
                return None, None, w, h
            
            data = res.json().get("uploadCanvasInitImage", {})
            init_id = data.get("initImageId")
            mask_id = data.get("masksImageId")
            
            init_url = data.get("initUrl")
            init_fields = json.loads(data.get("initFields", "{}"))
            
            mask_url = data.get("masksUrl")
            mask_fields = json.loads(data.get("masksFields", "{}"))

            # Step B: Multipart POST for Init Image
            _, buf_init = cv2.imencode('.png', image)
            requests.post(init_url, data=init_fields, files={'file': ('init.png', buf_init.tobytes(), 'image/png')})
            
            # Step C: Multipart POST for Mask Image
            _, buf_mask = cv2.imencode('.png', mask)
            requests.post(mask_url, data=mask_fields, files={'file': ('mask.png', buf_mask.tobytes(), 'image/png')})
            
            logger.info(f"Canvas Assets Uploaded. Init: {init_id}, Mask: {mask_id} ({w}x{h})")
            return init_id, mask_id, w, h

        except Exception as e:
            logger.error(f"Canvas Upload Exception: {str(e)}")
            return None, None, 0, 0

    def _trigger_generation(self, init_id: str, mask_id: str, prompt: str, strength: float, width: int = 1024, height: int = 768) -> Optional[str]:
        """Triggers the Leonardo generation using the verified Canvas Request schema."""
        
        # 1. Leonardo Dimensions MUST be multiples of 8
        # We cap at 1024 and ensure divisibility
        max_dim = 1024
        if width > max_dim or height > max_dim:
            scale = max_dim / max(width, height)
            width = int(width * scale)
            height = int(height * scale)
            
        # Force multiples of 8
        width = (width // 8) * 8
        height = (height // 8) * 8
            
        # 2. Balanced Geometry settings
        guidance = 7
        strength = 0.25
        
        print(f"[GUIDANCE STRENGTH]: {strength} (Creativity: {1-strength})")
            
        payload = {
            "height": height,
            "width": width,
            "modelId": self.model_id,
            "prompt": prompt,
            "init_strength": strength,
            "guidance_scale": guidance, 
            "num_images": 1,
            "public": False,
            "canvasRequest": True,
            "canvasRequestType": "INPAINT",
            "canvasInitId": init_id,
            "canvasMaskId": mask_id
        }

        logger.info(f"[LEONARDO] DISPATCHING CANVAS REQUEST TO: {self.base_url}/generations")
        logger.info(f"[LEONARDO] PAYLOAD: {json.dumps(payload, indent=2)}")

        try:
            res = requests.post(f"{self.base_url}/generations", json=payload, headers=self.headers)
            logger.info(f"[LEONARDO] STATUS: {res.status_code}")
            
            if res.status_code != 200:
                logger.error(f"Generation Trigger failed: {res.status_code} - {res.text}")
                return None
                
            return res.json().get("sdGenerationJob", {}).get("generationId")
        except Exception as e:
            logger.error(f"Generation Dispatch Exception: {str(e)}")
            return None

    def _poll_generation(self, gen_id: str, max_retries: int = 20) -> Optional[str]:
        """Polls for result with increasing sleep intervals."""
        for i in range(max_retries):
            time.sleep(2 + (i // 5)) # Exponential backoff
            res = requests.get(f"{self.base_url}/generations/{gen_id}", headers=self.headers)
            if res.status_code == 200:
                gen = res.json().get("generations_by_pk", {})
                images = gen.get("generated_images", [])
                if images: return images[0]["url"]
                if gen.get("status") == "FAILED": return None
        return None

    def _download_image(self, url: str) -> Optional[np.ndarray]:
        res = requests.get(url, timeout=15)
        if res.status_code == 200:
            arr = np.frombuffer(res.content, np.uint8)
            return cv2.imdecode(arr, cv2.IMREAD_COLOR)
        return None

    def _composite_structural_integrity(self, original: np.ndarray, ai_gen: np.ndarray, masks: Dict[str, np.ndarray]) -> np.ndarray:
        """
        The Core Architectural Restoration Pipeline. 
        Ensures AI results are perfectly aligned and blended with original room geometry.
        """
        target_h, target_w = original.shape[:2]
        
        # 1. Synchronize Resolutions
        ai_gen = cv2.resize(ai_gen, (target_w, target_h))
        
        # 2. Extract and Synchronize Masks
        protected = masks.get('protected')
        alpha = masks.get('alpha')

        if protected is None or alpha is None:
            logger.warning("Masks missing, returning raw AI output.")
            return ai_gen

        # Resize masks to match original resolution
        protected = cv2.resize(protected, (target_w, target_h), interpolation=cv2.INTER_NEAREST)
        alpha = cv2.resize(alpha, (target_w, target_h), interpolation=cv2.INTER_LINEAR)

        # 3. STEP A: Structural Anchor (Hard Overlay)
        # We physically paste the original high-res windows/doors back.
        mask_3d = cv2.merge([protected, protected, protected])
        restored = np.where(mask_3d == 255, original, ai_gen)

        # 4. STEP B: Seamless Alpha Blending
        # We blend the restored result with the AI generation to smooth the seams 
        # between original structural elements and new AI content.
        alpha_3d = cv2.merge([alpha, alpha, alpha])
        
        # Normalize if needed
        if alpha_3d.max() > 1:
            alpha_3d = alpha_3d / 255.0
        
        # Use float32 for blending to prevent overflow/clipping
        final = (
            restored.astype(np.float32) * alpha_3d + 
            ai_gen.astype(np.float32) * (1.0 - alpha_3d)
        ).astype(np.uint8)

        return final
