import os
import time
import cv2
import numpy as np
import io
import asyncio
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, List
import concurrent.futures
from dotenv import load_dotenv

# Import our custom Geometry Stack
from core.geometry import GeometryEngine
from core.segmentation import SegmentationEngine
from core.generation import GenerationEngine
from core.prompt_templates import ROOM_PRESETS

# Load Environment
load_dotenv()

app = FastAPI(title="Ideal AI Interior Redesign Service")

# CORS for Production SaaS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Engines (Loaded once into memory for speed)
# Use relative paths for production deployment
geometry_engine = GeometryEngine(model_path="models/mlsd_tiny_512_fp32.onnx")
segmentation_engine = SegmentationEngine(model_path="models/yolov11n-seg.pt")
generation_engine = GenerationEngine(
    api_key=os.getenv("LEONARDO_API_KEY"),
    model_id=os.getenv("LEONARDO_MODEL_ID", "1e60896f-3c26-4296-8ecc-53e2afecc132")
)

# Thread Pool for CPU-bound Computer Vision tasks
executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

class RedesignResponse(BaseModel):
    success: bool
    final_image_url: Optional[str] = None
    debug_mask_url: Optional[str] = None
    processing_time: float
    error: Optional[str] = None

# --- HELPER FUNCTIONS ---
def process_cv_pipeline(image_bytes: bytes):
    """CPU-Bound: Runs Geometry + Segmentation in parallel threads."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # 1. Geometry Extraction
    skeleton = geometry_engine.process_image(img)
    
    # 2. Segmentation & Masking
    masks = segmentation_engine.generate_masks(img)
    
    return img, skeleton, masks

# --- THE MAIN ENDPOINT ---
@app.post("/api/redesign-room", response_model=RedesignResponse)
async def redesign_room(
    file: UploadFile = File(...),
    room_type: str = Form("living_room"),
    style: str = Form("modern"),
    custom_requirements: Optional[str] = Form(None),
    image_strength: float = Form(0.75)
):
    start_time = time.time()
    
    try:
        # 1. Image Ingestion
        contents = await file.read()
        
        # 2. Run CV Pipeline (Offload to thread pool to prevent event loop blocking)
        loop = asyncio.get_event_loop()
        original_img, skeleton, masks = await loop.run_in_executor(
            executor, process_cv_pipeline, contents
        )

        # 3. Prompt Orchestration
        base_style = ROOM_PRESETS.get(room_type, ROOM_PRESETS["living_room"])
        user_prompt = f"{style} {base_style}"
        if custom_requirements:
            user_prompt += f", {custom_requirements}"
        
        # 4. Call Leonardo Generation Pipeline (I/O Bound)
        # This handles: Upload -> Poll -> Composite -> Restoration
        final_result, err = generation_engine.redesign_room(
            original_image=original_img,
            style_prompt=user_prompt,
            masks=masks,
            image_strength=image_strength
        )

        if err:
            raise HTTPException(status_code=500, detail=err)

        # 5. Production Result Management
        # (In production, you would upload final_result to S3/R2 and return the URL)
        # For this demonstration, we assume generation_engine handles the upload
        
        # Mocking URL for this example - in reality, generation_engine returns a URL or B64
        return RedesignResponse(
            success=True,
            final_image_url="https://your-s3-bucket.com/results/final_output.png",
            processing_time=time.time() - start_time
        )

    except Exception as e:
        return RedesignResponse(
            success=False,
            error=str(e),
            processing_time=time.time() - start_time
        )

@app.get("/health")
async def health():
    return {"status": "healthy", "engines_loaded": True}

if __name__ == "__main__":
    import uvicorn
    # Use uvicorn for high-performance production serving
    uvicorn.run(app, host="0.0.0.0", port=8000)
