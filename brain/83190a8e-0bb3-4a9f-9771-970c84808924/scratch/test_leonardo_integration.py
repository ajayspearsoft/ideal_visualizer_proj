import os
import requests
import json
import io
from PIL import Image
from dotenv import load_dotenv

# Load environment variables
load_dotenv('d:/Ideal_trendzzz_visuals/ideal_visualizer_proj/backend/.env')

API_KEY = os.getenv("LEONARDO_API_KEY")
API_URL = "https://cloud.leonardo.ai/api/rest/v1"
MODEL_ID = "1e60896f-3c26-4296-8ecc-53e2afecc132"

def test_full_flow():
    print(f"Testing Leonardo API with Key: {API_KEY[:5]}...")
    
    # 1. Create dummy image and mask
    init_img = Image.new('RGB', (1024, 768), color=(100, 100, 100))
    mask_img = Image.new('L', (1024, 768), color=0)
    # Draw a white rectangle for inpainting (the "floor")
    from PIL import ImageDraw
    draw = ImageDraw.Draw(mask_img)
    draw.rectangle([100, 500, 900, 700], fill=255)
    
    init_buffer = io.BytesIO()
    init_img.save(init_buffer, format="PNG")
    init_bytes = init_buffer.getvalue()
    
    mask_buffer = io.BytesIO()
    mask_img.save(mask_buffer, format="PNG")
    mask_bytes = mask_buffer.getvalue()
    
    # 2. Get Presigned URLs
    print("Step 1: Getting presigned URLs...")
    payload = {"initExtension": "png", "maskExtension": "png"}
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {API_KEY}"
    }
    resp = requests.post(f"{API_URL}/canvas-init-image", json=payload, headers=headers)
    if not resp.ok:
        print(f"FAILED to get URLs: {resp.text}")
        return
    
    data = resp.json().get("uploadCanvasInitImage", {})
    init_id = data.get("initImageId")
    init_url = data.get("initUrl")
    init_fields = json.loads(data.get("initFields", "{}"))
    
    mask_id = data.get("masksImageId")
    mask_url = data.get("masksUrl")
    mask_fields = json.loads(data.get("masksFields", "{}"))
    
    # 3. Upload to S3
    print(f"Step 2: Uploading images (InitID: {init_id})...")
    # Init
    r1 = requests.post(init_url, data=init_fields, files={'file': ('init.png', init_bytes, 'image/png')})
    print(f"Init Upload Status: {r1.status_code}")
    
    # Mask
    r2 = requests.post(mask_url, data=mask_fields, files={'file': ('mask.png', mask_bytes, 'image/png')})
    print(f"Mask Upload Status: {r2.status_code}")
    
    if r1.status_code != 204 or r2.status_code != 204:
        print("Upload failed")
        return

    # 4. Trigger Generation
    print("Step 3: Triggering generation...")
    gen_payload = {
        "prompt": "luxury modern interior with white marble floor",
        "modelId": MODEL_ID,
        "num_images": 1,
        "width": 1024,
        "height": 768,
        "init_strength": 0.1,
        "canvasRequest": True,
        "canvasRequestType": "INPAINT",
        "canvasInitId": init_id,
        "canvasMaskId": mask_id
    }
    gen_resp = requests.post(f"{API_URL}/generations", json=gen_payload, headers=headers)
    if not gen_resp.ok:
        print(f"FAILED to trigger: {gen_resp.text}")
    else:
        print("SUCCESS! Generation triggered.")
        print(f"Generation ID: {gen_resp.json().get('sdGenerationJob', {}).get('generationId')}")

if __name__ == "__main__":
    test_full_flow()
