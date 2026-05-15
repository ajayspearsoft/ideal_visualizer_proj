import cv2
import numpy as np
import os
import logging
import fal_client
import base64
import requests
from openai import OpenAI
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
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.openai_client = OpenAI(api_key=self.openai_key) if self.openai_key else None
        
        if not self.api_key:
            logger.warning("FAL_KEY not found in environment. Local testing only.")
        else:
            os.environ["FAL_KEY"] = self.api_key

    def redesign_room(self, original_image: np.ndarray, style_prompt: str, masks: dict, image_strength: float = 0.5, *args, **kwargs) -> Tuple[Optional[np.ndarray], Optional[str]]:
        """
        High-performance pipeline using Flux Dev Inpainting with Scene Intelligence.
        """
        try:
            # 1. Prepare Images
            h, w = original_image.shape[:2]
            
            # Encode images to Base64 for Fal.ai API
            # HYPER-SAVING: Resize to max 768px to reduce Megapixel costs
            h, w = original_image.shape[:2]
            scale = 768 / max(h, w)
            new_size = (int(w * scale), int(h * scale))
            low_res_img = cv2.resize(original_image, new_size)
            
            _, buffer_img = cv2.imencode(".png", low_res_img)
            img_bytes = buffer_img.tobytes()
            base64_img = f"data:image/png;base64,{base64.b64encode(img_bytes).decode('utf-8')}"
            
            # The mask used for Flux Inpainting (editable area)
            editable_mask = masks['editable']
            editable_mask = cv2.resize(editable_mask, new_size)
            
            # SPATIAL OVERWRITE: DILATE the mask (15 pixels)
            # This ensures we "eat" the edges of the white shelves.
            kernel = np.ones((15, 15), np.uint8)
            editable_mask = cv2.dilate(editable_mask, kernel, iterations=1)
            
            # ARCHITECTURAL LOCK: Combine original protection (doors/windows)
            # with the inverse of the editable area.
            # This ensures doors/windows are NEVER overwritten.
            orig_protected = masks.get('protected', np.zeros_like(editable_mask))
            if orig_protected.shape[:2] != editable_mask.shape[:2]:
                orig_protected = cv2.resize(orig_protected, new_size, interpolation=cv2.INTER_NEAREST)
                
            masks['protected'] = cv2.bitwise_or(orig_protected, cv2.bitwise_not(editable_mask))
            
            _, buffer_mask = cv2.imencode(".png", editable_mask)
            base64_mask = f"data:image/png;base64,{base64.b64encode(buffer_mask).decode('utf-8')}"

            # 2. Scene Analysis (The 'Architectural Eye')
            # Analyze the room layout to ensure logical furniture placement
            scene_analysis = self.analyze_scene(img_bytes)
            logger.info(f"[SCENE ANALYSIS] {scene_analysis}")

            # 3. Build Tailored Architectural Prompt
            full_prompt = self._build_architectural_prompt(style_prompt, scene_analysis)
            
            # 4. Call fal.ai Flux Dev LoRA Inpainting (Cost Effective $0.035/MP)
            logger.info(f"[FAL.AI] Dispatching Flux Dev LoRA request...")
            
            handler = fal_client.submit(
                "fal-ai/flux-lora/inpainting",
                arguments={
                    "prompt": full_prompt,
                    "image_url": base64_img,
                    "mask_url": base64_mask,
                    "guidance_scale": 15.0,
                    "num_inference_steps": 28,
                    "strength": 0.82, # Surgical Integration Mode
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

    def analyze_scene(self, image_bytes: bytes) -> str:
        """Uses GPT-4o-mini Vision to understand the room layout."""
        if not self.openai_client:
            return "A room interior."
            
        try:
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Describe this room's architectural layout for an interior designer. Mention where the walls, windows, doors, and floor are. Be brief but spatial."},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}",
                                    "detail": "low"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=150,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Scene Analysis Error: {e}")
            return "A room interior."

    def _build_architectural_prompt(self, user_prompt: str, scene_analysis: str = "") -> str:
        """Adds architectural quality and spatial context to the user prompt."""
        prefix = "Photorealistic architectural interior photography, "
        spatial_context = f"The room is {scene_analysis}. " if scene_analysis else ""
        
        # GLOBAL STRUCTURAL RULES (Apply to everything)
        global_rules = (
            "SURGICAL INTEGRATION: Seamlessly add new furniture and decor into the existing space. "
            "You MUST add premium panelling and shutters over all open shelving. "
            "You MUST integrate the requested furniture (Bed, Wardrobe, AC) into the existing layout. "
            "MANDATORY: Keep all vertical lines perfectly 90 degrees. No slanting. "
            "STRICT ARCHITECTURAL LOCKDOWN: No new doors, no new windows. Preserve original structural outlines exactly."
        )
        
        suffix = (
            ", masterpiece, 8k DSLR, highly detailed, realistic textures, "
            "natural volumetric lighting, soft shadows, professional interior styling, "
            "avoid cartoonish looks, no CGI, no 3D render feel."
        )
        return f"{prefix}{spatial_context}{global_rules}{user_prompt}{suffix}"

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
        
        # We use the 'protected' mask to keep the original structures (windows/doors/etc)
        protected = masks.get('protected')
        if protected is None:
            return ai_gen

        protected = cv2.resize(protected, (target_w, target_h), interpolation=cv2.INTER_NEAREST)
        
        # KILL GHOSTING: Use a strictly binary mask for the composite
        # 255 (White) in protected mask = Keep Original Photo (Walls/Doors)
        # 0 (Black) in protected mask = Use AI Generated Design (Shelves/Cabinets)
        mask_3d = cv2.merge([protected, protected, protected])
        mask_float = mask_3d.astype(np.float32) / 255.0
        
        # SURGICAL COMPOSITE: No blurring in the editable zone means NO GHOSTING
        final = (original.astype(np.float32) * mask_float) + (ai_gen.astype(np.float32) * (1.0 - mask_float))
        return np.clip(final, 0, 255).astype(np.uint8)
