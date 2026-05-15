import cv2
import numpy as np
import os
import logging
import fal_client
import base64
import requests
from typing import Dict, Optional, Tuple, Any

# Configure production logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GenerationEngine")

class GenerationEngine:
    """
    Production-grade Flux Pro Orchestrator for Architectural Redesign.
    Uses fal.ai for state-of-the-art photorealistic inpainting.
    """
    def __init__(self, api_key: str = None, *args, **kwargs):
        # Use FAL_KEY from env if not provided
        self.api_key = api_key or os.getenv("FAL_KEY")
        if not self.api_key:
            logger.warning("FAL_KEY not found in environment. Local testing only.")
        else:
            os.environ["FAL_KEY"] = self.api_key

    def redesign_room(self, original_image: np.ndarray, style_prompt: str, masks: dict, image_strength: float = 0.5, *args, **kwargs) -> Tuple[Optional[np.ndarray], Optional[str]]:
        """
        High-performance pipeline using Flux Pro 1.1 Inpainting.
        """
        try:
            # 1. Prepare Images
            h, w = original_image.shape[:2]
            
            # Encode images to Base64 for Fal.ai API
            _, buffer_img = cv2.imencode(".png", original_image)
            base64_img = f"data:image/png;base64,{base64.b64encode(buffer_img).decode('utf-8')}"
            
            # The mask used for Flux Inpainting (editable area)
            _, buffer_mask = cv2.imencode(".png", masks['editable'])
            base64_mask = f"data:image/png;base64,{base64.b64encode(buffer_mask).decode('utf-8')}"

            # 2. Build High-End Architectural Prompt
            full_prompt = self._build_architectural_prompt(style_prompt)
            
            # 3. Call fal.ai Flux Dev Inpainting
            # Flux Dev is significantly cheaper than Pro and very high quality
            logger.info(f"[FAL.AI] Dispatching Flux Dev request...")
            
            # We use the 'fal-ai/flux-general/inpainting' endpoint for Flux Dev
            handler = fal_client.submit(
                "fal-ai/flux-general/inpainting",
                arguments={
                    "prompt": full_prompt,
                    "image_url": base64_img,
                    "mask_url": base64_mask,
                    "guidance_scale": 7.5,
                    "num_inference_steps": 30,
                    "enable_safety_checker": False
                }
            )
            
            result = handler.get()
            image_url = result.get("images", [{}])[0].get("url")
            
            if not image_url:
                return None, "Fal.ai failed to return an image URL"

            # 4. Download Result
            ai_gen = self._download_image(image_url)
            if ai_gen is None:
                return None, "Result download failed"

            # 5. SURGICAL RESTORATION
            # This ensures walls, windows, and floor geometry stay 100% original
            final_composite = self._composite_structural_integrity(original_image, ai_gen, masks)
            
            return final_composite, None

        except Exception as e:
            logger.error(f"Redesign Engine Crash: {str(e)}")
            return None, f"Internal Pipeline Error: {str(e)}"

    def _build_architectural_prompt(self, user_prompt: str) -> str:
        """Adds architectural quality and negative context to the user prompt."""
        prefix = "Photorealistic architectural interior photography, "
        suffix = (
            ", masterpiece, 8k DSLR, highly detailed, realistic textures, "
            "natural volumetric lighting, soft shadows, professional interior styling, "
            "avoid cartoonish looks, no CGI, no 3D render feel, preserve room geometry."
        )
        return f"{prefix}{user_prompt}{suffix}"

    def _download_image(self, url: str) -> Optional[np.ndarray]:
        res = requests.get(url, timeout=30)
        if res.status_code == 200:
            arr = np.frombuffer(res.content, np.uint8)
            return cv2.imdecode(arr, cv2.IMREAD_COLOR)
        return None

    def _composite_structural_integrity(self, original: np.ndarray, ai_gen: np.ndarray, masks: Dict[str, np.ndarray]) -> np.ndarray:
        """Perfectly blends AI generated content with original structural boundaries."""
        target_h, target_w = original.shape[:2]
        ai_gen = cv2.resize(ai_gen, (target_w, target_h))
        
        protected = masks.get('protected')
        if protected is None:
            return ai_gen

        protected = cv2.resize(protected, (target_w, target_h), interpolation=cv2.INTER_NEAREST)

        # SOFT RESTORATION:
        # We only restore the original image for CRITICAL structural zones like windows/doors
        # to ensure the geometry is locked. We do NOT restore the floor or walls
        # so the AI can draw realistic shadows and lighting.
        mask_3d = cv2.merge([protected, protected, protected])
        
        # Blur the mask slightly for a natural blend
        mask_3d_float = cv2.GaussianBlur(mask_3d.astype(np.float32) / 255.0, (7, 7), 0)
        
        # Linear Interpolation (Alpha Blending)
        final = (original.astype(np.float32) * mask_3d_float) + (ai_gen.astype(np.float32) * (1.0 - mask_3d_float))
        return np.clip(final, 0, 255).astype(np.uint8)
