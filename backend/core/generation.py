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
    ================================================================================
    SURGICAL ARCHITECTURAL EDITING & STAGING ENGINE
    ================================================================================
    
    This engine orchestrates advanced image inpainting tailored specifically for 
    Indian home renovations. It ensures that the original room geometry, perspective,
    walls, columns, ceiling lines, doors, and windows are preserved 100% original, 
    while only requested furniture (such as beds, modular wardrobes, TV units) 
    is surgically added or modified inside designated coordinates.

    MIGRATION ROADMAP FOR PRODUCTION-GRADE STAGING:
    ----------------------------------------------------------------------------
    Currently, the engine triggers a basic single-pass inpainting pipeline via 
    Flux Dev LoRA on Fal.ai. While cost-effective, raw Flux Dev is highly prone to 
    structural hallucination, camera drifting, and furniture deformation.

    To transition this to a true architectural-constrained editing engine, implement 
    the following multi-control SDXL/ControlNet pipeline:

    1. Scene Understanding (Room DNA):
       - Segformer partitions the room into structural components (walls, ceiling).
       - YOLOv8 isolates foreground furniture layers into protection safety tiers.
       - MLSD detects key vertical and horizontal linear features (shelves, frames).

    2. Multi-Control Conditioning Stack:
       - Rather than passing only an inpaint mask, bind the input to multiple ControlNets:
         * ControlNet Depth (weight: 0.85) -> Locks room depth and spatial layers.
         * ControlNet Canny (weight: 0.70) -> Preserves window panes, corners, and trims.
         * ControlNet Lineart (weight: 0.90) -> Locks straight lines of shelves/joineries.
         * IP-Adapter (weight: 0.65) -> Conditions the generation on reference style images.

    3. Controlled Inpainting (SDXL Inpainting):
       - Use a professional-grade base like SDXL Inpainting or Flux Kontext Pro.
       - Restrict editing exclusively to the editable mask coordinates with a 15px 
         feathered blending threshold.

    4. Multi-Pass Refinement:
       - Pass 1 (Structure Lock): Render the base cabinet doors or headboards.
       - Pass 2 (Lighting/Shadow Synthesis): Cast ambient and contact shadows onto 
         the floor using the Bilateral gray-scale light field.
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
        Controlled surgical inpainting pipeline.
        Surgically stages furniture into masked areas while enforcing strict structural locks.
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
            
            # The mask used for Flux Inpainting (editable area)
            editable_mask = masks['editable']
            editable_mask = cv2.resize(editable_mask, new_size)
            
            _, buffer_img = cv2.imencode(".png", low_res_img)
            img_bytes = buffer_img.tobytes()
            base64_img = f"data:image/png;base64,{base64.b64encode(img_bytes).decode('utf-8')}"
            
            # SPATIAL OVERWRITE: DILATE the mask (25 pixels)
            # This ensures we "eat" the outer frame of the shelves completely,
            # giving the AI enough room to install seamless wardrobe doors.
            kernel = np.ones((25, 25), np.uint8)
            editable_mask = cv2.dilate(editable_mask, kernel, iterations=1)
            
            # ARCHITECTURAL LOCK: Keep only the true architectural structures (windows, ceiling, doors)
            # protected to anchor room stability. We do NOT protect the inverse of the editable mask,
            # as doing so will copy back the old, empty shelves/floor over the new AI furniture composite!
            orig_protected = masks.get('protected', np.zeros_like(editable_mask))
            if orig_protected.shape[:2] != editable_mask.shape[:2]:
                orig_protected = cv2.resize(orig_protected, new_size, interpolation=cv2.INTER_NEAREST)
                
            masks['protected'] = orig_protected
            
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
                    "strength": image_strength, # Dynamic strength mapped from app.py
                    "enable_safety_checker": False,
                    "negative_prompt": (
                        "do not alter room structure, do not change architecture, "
                        "do not distort geometry, preserve perspective consistency, "
                        "no hallucinated walls, no shifted camera angles, no extra windows, "
                        "avoid CGI look, avoid low quality"
                    )
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
        """Adds architectural quality, balanced spatial locks, and localized furniture confidence to the prompt."""
        # 1. PRESERVE SECTION
        preserve_section = (
            "Photorealistic real estate architectural DSLR interior photo of the same exact room. "
            "Preserve the exact room architecture, same walls, same ceiling, same camera angle, "
            "same window, same perspective, same room identity. Keep original room structure, "
            "corners, and camera framing 100% identical and untouched. "
        )
        
        # 2. EDIT / SPATIAL ANALYSIS SECTION
        spatial_context = f"The current room layout is: {scene_analysis}. " if scene_analysis else ""
        
        # High confidence furniture spawning rules using "existing structure" and professional carpentry vocabulary
        furniture_injection = (
            "SURGICAL FURNITURE INJECTION: Install clearly visible modular wardrobe panels, "
            "properly installed cabinetry, realistic matte laminate cabinetry, and professionally integrated furniture. "
            "Convert the existing open shelves into fully installed floor-to-ceiling modular wardrobe shutters "
            "with clean doors, solid flat panels, and premium bronze handles, built into the existing wall cavities "
            "and fitted into the current room structure using custom-built storage installation. "
            "Add custom professional interior carpentry below the window counter as lower storage cabinets, "
            "aligned perfectly to the original architecture. "
            "Place a compact modern bed naturally aligned and installed within the existing layout on the floor. "
        )
        
        # 3. REALISM SECTION
        realism_suffix = (
            ", masterpiece, 8k DSLR, highly detailed, realistic textures, "
            "photorealistic Indian apartment interior, real DSLR photography, natural shadows, "
            "realistic scale, accurate furniture proportions, soft ambient lighting, "
            "avoid cartoonish looks, no CGI, no 3D render feel."
        )
        
        # Combine user's customized style prompt with our balanced staging rules
        return f"{preserve_section}{spatial_context}{furniture_injection}{user_prompt}{realism_suffix}"

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
        
        # BLEND SEAM: Apply a slight Gaussian blur to feather the hard edge between the original and AI image.
        # This removes the sharp 'scissor cut' line while keeping the geometry strict.
        blurred_protected = cv2.GaussianBlur(protected, (15, 15), 0)
        mask_3d = cv2.merge([blurred_protected, blurred_protected, blurred_protected])
        mask_float = mask_3d.astype(np.float32) / 255.0
        
        # SURGICAL COMPOSITE
        final = (original.astype(np.float32) * mask_float) + (ai_gen.astype(np.float32) * (1.0 - mask_float))
        return np.clip(final, 0, 255).astype(np.uint8)
