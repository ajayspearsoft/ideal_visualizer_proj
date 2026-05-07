import os
import time
import os
import time
import cv2
import torch
import torch.nn as nn
import numpy as np
try:
    import fitz
except ImportError:
    fitz = None

# ==========================================
# CRITICAL: LOAD ENVIRONMENT FIRST
# ==========================================
from dotenv import load_dotenv, find_dotenv
import os

# ==========================================
# CRITICAL: LOAD ENVIRONMENT FIRST
# ==========================================
try:
    # 1. Use find_dotenv to search upwards from the current file
    env_path = find_dotenv()
    
    # 2. Manual fallback for specific project structure if find_dotenv misses
    if not env_path:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Potential paths: root (parent) or local (backend)
        paths_to_check = [
            os.path.join(os.path.dirname(current_dir), '.env'),
            os.path.join(current_dir, '.env')
        ]
        for p in paths_to_check:
            if os.path.exists(p):
                env_path = p
                break

    if env_path:
        print(f"\n[ENV CHECK] Loading .env from: {env_path}", flush=True)
        load_dotenv(env_path, override=True)
        print(f"[ENV CHECK] Environment loaded successfully.", flush=True)
    else:
        # On Railway, env vars are injected directly, so we don't need a .env file
        print(f"[ENV CHECK] .env file not found. Using system environment variables.", flush=True)
except Exception as e:
    print(f"[ENV CHECK] Environment loading error: {e}", flush=True)

import hashlib
import re
import threading
import boto3
from flask import Flask, jsonify, request, send_from_directory, make_response
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from botocore.config import Config
from pymongo import MongoClient
from bson import ObjectId
import torch.nn as nn
from concurrent.futures import ThreadPoolExecutor
import traceback
try:
    from docx import Document
except ImportError:
    Document = None

def decode_image(image_bytes):
    """Robustly decode image from bytes using OpenCV, PIL, and Base64 fallbacks."""
    import cv2
    import numpy as np
    if not image_bytes:
        return None
        
    # Attempt 1: Raw bytes (from cloud/R2)
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is not None: return img
    except: pass

    # Attempt 2: Base64 string fallback
    try:
        if isinstance(image_bytes, bytes):
            decoded_str = image_bytes.decode('utf-8')
        else:
            decoded_str = image_bytes
            
        if "base64," in decoded_str:
            decoded_str = decoded_str.split("base64,")[-1]
        import base64
        decoded = base64.b64decode(decoded_str)
        nparr = np.frombuffer(decoded, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is not None: return img
    except: pass

    # Attempt 3: PIL fallback
    try:
        from PIL import Image
        import io
        img_pil = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
    except: pass

    return None

# --- ADMIN CONFIGURATION ---
ADMIN_IDS = ["69f9e0d64957cbcc423c7410", "69fa1163d676d11942bb4662", "69f9e329fdeed38be66669702"] # Old, New, and Image-referenced Admin

# --- CLOUDFLARE R2 CONFIGURATION ---
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "idealtrendzzz")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL")

# Startup Validation
if not all([R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ACCOUNT_ID]):
    print("\n" + "!"*60)
    print("[CRITICAL] CLOUDFLARE R2 CONFIGURATION IS MISSING!")
    if not R2_ACCESS_KEY_ID: print("[CRITICAL] R2_ACCESS_KEY_ID is missing from .env")
    if not R2_ACCOUNT_ID: print("[CRITICAL] R2_ACCOUNT_ID is missing from .env")
    print(f"[DEBUG] R2_ENDPOINT calculated as: https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com")
    print("!"*60 + "\n", flush=True)

r2_client = boto3.client(
    service_name='s3',
    endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
    config=Config(signature_version='s3v4'),
    region_name='auto'
)

def upload_to_r2(file_data, object_name, content_type='image/png'):
    try:
        if not R2_ACCOUNT_ID or not R2_ACCESS_KEY_ID:
            raise ValueError("Cloudflare R2 configuration is missing in the .env file.")

        if isinstance(file_data, str):
            with open(file_data, 'rb') as f:
                data = f.read()
        else:
            data = file_data
        r2_client.put_object(
            Bucket=R2_BUCKET_NAME,
            Key=object_name,
            Body=data,
            ContentType=content_type
        )
        return f"{R2_PUBLIC_URL}/{object_name}", None
    except Exception as e:
        error_msg = str(e)
        print(f"R2 Upload Error: {error_msg}")
        return None, error_msg

# --- MONGODB CONFIGURATION ---
MONGO_URL = os.getenv("MONGODB_URL")
DB_NAME = os.getenv("DATABASE_NAME", "idealtredz")

mongo_client = MongoClient(MONGO_URL)
db = mongo_client[DB_NAME]
users_col = db["users"]
pdfs_col = db["pdfs"]
filters_col = db["filters"]
ocr_cache_col = db["ocr_cache"] # Cache for OCR results

def init_db():
    users_col.create_index("mobile", unique=True)
    users_col.create_index("email", unique=True)
    pdfs_col.create_index("user_id")
    filters_col.create_index("user_id")
    ocr_cache_col.create_index("page_url", unique=True)
    print("[DEBUG] MongoDB Connected & Indexed", flush=True)

# ==========================================
# UTILS
# ==========================================
def normalize_code(text):
    if not text: return ""
    text = text.replace(" ", "")
    text = text.replace("–", "-").replace("—", "-")
    return text.strip().upper()

# ==========================================
# OCR CONFIGURATION (EASYOCR)
# ==========================================
ocr_reader = None

def init_ocr():
    global ocr_reader
    print("[DEBUG] Initializing EasyOCR...", flush=True)
    import easyocr
    import torch
    ocr_reader = easyocr.Reader(['en'], gpu=torch.cuda.is_available())
    print("[DEBUG] EasyOCR Ready", flush=True)

# ==========================================
# CONFIGURATION
# ==========================================
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=False)

# ==========================================
# ROUTES
# ==========================================
@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "service": "Ideal Visualizer Backend",
        "message": "API is running. Use /api/rooms or other endpoints.",
        "timestamp": time.time()
    })

@app.route('/health')
def health():
    return jsonify({"status": "ok"}), 200

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

init_db()

with app.app_context():
    init_db()

# Global model instances
sam_predictor = None
yolo_model = None
scene_processor = None
scene_model = None
models_ready = False
model_loading_error = None

# Cache for performance
wall_cache = {}
texture_cache = {}
room_session_cache = {} # Production-grade session management

# Mock Room Data
ROOMS = [
    {'id': 'living-room', 'name': 'Living Room', 'image': 'https://images.unsplash.com/photo-1583847268964-b28dc8f51f92?w=800'},
    {'id': 'bedroom', 'name': 'Bedroom', 'image': 'https://images.unsplash.com/photo-1616594111350-47598ff1f61a?w=800'},
    {'id': 'kitchen', 'name': 'Kitchen', 'image': 'https://images.unsplash.com/photo-1556911223-05345a3068e4?w=800'},
    {'id': 'office', 'name': 'Office', 'image': 'https://images.unsplash.com/photo-1497366754035-f200968a6e72?w=800'}
]

def load_models():
    """Load all AI models asynchronously for faster startup."""
    global sam_predictor, yolo_model, scene_processor, scene_model, models_ready, model_loading_error
    
    print("\n[DEBUG] --- Model Loading Started ---", flush=True)
    try:
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[DEBUG] Target Device: {device}", flush=True)

        # 1. SAM (Segment Anything Model)
        print("[DEBUG] Importing SAM & Vision Libraries...", flush=True)
        from segment_anything import sam_model_registry, SamPredictor
        from ultralytics import YOLO
        from transformers import SegformerImageProcessor, SegformerForSemanticSegmentation
        
        print("[DEBUG] Loading SAM (vit_b)...", flush=True)
        sam_checkpoint = "sam_vit_b_01ec64.pth"
        if not os.path.exists(sam_checkpoint):
            print(f"[WARNING] SAM checkpoint '{sam_checkpoint}' not found locally.", flush=True)
            # Optional: Download if needed, but for now we'll just fail gracefully to avoid hanging
            print("[DEBUG] Attempting to download SAM checkpoint...", flush=True)
            try:
                import urllib.request
                url = "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth"
                urllib.request.urlretrieve(url, sam_checkpoint)
                print("[DEBUG] SAM Download Complete", flush=True)
            except Exception as e:
                raise Exception(f"Failed to download SAM model: {e}")
        
        sam = sam_model_registry["vit_b"](checkpoint=sam_checkpoint)
        sam.to(device)
        sam_predictor = SamPredictor(sam)
        print("[DEBUG] SAM Loaded Successfully", flush=True)

        # 2. YOLOv8
        print("[DEBUG] Loading YOLOv8...", flush=True)
        yolo_model = YOLO("yolov8n-seg.pt")
        yolo_model.to(device)
        print("[DEBUG] YOLOv8 Loaded Successfully", flush=True)

        # 3. SegFormer (Scene Understanding)
        print("[DEBUG] Loading SegFormer (Scene Understanding)...", flush=True)
        model_id = "nvidia/segformer-b0-finetuned-ade-512-512"
        scene_processor = SegformerImageProcessor.from_pretrained(model_id)
        scene_model = SegformerForSemanticSegmentation.from_pretrained(model_id)
        scene_model.to(device)
        scene_model.eval()
        print("[DEBUG] SegFormer Loaded Successfully", flush=True)

        # 4. OCR
        init_ocr()

        # 5. GLOBAL CPU OPTIMIZATION
        torch.set_num_threads(min(os.cpu_count(), 4)) # Optimize for multi-tenant CPU environments
        
        models_ready = True
        print("\n[DEBUG] --- All Models Loaded & Ready ---\n", flush=True)

    except Exception as e:
        model_loading_error = str(e)
        print(f"\n[ERROR] Model Loading Failed: {e}", flush=True)
        print("[DEBUG] The application will continue without AI features.\n", flush=True)

# ==========================================
# GENERAL DATA ROUTES
# ==========================================

# ==========================================
# GENERAL DATA ROUTES
# ==========================================

@app.route('/api/rooms', methods=['GET'])
def get_rooms():
    return jsonify(ROOMS)

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

def get_user_path(user_id, subfolder=None):
    if not user_id:
        user_id = "anonymous"
    user_dir = os.path.join(app.config['UPLOAD_FOLDER'], str(user_id))
    if subfolder:
        user_dir = os.path.join(user_dir, subfolder)
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
    return user_dir

def get_pdf_path(user_id, pdf_id, subfolder=None):
    user_dir = get_user_path(user_id)
    pdf_dir = os.path.join(user_dir, 'pdfs', str(pdf_id))
    if subfolder:
        pdf_dir = os.path.join(pdf_dir, subfolder)
    if not os.path.exists(pdf_dir):
        os.makedirs(pdf_dir, exist_ok=True)
    return pdf_dir

def process_pdf_background(user_id, pdf_id, pdf_filename, original_pdf_path):
    """
    OPTIMIZED: Progressive Streaming Pipeline.
    Renders, Uploads, and Updates DB page-by-page to enable instant UI feedback.
    """
    if not fitz and not original_pdf_path.lower().endswith('.docx'):
        print("[BACKGROUND ERROR] PyMuPDF (fitz) is not installed.", flush=True)
        return

    start_time = time.time()
    user_prefix = f"{user_id}" if user_id else "anonymous"
    is_docx = original_pdf_path.lower().endswith('.docx')
    
    try:
        print(f"[BACKGROUND] Processing {pdf_id} (Streaming Mode)...", flush=True)
        
        # 1. Immediate Raw File Upload
        content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' if is_docx else 'application/pdf'
        r2_pdf_path = f"{user_prefix}/pdfs/{pdf_id}/{pdf_filename}"
        public_pdf_url, pdf_err = upload_to_r2(original_pdf_path, r2_pdf_path, content_type)
        
        if pdf_err:
            print(f"[BACKGROUND ERROR] Initial upload failed: {pdf_err}", flush=True)
            return

        # 2. Open Document
        doc = None
        page_count = 0
        if not is_docx:
            doc = fitz.open(original_pdf_path)
            page_count = len(doc)
        
        # Initial DB Setup
        pdfs_col.update_one(
            {"_id": ObjectId(pdf_id)},
            {"$set": {"status": "processing", "page_count": page_count, "pages": [None] * page_count}}
        )

        # 3. PIPELINED EXECUTION: Render -> Async Upload -> Async DB Update
        # Using a higher worker count to overlap I/O and Rendering
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []

            def upload_and_notify(idx, img_data, ext):
                """Worker task for R2 upload + DB notification."""
                up_start = time.time()
                path = f"{user_prefix}/pdfs/{pdf_id}/pages/page_{idx}.{ext}"
                mime = f"image/{ext}" if ext != 'jpg' else 'image/jpeg'
                url, err = upload_to_r2(img_data, path, mime)
                if url:
                    pdfs_col.update_one(
                        {"_id": ObjectId(pdf_id)},
                        {"$set": {f"pages.{idx}": url, "processed_count": idx + 1}}
                    )
                    # print(f"[OK] Page {idx} streamed to R2 in {time.time() - up_start:.2f}s")
                return idx, url

            if is_docx:
                # Word processing remains sequential for extraction but parallel for upload
                import zipfile
                with zipfile.ZipFile(original_pdf_path, 'r') as zip_ref:
                    img_idx = 0
                    media_files = sorted([f for f in zip_ref.namelist() if f.startswith('word/media/')])
                    for file in media_files:
                        with zip_ref.open(file) as img_file:
                            img_bytes = img_file.read()
                            if len(img_bytes) > 5000:
                                ext = file.split('.')[-1].lower()
                                futures.append(executor.submit(upload_and_notify, img_idx, img_bytes, ext))
                                img_idx += 1
                page_count = img_idx
                pdfs_col.update_one({"_id": ObjectId(pdf_id)}, {"$set": {"page_count": page_count, "pages": [None] * page_count}})
            else:
                # PDF STREAMING RENDER
                for i in range(page_count):
                    render_start = time.time()
                    page = doc.load_page(i)
                    
                    # DYNAMIC RESOLUTION: Scale based on physical page size to avoid massive textures
                    # Standard 72 DPI. 1.5x is 108 DPI.
                    p_rect = page.rect
                    scale = 1.5
                    if max(p_rect.width, p_rect.height) > 2000: scale = 1.0 # High-res enough
                    
                    mat = fitz.Matrix(scale, scale)
                    pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
                    img_bytes = pix.tobytes("jpg", jpg_quality=75)
                    
                    # print(f"[RENDER] Page {i} in {time.time() - render_start:.2f}s")
                    futures.append(executor.submit(upload_and_notify, i, img_bytes, 'jpg'))
                    
                    # Prevent thread starvation in heavy CPU environments
                    if i % 5 == 0: time.sleep(0.01)

            # Wait for all uploads to complete
            for f in futures: f.result()
            if doc: doc.close()

        # 4. Finalize
        if os.path.exists(original_pdf_path): os.remove(original_pdf_path)
        total_time = time.time() - start_time
        print(f"[BACKGROUND] Streaming Finished for {pdf_id} in {total_time:.2f}s.", flush=True)
        
        pdfs_col.update_one(
            {"_id": ObjectId(pdf_id)},
            {"$set": {"status": "completed", "total_processing_time": total_time, "processed_count": page_count}}
        )

    except Exception as e:
        print(f"[BACKGROUND ERROR] {pdf_id} failed: {str(e)}", flush=True)
        traceback.print_exc()
        pdfs_col.update_one({"_id": ObjectId(pdf_id)}, {"$set": {"status": "error", "error_message": str(e)}})
    finally:
        # Prevent "forever processing" UI state
        pdfs_col.update_one({"_id": ObjectId(pdf_id), "status": "processing"}, {"$set": {"status": "completed"}})

@app.route('/api/upload-pdf', methods=['POST'])
def upload_pdf():
    user_id = request.headers.get('X-User-ID') or request.form.get('user_id')
    if 'pdf_file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['pdf_file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    start_time = time.time()
    original_name = file.filename
    file_ext = original_name.split('.')[-1].lower()
    pdf_filename = f"doc_{int(time.time())}.{file_ext}"
    
    # Save to a temporary location
    user_dir = get_user_path(user_id)
    temp_path = os.path.join(user_dir, f"temp_{int(time.time())}.pdf")
    file.save(temp_path)
    
    try:
        # Get page count instantly
        if not fitz:
            return jsonify({'error': 'PyMuPDF (fitz) is not installed on the server. Please contact admin.'}), 500
            
        doc = fitz.open(temp_path)
        page_count = len(doc)
        doc.close()
        
        # Save initial record to DB to get ID
        pdf_data = {
            "user_id": str(user_id),
            "filename": pdf_filename,
            "original_name": original_name,
            "page_count": page_count,
            "created_at": time.time(),
            "status": "processing",
            "pages": [None] * page_count # Placeholder for progressive updates
        }
        result = pdfs_col.insert_one(pdf_data)
        pdf_id = str(result.inserted_id)
        
        # Start background processing
        thread = threading.Thread(
            target=process_pdf_background, 
            args=(user_id, pdf_id, pdf_filename, temp_path),
            daemon=True
        )
        thread.start()
        
        print(f"[API] PDF {pdf_id} received. Returning success in {time.time() - start_time:.2f}s", flush=True)
        
        # Return success immediately
        return jsonify({
            'success': True,
            'pdf_id': pdf_id,
            'page_count': page_count,
            'status': 'processing'
        })
        
    except Exception as e:
        if os.path.exists(temp_path): os.remove(temp_path)
        return jsonify({'error': f"Upload failed: {str(e)}"}), 500

@app.route('/api/pdfs', methods=['GET'])
def get_pdfs():
    user_id = request.args.get('user_id') or request.headers.get('X-User-ID')
    
    rows = list(pdfs_col.find({"user_id": str(user_id)}).sort("created_at", -1))
    
    pdfs = []
    user_prefix = f"{user_id}" if user_id else "anonymous"
    for row in rows:
        pdfs.append({
            'id': str(row["_id"]),
            'original_name': row["original_name"],
        'page_count': row["page_count"],
        'created_at': row["created_at"],
        'status': row.get("status", "completed"),
        'thumbnail': row.get("pages", [None])[0] or f"{R2_PUBLIC_URL}/{user_prefix}/pdfs/{str(row['_id'])}/pages/page_0.jpg"
    })
    return jsonify(pdfs)

@app.route('/api/delete-pdf', methods=['DELETE'])
def delete_pdf():
    pdf_id = request.args.get('id')
    user_id = request.args.get('user_id') or request.headers.get('X-User-ID')
    
    if not pdf_id:
        return jsonify({'error': 'Missing PDF ID'}), 400

    try:
        # Check ownership or admin status before deletion
        pdf_item = pdfs_col.find_one({"_id": ObjectId(pdf_id)})
        
        if not pdf_item:
            return jsonify({'error': 'PDF not found'}), 404
            
        if str(pdf_item.get("user_id")) != str(user_id) and str(user_id) not in ADMIN_IDS:
            return jsonify({'error': 'Permission denied'}), 403
            
        pdfs_col.delete_one({"_id": ObjectId(pdf_id)})
        return jsonify({'success': True})
    except Exception as e:
        print(f"Delete PDF Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/pages', methods=['GET'])
def get_pages():
    user_id = request.args.get('user_id') or request.headers.get('X-User-ID')
    pdf_id = request.args.get('pdf_id')
    
    if not pdf_id:
        return jsonify({'error': 'Missing pdf_id'}), 400
        
    try:
        # Fetch PDF details from MongoDB to get page count
        pdf_item = pdfs_col.find_one({"_id": ObjectId(pdf_id)})
        if not pdf_item:
            return jsonify({'error': 'PDF record not found'}), 404
            
        page_count = pdf_item.get('page_count', 0)
        user_prefix = f"{user_id}" if user_id else "anonymous"
        # Generate URLs for all pages, but check if they are uploaded yet
        urls = []
        pages_in_db = pdf_item.get('pages', [])
        
        for i in range(page_count):
            # Use DB stored URL if available (progressive processing)
            if i < len(pages_in_db) and pages_in_db[i]:
                urls.append(pages_in_db[i])
            else:
                # Fallback to standard path if DB isn't updated yet (legacy or during processing)
                urls.append(f"{R2_PUBLIC_URL}/{user_prefix}/pdfs/{pdf_id}/pages/page_{i}.jpg")
            
        return jsonify(urls)
    except Exception as e:
        print(f"Error fetching pages: {e}")
        return jsonify([])

@app.route('/api/crop', methods=['POST'])
def crop_image():
    data = request.json
    page_url = data.get('page_url')
    x = data.get('x'); y = data.get('y'); width = data.get('width'); height = data.get('height')
    
    # Get user_id early
    user_id = request.args.get('user_id') or request.headers.get('X-User-ID')
    if not user_id:
        try:
            # Fallback: extract from URL
            if "/uploads/" in page_url:
                user_id = page_url.split('/uploads/')[1].split('/')[0]
            else:
                user_id = page_url.split('.dev/')[1].split('/')[0]
        except:
            user_id = "anonymous"

    if not all([page_url, x is not None, y is not None, width, height]):
        return jsonify({'error': 'Missing coordinates'}), 400
    
    # Handle R2 vs Local URLs
    image = None
    if page_url.startswith('http') and 'localhost' not in page_url:
        try:
            import requests
            resp = requests.get(page_url)
            if resp.ok:
                image = decode_image(resp.content)
            else:
                return jsonify({'error': f"Failed to download page from cloud: {resp.status_code}"}), 500
        except Exception as e:
            return jsonify({'error': f"Cloud download error: {str(e)}"}), 500
    
    if image is None:
        # Legacy local handling
        try:
            rel_path = page_url.split('/uploads/')[-1].replace('/', os.sep)
            img_path = os.path.join(app.config['UPLOAD_FOLDER'], rel_path)
            if os.path.exists(img_path):
                image = cv2.imread(img_path)
        except:
            pass

    if image is None:
        return jsonify({'error': 'Page image could not be retrieved from cloud or local storage.'}), 404
    
    real_x = int(x); real_y = int(y); real_w = int(width); real_h = int(height)
    ih, iw = image.shape[:2]
    real_x = max(0, min(real_x, iw - 1)); real_y = max(0, min(real_y, ih - 1))
    real_w = max(1, min(real_w, iw - real_x)); real_h = max(1, min(real_h, ih - real_y))
    
    cropped = image[real_y:real_y+real_h, real_x:real_x+real_w]
    crop_name = f"crop_{int(time.time())}.png"
    
    # Encode to memory
    is_success, buffer = cv2.imencode(".png", cropped)
    if not is_success:
        return jsonify({'error': 'Failed to encode cropped image.'}), 500
    cropped_bytes = buffer.tobytes()

    # Upload to R2
    user_prefix = f"{user_id}" if user_id else "anonymous"
    r2_crop_path = f"{user_prefix}/filters/{crop_name}"
    public_url, upload_err = upload_to_r2(cropped_bytes, r2_crop_path, 'image/png')
    
    if not public_url:
        return jsonify({'error': f'Failed to save material to cloud storage: {upload_err}'}), 500

    # Perform OCR on the crop to see if a code is inside it
    manual_code = data.get('manual_code')
    detected_codes_from_ui = data.get('detected_codes', []) # Optional: list of codes already found on page
    
    # Debug: Save the raw crop
    cv2.imwrite("debug_crop.png", cropped)
    
    if manual_code:
        detected_code = manual_code
    else:
        # 1. Try OCR directly on the crop
        detected_code = extract_code_ocr(cropped, (real_w // 2, real_h // 2))
        
        # 2. If not found, search specifically BELOW the crop (standard catalog layout)
        if not detected_code:
            search_margin = 250 # Pixels to look below
            search_top = real_y + real_h
            search_bottom = min(ih, search_top + search_margin)
            
            # Extract search area (only below)
            search_area = image[search_top:search_bottom, real_x:real_x+real_w]
            
            if search_area.size > 0:
                # Debug: Save the search area
                cv2.imwrite("debug_search.png", search_area)
                detected_code = extract_code_ocr(search_area, (real_w // 2, search_margin // 2))

        # 3. Last Resort: Find the nearest code from the UI's pre-detected list
        if not detected_code and detected_codes_from_ui:
            best_dist = float('inf')
            # Look for codes near the bottom-center of the crop
            target_x = real_x + real_w // 2
            target_y = real_y + real_h
            
            for d in detected_codes_from_ui:
                # d should have {code, x, y} in natural image coordinates
                dist = ((d['x'] - target_x)**2 + (d['y'] - target_y)**2)**0.5
                if dist < 500 and dist < best_dist: # 500px radius
                    best_dist = dist
                    detected_code = d['code']
                    print(f"[OK] Associated with nearest pre-detected code: {detected_code} (dist: {dist:.1f})")

    # Save to MongoDB
    filter_data = {
        "user_id": str(user_id),
        "image_path": public_url,
        "code": detected_code or "UNKNOWN",
        "created_at": time.time()
    }
    filters_col.insert_one(filter_data)

    return jsonify({
        'success': True, 
        'image_path': public_url,
        'url': public_url,
        'code': detected_code or "UNKNOWN"
    })

@app.route('/api/filters', methods=['GET'])
def get_filters():
    user_id = request.args.get('user_id') or request.headers.get('X-User-ID')
    # Show materials from the current user PLUS materials from the Admin (Unified Library)
    if not user_id or user_id in ['undefined', 'null', 'None']:
        query = {"user_id": {"$in": ADMIN_IDS}}
    else:
        query = {"$or": [{"user_id": str(user_id)}, {"user_id": {"$in": ADMIN_IDS}}]}
    rows = list(filters_col.find(query).sort("created_at", -1))
    
    filters = []
    for row in rows:
        image_path = row["image_path"]
        url = image_path if image_path.startswith('http') else f"http://localhost:5000/{image_path}"
        
        filters.append({
            'id': str(row["_id"]),
            'image_path': image_path,
            'url': url,
            'code': row["code"],
            'created_at': row.get("created_at", 0)
        })
    return jsonify(filters)

@app.route('/api/extracted-textures', methods=['GET'])
def get_extracted_textures():
    user_id = request.args.get('user_id') or request.headers.get('X-User-ID')
    # Show materials from the current user PLUS materials from the Admin (Unified Library)
    if not user_id or user_id in ['undefined', 'null', 'None']:
        query = {"user_id": {"$in": ADMIN_IDS}}
    else:
        query = {"$or": [{"user_id": str(user_id)}, {"user_id": {"$in": ADMIN_IDS}}]}
    rows = list(filters_col.find(query).sort("created_at", -1))
    
    textures = []
    for row in rows:
        image_path = row["image_path"]
        url = image_path if image_path.startswith('http') else f"http://localhost:5000/{image_path}"
        
        textures.append({
            'id': str(row["_id"]),
            'name': row["code"],
            'url': url
        })
    return jsonify(textures)

@app.route('/api/products', methods=['GET'])
def get_products():
    user_id = request.args.get('user_id') or request.headers.get('X-User-ID')
    # Show materials from the current user PLUS materials from the Admin (Unified Library)
    if not user_id or user_id in ['undefined', 'null', 'None']:
        query = {"user_id": {"$in": ADMIN_IDS}}
    else:
        query = {"$or": [{"user_id": str(user_id)}, {"user_id": {"$in": ADMIN_IDS}}]}
    rows = list(filters_col.find(query).sort("created_at", -1))
    
    products = []
    for row in rows:
        image_path = row["image_path"]
        url = image_path if image_path.startswith('http') else f"http://localhost:5000/{image_path}"
        
        products.append({
            'id': str(row["_id"]),
            'name': row["code"],
            'image': url,
            'preview': url,
            'type': 'wall',
            'color': '#ffffff',
            'pattern': url
        })
    return jsonify(products)

@app.route('/api/filter', methods=['DELETE'])
def delete_filter():
    id = request.args.get('id')
    user_id = request.args.get('user_id') or request.headers.get('X-User-ID')
    if not id:
        return jsonify({'error': 'Missing ID'}), 400
    
    try:
        # Check ownership or admin status before deletion
        filter_item = filters_col.find_one({"_id": ObjectId(id)})
        
        if not filter_item:
            return jsonify({'error': 'Filter not found'}), 404
            
        if filter_item["user_id"] != str(user_id) and str(user_id) not in ADMIN_IDS:
            return jsonify({'error': 'Permission denied'}), 403
            
        filters_col.delete_one({"_id": ObjectId(id)})
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/detect-codes', methods=['POST'])
def detect_codes():
    start_total = time.time()
    data = request.json
    page_url = data.get('page_url')
    
    if not page_url:
        return jsonify({'error': 'Missing page_url'}), 400
        
    # 1. CHECK CACHE FIRST
    cached = ocr_cache_col.find_one({"page_url": page_url})
    if cached:
        print(f"[OCR CACHE] Hit for {page_url}. Returning instantly.", flush=True)
        return jsonify({'success': True, 'codes': cached['codes'], 'cached': True})

    # 2. DOWNLOAD IMAGE
    image = None
    if page_url.startswith('http') and 'localhost' not in page_url:
        try:
            import requests
            resp = requests.get(page_url)
            if resp.ok:
                image = decode_image(resp.content)
            else:
                return jsonify({'error': f"Failed to download page for OCR: {resp.status_code}"}), 500
        except Exception as e:
            return jsonify({'error': f"Cloud OCR download error: {str(e)}"}), 500
    
    if image is None:
        try:
            rel_path = page_url.split('/uploads/')[-1].replace('/', os.sep)
            img_path = os.path.join(app.config['UPLOAD_FOLDER'], rel_path)
            if os.path.exists(img_path):
                image = cv2.imread(img_path)
        except:
            pass

    if image is None:
        return jsonify({'error': 'Page image not found for code detection.'}), 404
        
    if not models_ready or ocr_reader is None:
        return jsonify({'error': 'OCR engine is still initializing. Please wait 10-15 seconds and try again.', 'retry': True}), 503

    try:
        prep_start = time.time()
        # 3. INTELLIGENT RESIZING & FAST PREPROCESSING
        h, w = image.shape[:2]
        max_dim = 1800 # Reduced from 2000 for faster CPU inference with negligible loss
        
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            image_proc = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        else:
            scale = 1.0
            image_proc = image
            
        gray = cv2.cvtColor(image_proc, cv2.COLOR_BGR2GRAY)
        
        # OPTIMIZED FILTER: Fast Median blur + slight sharpening for OCR
        # This is 4-5x faster than bilateralFilter on CPU
        gray = cv2.medianBlur(gray, 3)
        
        print(f"[OCR PREP] Scale: {scale:.2f}, Time: {time.time() - prep_start:.2f}s", flush=True)

        # 4. SINGLE PASS OPTIMIZED OCR
        ocr_start = time.time()
        all_results = ocr_reader.readtext(gray)
        print(f"[OCR ENGINE] Pass took {time.time() - ocr_start:.2f}s", flush=True)
        
        detected = []
        wk_pattern = re.compile(r'WK[0-9OIlS\-\s]{2,10}', re.IGNORECASE)
        
        for (bbox, text, prob) in all_results:
            if not text: continue
            
            match = wk_pattern.search(text)
            if match:
                code = normalize_code(match.group(0))
                if len(code) < 4: continue
                
                (tl, tr, br, bl) = bbox
                # Map coordinates back to original image size
                left = int(tl[0] / scale)
                top = int(tl[1] / scale)
                width = int((tr[0] - tl[0]) / scale)
                height = int((bl[1] - tl[1]) / scale)
                
                detected.append({
                    'code': code,
                    'left': left,
                    'top': top,
                    'width': width,
                    'height': height,
                    'x': left + width // 2,
                    'y': top + height // 2
                })
        
        # Deduplicate
        final_detected = []
        seen_pos = set()
        for item in detected:
            pos_key = f"{item['left'] // 20}_{item['top'] // 20}"
            if pos_key not in seen_pos:
                final_detected.append(item)
                seen_pos.add(pos_key)
        
        # 5. SAVE TO CACHE
        ocr_cache_col.replace_one(
            {"page_url": page_url},
            {"page_url": page_url, "codes": final_detected, "created_at": time.time()},
            upsert=True
        )
                    
        print(f"[OCR TOTAL] {len(final_detected)} codes found in {time.time() - start_total:.2f}s", flush=True)
        return jsonify({'success': True, 'codes': final_detected, 'cached': False})
        
    except Exception as e:
        print(f"[OCR ERROR] {e}", flush=True)
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ==========================================
# SMART CODE EXTRACTION (PDF + OCR FALLBACK)
# ==========================================

def normalize_code(text):
    """
    Standardizes material codes and corrects common OCR misreads.
    Example: WK16O-O6 -> WK160-06
    """
    if not text: return ""
    # Remove whitespace and standardize dashes
    text = re.sub(r'\s+', '', text)
    text = text.replace("–", "-").replace("—", "-")
    
    # OCR Correction logic (Dynamic, not hardcoded to specific codes)
    if text.upper().startswith("WK"):
        prefix = text[:2].upper()
        rest = text[2:]
        # Correct common digit/letter confusions in the numeric part
        rest = rest.replace('O', '0').replace('o', '0')
        rest = rest.replace('I', '1').replace('l', '1')
        rest = rest.replace('S', '5').replace('s', '5')
        text = prefix + rest
        
    return text.strip().upper()

def extract_code_regex(text):
    """
    Regex patterns that are robust to OCR misreads but strict on format.
    Ensures full codes like WK160-28 are captured, not just WK160.
    """
    # Strict catalog pattern: WK followed by 3 digits, dash, 2-3 digits
    # Allowing O for 0, I for 1 etc. as they are corrected in normalize_code
    patterns = [
        r'WK[0-9OIlS]{3}-[0-9OIlS]{2,3}', # Preferred full match: WK160-28
        r'[A-Z]{1,3}[0-9OIlS]{3,5}-[0-9OIlS]{1,3}', # General fallback
        r'WK[0-9OIlS]{3,5}', # Partial but specific prefix
        r'[0-9OIlS]{5,}' # Numeric only fallback
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return normalize_code(match.group(0))
    return ""

def extract_code_ocr(image, target_point):
    if not ocr_reader: return ""
    
    # Use EasyOCR
    results = ocr_reader.readtext(image)
    
    target_x, target_y = target_point
    best_code = ""
    min_dist = float('inf')
    
    for (bbox, text, prob) in results:
        word_text = text.strip()
        if not word_text or len(word_text) < 3: continue
        
        code = extract_code_regex(word_text)
        if not code: continue
        
        # Calculate center of this word's bounding box
        (tl, tr, br, bl) = bbox
        cx, cy = (tl[0] + br[0]) / 2, (tl[1] + br[1]) / 2
        
        dist = ((cx - target_x)**2 + (cy - target_y)**2)**0.5
        if dist < min_dist:
            min_dist = dist
            best_code = code
            
    return best_code

def extract_code_from_pdf(page, target_center_pdf):
    """
    Robust PDF text extraction using a radial search.
    Searches all text blocks within the PDF vector layer near the selection.
    """
    # Use get_text("words") for precise word-level coordinates
    words = page.get_text("words")
    tx, ty = target_center_pdf
    
    candidates = []
    
    # 1. Collect all potential codes within a reasonable radius (300 points)
    for w in words:
        x0, y0, x1, y1, word_text = w[:5]
        
        # Clean the text (remove noise)
        clean_text = word_text.strip().upper()
        code = extract_code_regex(clean_text)
        
        if code:
            # Calculate center of the word
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            dist = ((cx - tx)**2 + (cy - ty)**2)**0.5
            
            # If it's within 400 points (about 5-6 inches on a standard page)
            if dist < 400:
                candidates.append({'code': code, 'dist': dist})
    
    # 2. Sort by distance and return the closest one
    if not candidates:
        return ""
        
    candidates.sort(key=lambda x: x['dist'])
    return candidates[0]['code']

def _build_cors_preflight_response():

    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add('Access-Control-Allow-Headers', "*")
    response.headers.add('Access-Control-Allow-Methods', "*")
    return response

# ==========================================
# IMAGE PROCESSING ENGINE
# ==========================================

# ==========================================
# PRODUCTION-GRADE MODULAR PIPELINE
# ==========================================

def detect_walls(image):
    """Step 1: Adaptive Scene Segmentation using SegFormer (ADE20K)"""
    try:
        h, w = image.shape[:2]
        
        # Memory Optimization: Resize for model inference if image is very large
        # SegFormer-b0 is optimized for 512x512
        max_dim = 1024
        scale = 1.0
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            image_small = cv2.resize(image, (int(w * scale), int(h * scale)))
        else:
            image_small = image

        inputs = scene_processor(images=image_small, return_tensors="pt").to(scene_model.device)
        with torch.no_grad():
            outputs = scene_model(**inputs)
        
        # REDUCED MEMORY PIPELINE:
        # Instead of upsampling the full 150-channel logits (which causes OOM on CPU),
        # we process the probability maps at model resolution and then upsample 1-channel results.
        logits = outputs.logits # [1, 150, H_m, W_m]
        
        # 1. Extract Wall probabilities (Class 0)
        probs_small = torch.nn.functional.softmax(logits, dim=1)[0]
        wall_prob_small = probs_small[0:1].unsqueeze(0) # [1, 1, H_m, W_m]
        
        # Upsample only the 1-channel wall map to original image size
        wall_conf = nn.functional.interpolate(wall_prob_small, size=(h, w), mode="bilinear", align_corners=False)[0, 0].cpu().numpy()
        
        # 2. Extract structural labels
        labels_small = logits.argmax(dim=1)[0].cpu().numpy()
        # Upsample labels using nearest neighbor to preserve category IDs
        labels = cv2.resize(labels_small.astype(np.float32), (w, h), interpolation=cv2.INTER_NEAREST).astype(np.int32)

        # Adaptive confidence threshold
        conf_thresh = np.percentile(wall_conf, 40) 
        wall_mask = (wall_conf > max(0.5, conf_thresh)).astype(np.uint8)
        
        # Structural protection: floor(3), ceiling(5), windowpane(8), mirror(18)
        # We use the upsampled labels mask
        protection_ids = [3, 4, 5, 8, 11, 14, 18, 28, 31, 32, 33, 34, 35, 36, 42, 43, 47, 51, 158]
        structural_protection = np.isin(labels, protection_ids).astype(np.uint8)
        
        return wall_mask, structural_protection, labels
    except Exception as e:
        print(f"Fallback in detect_walls: {e}")
        return np.ones(image.shape[:2], dtype=np.uint8), np.zeros(image.shape[:2], dtype=np.uint8), None

def detect_objects(image):
    """Step 2: Dynamic Object Protection Layer using YOLOv8 (Optimized for 640px)"""
    try:
        h_orig, w_orig = image.shape[:2]
        object_mask = np.zeros((h_orig, w_orig), dtype=np.uint8)
        
        # DOWN-SCALE FOR REALTIME INFERENCE
        max_yolo_dim = 640
        scale = max_yolo_dim / max(h_orig, w_orig)
        img_small = cv2.resize(image, (int(w_orig * scale), int(h_orig * scale)))
        
        # Run YOLO with dynamic confidence filtering
        results = yolo_model.predict(img_small, conf=0.25, verbose=False)
        for res in results:
            if res.masks is not None:
                for m_data in res.masks.data:
                    m_cpu = m_data.cpu().numpy()
                    m_resized = cv2.resize(m_cpu, (w_orig, h_orig), interpolation=cv2.INTER_NEAREST)
                    object_mask[m_resized > 0] = 1
        return object_mask
    except Exception:
        return np.zeros(image.shape[:2], dtype=np.uint8)

def detect_edges(image):
    """Step 3: Adaptive Edge Detection using median-based statistics"""
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    v = np.median(gray)
    
    # Adaptive sigma for Canny based on global image statistics
    sigma = 0.33
    lower = int(max(0, (1.0 - sigma) * v))
    upper = int(min(255, (1.0 + sigma) * v))
    edges = cv2.Canny(gray, lower, upper)
    
    # Resolution-aware dilation kernel
    diag = np.sqrt(image.shape[0]**2 + image.shape[1]**2)
    k_size = max(3, int(diag / 400))
    if k_size % 2 == 0: k_size += 1
    
    kernel = np.ones((k_size, k_size), np.uint8)
    return cv2.dilate(edges, kernel, iterations=1)

def detect_texture(image):
    """Step 4: Dynamic Texture/Graphic Removal (Stickers, Posters, Frames)"""
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    
    # Calculate local variation using gradient magnitude
    grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    grad_mag = cv2.sqrt(grad_x**2 + grad_y**2)
    
    # Dynamic window size for local variance
    win_size = max(9, int(min(image.shape[:2]) / 80))
    if win_size % 2 == 0: win_size += 1
    
    # Blur the magnitude to get local texture density
    texture_density = cv2.GaussianBlur(grad_mag, (win_size, win_size), 0)
    
    # Adaptive threshold: Only remove regions with variance significantly higher 
    # than the image's median texture
    t_thresh = np.percentile(texture_density, 88)
    return (texture_density > t_thresh).astype(np.uint8)

def detect_glass(image):
    """Step 5: Dynamic Glass/Window Detection (HSV Percentiles)"""
    hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
    s_channel = hsv[:,:,1]
    v_channel = hsv[:,:,2]
    
    # Glass rule: High brightness + Low saturation relative to the room stats
    v_thresh = np.percentile(v_channel, 93) 
    s_thresh = np.percentile(s_channel, 12) 
    
    return ((v_channel > v_thresh) & (s_channel < s_thresh)).astype(np.uint8)

def refine_mask(image, wall_mask, protection_mask, preview_mode=True):
    """Step 6: Fine Segmentation & Boundary Refinement using SAM (Bypassed in Preview)"""
    if preview_mode:
        # FAST PATH: Use lightweight morphology instead of heavy SAM
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        refined = cv2.morphologyEx(wall_mask, cv2.MORPH_OPEN, kernel)
        return refined

    try:
        sam_predictor.set_image(image)
        wall_y, wall_x = np.where(wall_mask > 0)
        if len(wall_x) == 0: return wall_mask
        
        # Adaptive point count based on wall area
        point_count = min(15, max(5, int(len(wall_x) / 50000)))
        sample_indices = np.linspace(0, len(wall_x) - 1, point_count).astype(int)
        points = np.column_stack((wall_x[sample_indices], wall_y[sample_indices]))
        
        final_masks = []
        for pt in points:
            masks, scores, _ = sam_predictor.predict(
                point_coords=np.array([pt]), point_labels=np.array([1]), multimask_output=True
            )
            m = masks[np.argmax(scores)]
            
            # Confidence check: Ignore masks that bleed into protected objects
            overlap = np.sum(np.logical_and(m, protection_mask)) / (np.sum(m) + 1)
            if overlap < 0.15:
                final_masks.append(m)
        
        return np.logical_or.reduce(final_masks).astype(np.uint8) if final_masks else wall_mask
    except Exception:
        return wall_mask

def finalize_mask(mask, image_shape):
    """Step 8 & 9: Dynamic Morphology & Edge Smoothing"""
    mask = mask.astype(np.uint8)
    h, w = image_shape[:2]
    diag = np.sqrt(h**2 + w**2)
    
    # Adaptive kernel for closing small gaps
    k_size = max(3, int(diag / 300))
    if k_size % 2 == 0: k_size += 1
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k_size, k_size))
    
    # Step 8: Morphological Cleanup
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
    
    # Connected component filtering to remove small noise
    num_labels, labels_cc, stats, _ = cv2.connectedComponentsWithStats(mask)
    if num_labels > 1:
        max_area = np.max(stats[1:, cv2.CC_STAT_AREA])
        mask = np.isin(labels_cc, [i for i in range(1, num_labels) if stats[i, cv2.CC_STAT_AREA] > max_area * 0.04]).astype(np.uint8)
    
    # Step 9: Sharp but smooth blending (Small Resolution-aware Gaussian)
    blur_size = max(3, int(diag / 600))
    if blur_size % 2 == 0: blur_size += 1
    alpha = cv2.GaussianBlur(mask.astype(np.float32), (blur_size, blur_size), 0)
    
    # 🔥 Boost mask strength to prevent "patchy" walls
    alpha = np.clip(alpha * 1.2, 0, 1)
    
    return alpha

def tile_texture(texture, target_h, target_w, scale=1.0):
    """
    Dynamic High-Fidelity Tiling.
    Automatically balances pattern density so the texture looks "natural" 
    on walls of different resolutions.
    """
    try:
        th, tw = texture.shape[:2]
        
        # 🚀 DYNAMIC SCALING: Ensure the pattern isn't "too dense"
        # If the user hasn't provided a custom scale, we calculate a "Natural Scale"
        # based on the room height.
        if scale == 1.0:
            # We want one tile to cover roughly 20% of the room height for a natural look
            ideal_height = target_h * 0.20
            natural_scale = ideal_height / th
            
            # Limit the auto-upscale to prevent excessive blurriness (max 2.5x)
            scale = max(1.0, min(natural_scale, 2.5))
            
        # Step 1: Apply the calculated or user-provided scale
        if scale != 1.0:
            texture = cv2.resize(texture, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)
            th, tw = texture.shape[:2]
            
        # Step 2: Repeat pattern to fill the image
        repeat_y = (target_h // th) + 1
        repeat_x = (target_w // tw) + 1
        
        tiled = np.tile(texture, (repeat_y, repeat_x, 1))
        
        # Step 3: Final Crop
        return tiled[:target_h, :target_w]
    except Exception as e:
        print(f"Error in dynamic tiling: {e}")
        return cv2.resize(texture, (target_w, target_h))

def remove_wall_glare(image, mask):
    """
    Step 9: Dynamic Highlight Suppression.
    Detects and removes extreme sunlight or LED glare from the wall.
    """
    try:
        # Convert to LAB for luminance manipulation
        lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        
        # Only analyze the wall area
        wall_mask = (mask > 0.5).astype(np.uint8)
        if np.sum(wall_mask) == 0: return image
        
        wall_l = l[wall_mask > 0]
        
        # Detect glare: Top 5% of brightness in the wall
        glare_thresh = max(230, np.percentile(wall_l, 95))
        glare_mask = (l > glare_thresh) & (wall_mask > 0)
        
        if np.any(glare_mask):
            # Dilate to cover the glow around the glare
            kernel = np.ones((15, 15), np.uint8)
            glare_mask_uint8 = glare_mask.astype(np.uint8) * 255
            glare_mask_dilated = cv2.dilate(glare_mask_uint8, kernel, iterations=2)
            
            # Use Telea Inpainting to fill glare with surrounding wall texture/color
            l_cleaned = cv2.inpaint(l, glare_mask_dilated, 10, cv2.INPAINT_TELEA)
            
            # Smooth transition
            l_final = cv2.addWeighted(l, 0.3, l_cleaned, 0.7, 0)
            
            lab_new = cv2.merge([l_final, a, b])
            return cv2.cvtColor(lab_new, cv2.COLOR_LAB2RGB)
        return image
    except Exception as e:
        print(f"Glare Removal Error: {e}")
        return image

def apply_artistic_filter(image, preview_mode=False):
    """
    Architectural Tone Mapping & Premium Visual Filter.
    Bypassed in preview_mode for speed.
    """
    if preview_mode:
        return image # Skip expensive cinematic processing in preview

    try:
        # 1. Local Contrast Enhancement (CLAHE)
        lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8,8))
        l = clahe.apply(l)
        img = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2RGB)
        
        # 2. Color Balance (Subtle warming for premium feel)
        img = img.astype(np.float32)
        img[:,:,0] *= 1.02 # Red
        img[:,:,2] *= 0.98 # Blue
        
        # 3. Vibrance (Selective saturation)
        hsv = cv2.cvtColor(np.clip(img, 0, 255).astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
        hsv[:,:,1] *= 1.05
        img = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)
        
        # 4. Professional Vignette
        h, w = img.shape[:2]
        kernel_x = cv2.getGaussianKernel(w, int(w/1.2))
        kernel_y = cv2.getGaussianKernel(h, int(h/1.2))
        v_mask = (kernel_y * kernel_x.T)
        v_mask = v_mask / v_mask.max()
        v_mask = np.power(v_mask, 0.08) # Extremely subtle
        
        img_f = img.astype(np.float32)
        for i in range(3):
            img_f[:,:,i] *= v_mask
            
        return np.clip(img_f, 0, 255).astype(np.uint8)
    except Exception:
        return image

def apply_texture(image, mask, texture, scale=1.0, preview_mode=True):
    """
    REALTIME PREVIEW RENDERING PIPELINE
    Optimized for sub-5s material switching.
    """
    try:
        h, w = image.shape[:2]
        
        # --- 1. LIGHTING ESTIMATION (Simplified for Preview) ---
        # Instead of expensive inpainting, we use a simple luminosity map
        lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
        l_recon = lab[:,:,0].astype(np.float32)
        
        if preview_mode:
            # Fast blurring instead of bilateralFilter
            l_recon_smooth = cv2.GaussianBlur(l_recon.astype(np.uint8), (15, 15), 0).astype(np.float32)
            reconstructed_rgb = image.astype(np.float32) # Skip inpainting in preview
        else:
            # High-quality path (for future export)
            idz_mask = ((l_recon > 220) * (mask > 0.5)).astype(np.uint8)
            kernel = np.ones((15, 15), np.uint8)
            idz_mask_expanded = cv2.dilate(idz_mask, kernel, iterations=1)
            reconstructed_rgb = cv2.inpaint(image, idz_mask_expanded, 10, cv2.INPAINT_TELEA).astype(np.float32)
            l_recon_smooth = cv2.bilateralFilter(l_recon.astype(np.uint8), 11, 75, 75).astype(np.float32)

        mean_l_clean = np.mean(l_recon_smooth[mask > 0.5]) if np.any(mask > 0.5) else 128.0
        lighting_map = l_recon_smooth / (mean_l_clean + 1e-6)
        np.clip(lighting_map, 0.5, 1.3, out=lighting_map)
        
        # --- 2. TEXTURE APPLICATION ---
        tiled_tex = tile_texture(texture, h, w, scale=scale).astype(np.float32)
        blended = tiled_tex * np.expand_dims(lighting_map, axis=2)
        
        if not preview_mode:
            # Add detail restoration only in high-quality mode
            l_detail = l_recon - cv2.GaussianBlur(l_recon, (9, 9), 0)
            blended += np.expand_dims(l_detail * 0.1, axis=2)
        
        np.clip(blended, 0, 255, out=blended)
        
        # --- 3. BLENDING ---
        feather = 5 if preview_mode else 11
        alpha_mask = cv2.GaussianBlur(mask, (feather, feather), 0)
        alpha_mask_3d = np.expand_dims(alpha_mask, axis=2)
        
        result = (blended * alpha_mask_3d) + (reconstructed_rgb * (1.0 - alpha_mask_3d))
        
        # Cleanup
        del l_recon, l_recon_smooth, lighting_map, tiled_tex, alpha_mask_3d
        
        return apply_artistic_filter(np.clip(result, 0, 255).astype(np.uint8), preview_mode=preview_mode)
        
    except Exception as e:
        print(f"Rendering Error: {e}")
        return image





def remove_black_strips(texture):
    """
    Detect and remove dark horizontal bands (black strips) often found in PDF catalogs.
    Uses HSV thresholding and inpainting.
    """
    try:
        hsv = cv2.cvtColor(texture, cv2.COLOR_RGB2HSV)
        # Detect dark horizontal bands
        mask = cv2.inRange(hsv, (0, 0, 0), (180, 255, 80))
        
        kernel = np.ones((7, 25), np.uint8)
        mask = cv2.dilate(mask, kernel, iterations=2)
        
        cleaned = cv2.inpaint(texture, mask, 5, cv2.INPAINT_TELEA)
        return cleaned
    except Exception as e:
        print(f"Error in black strip removal: {e}")
        return texture

def remove_text_from_texture(texture):
    """
    Remove text from texture completely using OpenCV Inpainting.
    Detects both dark and light text regions and fills them with surrounding patterns.
    """
    try:
        gray = cv2.cvtColor(texture, cv2.COLOR_RGB2GRAY)

        # Detect dark text regions
        _, thresh1 = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
        # Detect light text regions
        _, thresh2 = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)

        # Combine masks
        text_mask = cv2.bitwise_or(thresh1, thresh2)

        # Morphological operations to highlight text-like areas and close gaps
        kernel = np.ones((5,5), np.uint8)
        text_mask = cv2.dilate(text_mask, kernel, iterations=2)

        # Inpaint to remove text
        cleaned = cv2.inpaint(texture, text_mask, 3, cv2.INPAINT_TELEA)

        return cleaned
    except Exception as e:
        print(f"Error in text removal: {e}")
        return texture

@app.route('/api/upload-room', methods=['POST'])
def upload_room():
    """
    ULTRA-PREMIUM WORKFLOW:
    Upload the room image ONCE. Get a session_id. 
    Never upload the same room file again during the session.
    """
    if not models_ready:
        return jsonify({'error': 'Models loading', 'retry': True}), 503

    try:
        if 'wall_image' not in request.files:
            return jsonify({'error': 'Missing room image'}), 400
            
        start_time = time.time()
        wall_file = request.files['wall_image']
        wall_bytes = wall_file.read()
        image_hash = hashlib.md5(wall_bytes).hexdigest()
        
        # Check session cache
        if image_hash in room_session_cache:
            return jsonify({
                'success': True,
                'session_id': image_hash,
                'message': 'Session resumed from RAM'
            })

        # 1. PROCESS & PREP (768px PREVIEW)
        image = decode_image(wall_bytes)
        if image is None: return jsonify({'error': 'Invalid image'}), 400
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        h_orig, w_orig = image_rgb.shape[:2]
        max_dim = 768
        scale = max_dim / max(h_orig, w_orig)
        new_w, new_h = int(w_orig * scale), int(h_orig * scale)
        image_preview = cv2.resize(image_rgb, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        # 2. AI SEGMENTATION
        wall_mask, structural_protection, labels = detect_walls(image_rgb)
        object_mask = detect_objects(image_rgb)
        protection_layer = np.logical_or(structural_protection > 0, object_mask > 0).astype(np.uint8)
        refined = refine_mask(image_rgb, wall_mask, protection_layer, preview_mode=True)
        mask_soft = finalize_mask(refined, image_rgb.shape)
        mask_preview = cv2.resize(mask_soft, (new_w, new_h))
        
        # 3. LIGHTING PREP
        lab = cv2.cvtColor(image_preview, cv2.COLOR_RGB2LAB).astype(np.float32)
        l_smooth = cv2.GaussianBlur(lab[:,:,0].astype(np.uint8), (13, 13), 0).astype(np.float32)
        mean_l = np.mean(l_smooth[mask_preview > 0.5]) if np.any(mask_preview > 0.5) else 128.0
        lighting_map = l_smooth / (mean_l + 1e-6)
        np.clip(lighting_map, 0.5, 1.3, out=lighting_map)
        
        # 4. STORE SESSION
        # Automatic Cleanup (Prune if cache > 50 sessions)
        if len(room_session_cache) > 50:
            oldest_key = list(room_session_cache.keys())[0]
            del room_session_cache[oldest_key]
            
        room_session_cache[image_hash] = {
            'image_preview': image_preview,
            'mask_preview': mask_preview,
            'lighting_map': lighting_map,
            'timestamp': time.time()
        }
        
        # Sync with legacy wall_cache
        wall_cache[image_hash] = room_session_cache[image_hash]
        
        print(f"🚀 SESSION CREATED: {image_hash} in {time.time() - start_time:.2f}s", flush=True)
        return jsonify({
            'success': True,
            'session_id': image_hash,
            'dimensions': {'w': new_w, 'h': new_h},
            'time': round(time.time() - start_time, 2)
        })
        
    except Exception as e:
        print(f"[SESSION ERROR] {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/warm-up-mask', methods=['POST'])
def warm_up_mask():
    """Proxy to upload-room for backward compatibility"""
    return upload_room()

@app.route('/api/process-wall', methods=['POST'])
def process_wall():
    if not models_ready:
        return jsonify({'error': 'AI Models are still loading. Please wait a few moments.', 'retry': True}), 503
    
    # Get user_id early
    user_id = request.args.get('user_id') or request.headers.get('X-User-ID') or "anonymous"

    try:
        start_total = time.time()
        
        # --- NEW SESSION-BASED LOGIC ---
        session_id = request.form.get('session_id') or request.args.get('session_id')
        
        if session_id and session_id in room_session_cache:
            print(f"[SESSION HIT] Instant retrieval for {session_id}", flush=True)
            cached_data = room_session_cache[session_id]
            image_preview = cached_data['image_preview']
            mask_preview = cached_data['mask_preview']
            lighting_map = cached_data['lighting_map']
            seg_time = 0.0
            tex_start = time.time() # To keep tex_time consistent
        else:
            # FALLBACK: UPLOAD EVERY TIME
            if 'wall_image' not in request.files: 
                return jsonify({'error': 'Missing session_id or wall_image'}), 400
                
            wall_file = request.files['wall_image']
            wall_bytes = wall_file.read()
            image_hash = hashlib.md5(wall_bytes).hexdigest()
            
            # Check if this image was already processed and is in session cache
            cached_data = room_session_cache.get(image_hash) or wall_cache.get(image_hash)
            
            if cached_data and 'image_preview' in cached_data:
                print(f"[CACHE HIT] Resuming session from hash: {image_hash}", flush=True)
                image_preview = cached_data['image_preview']
                mask_preview = cached_data['mask_preview']
                lighting_map = cached_data['lighting_map']
                seg_time = 0.0
            else:
                print(f"[CACHE MISS] Full pipeline for {image_hash}", flush=True)
                seg_start = time.time()
                image_bgr = decode_image(wall_bytes)
                if image_bgr is None: return jsonify({'error': 'Invalid image'}), 400
                image_full = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
                
                max_dim = 768
                h_orig, w_orig = image_full.shape[:2]
                scale = max_dim / max(h_orig, w_orig)
                image_preview = cv2.resize(image_full, (int(w_orig * scale), int(h_orig * scale)))
                
                wall_mask, structural_protection, _ = detect_walls(image_full)
                object_mask = detect_objects(image_full)
                protection_layer = np.logical_or(structural_protection > 0, object_mask > 0).astype(np.uint8)
                refined = refine_mask(image_full, wall_mask, protection_layer, preview_mode=True)
                mask_preview = cv2.resize(finalize_mask(refined, image_full.shape), (image_preview.shape[1], image_preview.shape[0]))
                
                lab = cv2.cvtColor(image_preview, cv2.COLOR_RGB2LAB).astype(np.float32)
                l_smooth = cv2.GaussianBlur(lab[:,:,0].astype(np.uint8), (13, 13), 0).astype(np.float32)
                mean_l = np.mean(l_smooth[mask_preview > 0.5]) if np.any(mask_preview > 0.5) else 128.0
                lighting_map = l_smooth / (mean_l + 1e-6)
                np.clip(lighting_map, 0.5, 1.3, out=lighting_map)
                
                # Store new session
                room_session_cache[image_hash] = {
                    'image_preview': image_preview,
                    'mask_preview': mask_preview,
                    'lighting_map': lighting_map,
                    'timestamp': time.time()
                }
                seg_time = time.time() - seg_start

        # --- SMART TEXTURE RETRIEVAL (WITH RAM CACHE) ---
        texture = None
        texture_hash = hashlib.md5(request.form.get('texture_url', '').encode()).hexdigest() if request.form.get('texture_url') else "upload"
        
        if texture_hash in texture_cache:
            print(f"[TEX CACHE] Hit for {texture_hash}", flush=True)
            texture = texture_cache[texture_hash]
            tex_time = 0.0
        else:
            tex_start = time.time()
            if 'texture_image' in request.files:
                tex_file = request.files['texture_image']
                texture = decode_image(tex_file.read())
            else:
                texture_url = request.form.get('texture_url')
                if not texture_url:
                    return jsonify({'error': 'Missing texture_url'}), 400
                
                # Handle R2 URLs
                if texture_url.startswith('http'):
                    try:
                        import requests
                        resp = requests.get(texture_url)
                        if resp.ok:
                            texture = decode_image(resp.content)
                    except Exception as e:
                        print(f"[TEX ERROR] R2 Download failed: {e}", flush=True)

                # Fallback to local
                if texture is None:
                    try:
                        rel_path = texture_url.split('/uploads/')[-1].replace('/', os.sep)
                        tex_path = os.path.join(app.config['UPLOAD_FOLDER'], rel_path)
                        texture = cv2.imread(tex_path)
                    except: pass

            if texture is not None:
                texture = cv2.cvtColor(texture, cv2.COLOR_BGR2RGB)
                # Store in RAM cache
                texture_cache[texture_hash] = texture
                print(f"[TEX CACHE] Miss. Downloaded and cached {texture_hash}", flush=True)
            
            tex_time = time.time() - tex_start

        if texture is None: 
            return jsonify({'error': 'Texture not found.'}), 400
        
        # Step 10: Apply Texture (Instant Preview Path)
        render_start = time.time()
        # Direct Blend logic (Optimized)
        h, w = image_preview.shape[:2]
        tiled_tex = tile_texture(texture, h, w, scale=1.0).astype(np.float32)
        blended = tiled_tex * np.expand_dims(lighting_map, axis=2)
        np.clip(blended, 0, 255, out=blended)
        
        alpha_mask_3d = np.expand_dims(mask_preview, axis=2)
        result = (blended * alpha_mask_3d) + (image_preview.astype(np.float32) * (1.0 - alpha_mask_3d))
        render_time = time.time() - render_start
        
        # 3. BASE64 WebP ENCODING (ELIMINATES R2 LATENCY)
        encode_start = time.time()
        result_uint8 = np.clip(result, 0, 255).astype(np.uint8)
        result_bgr = cv2.cvtColor(result_uint8, cv2.COLOR_RGB2BGR)
        is_success, buffer = cv2.imencode(".webp", result_bgr, [cv2.IMWRITE_WEBP_QUALITY, 60])
        
        import base64
        base64_img = base64.b64encode(buffer).decode('utf-8')
        data_uri = f"data:image/webp;base64,{base64_img}"
        encode_time = time.time() - encode_start

        total_time = time.time() - start_total
        print(f"🚀 INSTANT RENDER: {total_time:.2f}s | Seg: {seg_time:.2f}s | Tex: {tex_time:.2f}s | Render: {render_time:.2f}s | Encode: {encode_time:.2f}s", flush=True)
        
        return jsonify({
            'resultUrl': data_uri, # Frontend uses resultUrl, returning Base64 string works same as URL
            'timings': {
                'segmentation': round(seg_time, 2),
                'texture': round(tex_time, 2),
                'rendering': round(render_time, 2),
                'encode': round(encode_time, 2),
                'total': round(total_time, 2)
            },
            'cache_hit': cached_data is not None,
            'is_base64': True
        })

    except Exception as e:
        print(f"Server Error: {e}")
        return jsonify({'error': f"Internal Error: {str(e)}"}), 500

@app.route('/api/get-code-from-pdf', methods=['POST'])
def get_code_from_pdf():
    data = request.json
    page_url = data.get('page_url')
    x = data.get('x'); y = data.get('y')
    width = data.get('width'); height = data.get('height')
    scale_x = data.get('scale_x', 1.0); scale_y = data.get('scale_y', 1.0)
    
    if not all([page_url, x is not None, y is not None]):
        return jsonify({'error': 'Missing data'}), 400

    # Handle R2 Image Retrieval
    image = None
    if page_url.startswith('http'):
        try:
            import requests
            resp = requests.get(page_url)
            if resp.ok:
                image = decode_image(resp.content)
        except Exception as e:
            print(f"Cloud fetch error: {e}")

    if image is None:
        return jsonify({'error': 'Page image not found for code extraction.'}), 404

    # Extract info from URL to find the PDF in R2
    try:
        parts = page_url.split('/')
        # Expected: .../{user_id}/pdfs/{pdf_id}/pages/page_{index}.png
        pdf_id = parts[-3]
        user_id = parts[-5]
        page_index = int(parts[-1].split('_')[1].split('.')[0])
        
        # Download PDF from R2
        r2_pdf_path = f"{user_id}/pdfs/{pdf_id}/catalog.pdf"
        # We need to find the actual PDF name. Usually catalog.pdf or we can check DB
        pdf_item = pdfs_col.find_one({"_id": ObjectId(pdf_id)})
        if pdf_item:
            r2_pdf_path = pdf_item.get("r2_path")
        
        # Download PDF to memory
        import io
        pdf_stream = io.BytesIO()
        r2_client.download_fileobj(R2_BUCKET_NAME, r2_pdf_path, pdf_stream)
        pdf_stream.seek(0)
        
        doc = fitz.open(stream=pdf_stream, filetype="pdf")
        page = doc.load_page(page_index)
        
        # Map crop center to PDF coordinates
        pdf_rect = page.rect
        img_h, img_w = image.shape[:2]
        scale_pdf_x = pdf_rect.width / img_w
        scale_pdf_y = pdf_rect.height / img_h
        
        real_center_x = (x + width/2) * scale_x
        real_center_y = (y + height/2) * scale_y
        center_pdf = (real_center_x * scale_pdf_x, real_center_y * scale_pdf_y)
        
        code = extract_code_from_pdf(page, center_pdf)
        doc.close()
        
        if not code:
            # OCR FALLBACK using EasyOCR
            search_y1 = max(0, int(real_center_y - 150))
            search_y2 = min(int(real_center_y + 350), img_h)
            search_x1 = max(0, int(real_center_x - 150))
            search_x2 = min(int(real_center_x + 150), img_w)
            
            roi = image[search_y1:search_y2, search_x1:search_x2]
            if roi.size > 0:
                results = ocr_reader.readtext(roi)
                wk_pattern = re.compile(r'WK\d+\s*[-–—]?\s*\d+', re.IGNORECASE)
                for (bbox, text, prob) in results:
                    match = wk_pattern.search(text)
                    if match:
                        code = match.group(0).replace(" ", "").upper()
                        break

        if not code:
            return jsonify({'success': False, 'message': 'No code found near selection'})

        return jsonify({'success': True, 'code': code})
        
    except Exception as e:
        print(f"Get code error: {e}")
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
# ==========================================
# AUTHENTICATION ROUTES
# ==========================================
@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.json
    name = data.get('name')
    mobile = data.get('mobile')
    email = data.get('email')
    password = data.get('password')

    if not all([name, mobile, email, password]):
        return jsonify({'success': False, 'message': 'All fields are required'}), 400

    hashed_pw = generate_password_hash(password)

    try:
        user_data = {
            "name": name,
            "mobile": mobile,
            "email": email,
            "password": hashed_pw,
            "created_at": time.time()
        }
        result = users_col.insert_one(user_data)
        new_user_id = str(result.inserted_id)
        
        return jsonify({
            'success': True, 
            'message': 'Registration successful',
            'user': {
                'id': new_user_id,
                'name': name,
                'email': email
            }
        })
    except Exception as e:
        if "duplicate key error" in str(e).lower():
            return jsonify({'success': False, 'message': 'Mobile number or Email already exists'}), 409
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    # Handle both 'identifier' (Admin) and 'email' (Legacy User) keys
    identifier = (data.get('identifier') or data.get('email', '')).strip()
    password = (data.get('password', '')).strip()

    if not identifier or not password:
        print(f"[WARNING] [LOGIN DEBUG] Missing credentials in request: {data}")
        return jsonify({'success': False, 'message': 'Missing credentials'}), 400

    print(f"[LOGIN DEBUG] Attempt for identifier: {identifier}")
    # Search by email or mobile to support all login types
    user = users_col.find_one({
        "$or": [
            {"email": identifier},
            {"mobile": identifier}
        ]
    })

    if not user:
        print(f"[ERROR] [LOGIN DEBUG] User NOT FOUND in database for: {identifier}")
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

    if check_password_hash(user["password"], password):
        print(f"[OK] [LOGIN DEBUG] Password MATCHED for: {identifier}")
        return jsonify({
            'success': True,
            'user': {
                'id': str(user["_id"]),
                'name': user["name"],
                'email': user["email"]
            }
        })
    
    print(f"[ERROR] [LOGIN DEBUG] Password MISMATCH for: {identifier}")
    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

if __name__ == '__main__':
    print("\n[DEBUG] Starting Flask App...", flush=True)
    import threading
    
    # Load models in a background thread to prevent blocking startup
    model_thread = threading.Thread(target=load_models, daemon=True)
    model_thread.start()
    
    from waitress import serve
    port = int(os.getenv("PORT", 5000))
    print(f"\n[SYSTEM] Visualizer Backend is starting...")
    print(f"[DEBUG] R2_BUCKET: {R2_BUCKET_NAME}")
    print(f"[DEBUG] R2_ENDPOINT: https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com")
    
    if not all([R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ACCOUNT_ID]):
        print("[CRITICAL] R2 CONFIGURATION ERROR DETECTED. Background processing will fail.")
    else:
        print("[INFO] R2 Infrastructure validated.")
    
    print(f"[DEBUG] Starting Production Server on http://0.0.0.0:{port}\n", flush=True)
    try:
        serve(app, host='0.0.0.0', port=port, threads=6)
    except Exception as e:
        print(f"\n[CRITICAL] Server failed to start: {e}", flush=True)
    
    print("\n[STOP] [SHUTDOWN] Main thread has exited.", flush=True)
