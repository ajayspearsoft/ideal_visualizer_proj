import os
import time
import cv2
import numpy as np
import torch
import torch.nn as nn
from PIL import Image
try:
    import fitz
except ImportError:
    fitz = None

import concurrent.futures
from functools import wraps
import hashlib
import json
import requests

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
from openai import OpenAI
from core.segmentation import SegmentationEngine
from core.geometry import GeometryEngine
from core.generation import GenerationEngine
from core.depth import DepthEngine

try:
    from docx import Document
except ImportError:
    Document = None

# Initialize OpenAI client
openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key) if openai_api_key else None

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

# Leonardo.ai Configuration
LEONARDO_API_KEY = os.getenv("LEONARDO_API_KEY")
LEONARDO_API_URL = "https://cloud.leonardo.ai/api/rest/v1"
LEONARDO_MODEL_ID = "1e60896f-3c26-4296-8ecc-53e2afecc132" # Leonardo Diffusion XL (Excellent for Inpainting)

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
    try:
        import easyocr
        import torch
        ocr_reader = easyocr.Reader(['en'], gpu=torch.cuda.is_available())
        print("[DEBUG] EasyOCR Ready", flush=True)
    except ImportError:
        print("[WARNING] EasyOCR not installed. OCR features will be disabled.", flush=True)
        ocr_reader = None
    except Exception as e:
        print(f"[WARNING] EasyOCR failed to initialize: {e}", flush=True)
        ocr_reader = None

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
depth_model = None
depth_transform = None
rembg_session = None
models_ready = False
model_loading_error = None

# Production Engines
segmentation_engine = None
geometry_engine = None
generation_engine = None
depth_engine = None


# Cache for performance
wall_cache = {}
texture_cache = {}
room_session_cache = {} # Production-grade session management
sam_embeddings_cache = {} # Cache for SAM features
executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

def time_it(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"[PERF] {func.__name__} took {(end - start) * 1000:.2f}ms", flush=True)
        return result
    return wrapper

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

        # 4. MiDaS (Depth Estimation)
        print("[DEBUG] Loading MiDaS (Small)...", flush=True)
        try:
            depth_model_type = "MiDaS_small"
            depth_model = torch.hub.load("intel-isl/MiDaS", depth_model_type, trust_repo=True)
            depth_model.to(device)
            depth_model.eval()
            
            midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms", trust_repo=True)
            depth_transform = midas_transforms.small_transform if depth_model_type == "MiDaS_small" else midas_transforms.dpt_transform
            print("[DEBUG] MiDaS Loaded Successfully", flush=True)
        except Exception as depth_err:
            print(f"[WARNING] MiDaS loading failed, continuing without depth: {depth_err}", flush=True)

        # 5. OCR
        init_ocr()

        # 5.5 Rembg (Foreground Object Protection)
        print("[DEBUG] Loading Rembg session...", flush=True)
        try:
            from rembg import new_session
            global rembg_session
            rembg_session = new_session("u2net")
            print("[DEBUG] Rembg Loaded Successfully", flush=True)
        except Exception as e:
            print(f"[WARNING] Rembg loading failed: {e}", flush=True)

        global segmentation_engine, geometry_engine, generation_engine, depth_engine
        segmentation_engine = SegmentationEngine(
            yolov11_model=yolo_model,
            scene_model=scene_model,
            scene_processor=scene_processor
        )
        geometry_engine = GeometryEngine(model_path="models/mlsd_tiny_512_fp32.onnx")
        depth_engine = DepthEngine(model=depth_model, transform=depth_transform)
        generation_engine = GenerationEngine(api_key=LEONARDO_API_KEY, model_id=LEONARDO_MODEL_ID)
        print("[DEBUG] Production Engines Initialized", flush=True)

        # 6. GLOBAL CPU OPTIMIZATION
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

        # 3. Last Resort: Find the best matching code from the UI's pre-detected list
        if not detected_code and detected_codes_from_ui:
            # Layout-Aware Matching Logic
            # target_x/y is the center-bottom of the crop
            target_x = real_x + real_w // 2
            target_y = real_y + real_h
            
            scored_candidates = []
            for d in detected_codes_from_ui:
                # d: {code, x, y, width, height}
                cx = d.get('x', d.get('left', 0) + d.get('width', 0)//2)
                cy = d.get('y', d.get('top', 0) + d.get('height', 0)//2)
                cw = d.get('width', 40)
                ch = d.get('height', 20)
                
                # 1. Calculate weighted distance (Layout-Aware)
                dx = abs(cx - target_x)
                dy = cy - target_y # Distance below the crop
                
                # Base score is Euclidean
                score = (dx**2 + dy**2)**0.5
                
                # FACTOR A: Vertical Bias (Catalog Codes are usually BELOW the texture)
                if dy > 0 and dy < 350:
                    score *= 0.7  # Strong bonus for being below
                elif dy < -20:
                    score *= 3.0  # Strong penalty for being above the texture
                
                # FACTOR B: Horizontal Alignment (Column Awareness)
                # If the code's horizontal center is within the texture's width
                if dx < (real_w * 0.6):
                    score *= 0.8  # Bonus for being in the same visual column
                else:
                    score *= 2.5  # Heavy penalty for being in a different column
                
                # FACTOR C: Overlap/Containment
                # If code center is actually inside the crop horizontally
                if real_x <= cx <= (real_x + real_w):
                    score *= 0.9
                
                scored_candidates.append({'code': d['code'], 'score': score, 'dist': (dx**2 + dy**2)**0.5})

            if scored_candidates:
                # Sort by score (lowest is best)
                scored_candidates.sort(key=lambda x: x['score'])
                best = scored_candidates[0]
                
                # Only associate if it's reasonably close (800px max in any layout)
                if best['dist'] < 800:
                    detected_code = best['code']
                    print(f"[OK] Associated with Layout-Aware match: {detected_code} (score: {best['score']:.1f}, dist: {best['dist']:.1f})")

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
    Improved to handle catalog-specific artifacts (e.g. WK--100, symbols).
    """
    if not text: return ""
    
    # 1. Basic Cleanup
    text = text.upper().strip()
    text = re.sub(r'\s+', '', text) # Remove internal spaces
    
    # 2. Standardize Dashes (Handle different Unicode dashes)
    text = text.replace("–", "-").replace("—", "-").replace("·", "-").replace("..", "-")
    
    # 3. Suppress OCR Artifacts (Common noise characters)
    text = re.sub(r'[^A-Z0-9-]', '', text)
    
    # 4. Correct Double-Dashes and leading/trailing noise
    text = re.sub(r'-+', '-', text)
    text = text.strip('-')
    
    # 5. Semantic Correction for "WK" prefixed codes
    if text.startswith("WK"):
        prefix = "WK"
        rest = text[2:]
        # Common OCR confusions in digits
        rest = rest.replace('O', '0').replace('I', '1').replace('L', '1').replace('S', '5').replace('B', '8')
        
        # Ensure dash structure (WK16028 -> WK160-28)
        if '-' not in rest and len(rest) >= 5:
            # Infer split point for standard 3+2 or 3+3 digit codes
            text = f"WK{rest[:3]}-{rest[3:]}"
        else:
            text = prefix + rest
            
    return text

def extract_code_regex(text):
    """
    Improved multi-pattern regex for catalog code discovery.
    """
    patterns = [
        r'WK[0-9OIlS]{2,4}-[0-9OIlS]{2,4}', # Standard: WK160-28
        r'WK[0-9OIlS]{3,7}',                # No-dash: WK16028
        r'[A-Z]{1,3}-[0-9OIlS]{3,6}',       # Generic: AR-110
        r'[0-9OIlS]{3,4}-[0-9OIlS]{2,4}'    # Numeric only: 110-01
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
    min_score = float('inf')
    
    for (bbox, text, prob) in results:
        word_text = text.strip()
        if not word_text or len(word_text) < 3: continue
        
        code = extract_code_regex(word_text)
        if not code: continue
        
        # Calculate center of this word's bounding box
        (tl, tr, br, bl) = bbox
        cx, cy = (tl[0] + br[0]) / 2, (tl[1] + br[1]) / 2
        
        # Multi-Factor Scoring for Local Search
        dx = abs(cx - target_x)
        dy = cy - target_y
        
        # Base distance
        score = (dx**2 + dy**2)**0.5
        
        # Bonus for vertical alignment (code centered under texture)
        if dx < 30: score *= 0.5
        # Penalty for being above the target point
        if dy < -10: score *= 2.0
        
        if score < min_score:
            min_score = score
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

def fast_guided_filter(guide, src, radius, eps):
    """
    Production-Grade Guided Filter - v2.
    """
    # Performance Check: Ensure guide is grayscale
    if len(guide.shape) == 3:
        guide = cv2.cvtColor(guide, cv2.COLOR_RGB2GRAY)
    # 1. Normalize and reinforce guidance with Scharr gradients (more accurate than Sobel)
    guide_f = guide.astype(np.float32) / 255.0
    src_f = src.astype(np.float32)

    # Scharr is more rotationally symmetric than Sobel - better at diagonals
    dx = cv2.Scharr(guide_f, cv2.CV_32F, 1, 0)
    dy = cv2.Scharr(guide_f, cv2.CV_32F, 0, 1)
    grad_mag = cv2.magnitude(dx, dy)
    # Normalize gradient to [0,1] before blending
    grad_max = np.percentile(grad_mag, 99) + 1e-6
    grad_norm = np.clip(grad_mag / grad_max, 0, 1)
    edge_enhanced_guide = cv2.addWeighted(grad_norm, 0.18, guide_f, 0.82, 0)

    # 2. Box filter window - ensure odd and at least 3
    r = max(3, int(radius))
    if r % 2 == 0: r += 1
    win_size = (r, r)

    # 3. Local statistics
    mean_I  = cv2.blur(edge_enhanced_guide, win_size)
    mean_p  = cv2.blur(src_f, win_size)
    mean_Ip = cv2.blur(edge_enhanced_guide * src_f, win_size)
    cov_Ip  = mean_Ip - mean_I * mean_p

    mean_II = cv2.blur(edge_enhanced_guide * edge_enhanced_guide, win_size)
    var_I   = mean_II - mean_I * mean_I

    # 4. Coefficient calculation - tighter EPS for crisper edge locking
    a = cov_Ip / (var_I + eps + 1e-7)
    b = mean_p - a * mean_I

    # 5. Coefficient smoothing - use r (not 2r) to preserve fine edge detail
    smooth_win = (r, r)
    mean_a = cv2.blur(a, smooth_win)
    mean_b = cv2.blur(b, smooth_win)

    result = mean_a * edge_enhanced_guide + mean_b
    return np.clip(result, 0.0, 1.0).astype(np.float32)

def recover_wall_regions(wall_mask, object_mask, image, depth_map=None):
    """
    Recover sunlight/shadow wall regions and bridge gaps behind foreground objects
    while still protecting real objects. Uses structural continuity logic.
    Constraint: Architecture Barrier Map prevents spilling into openings/hallways.
    """
    h, w = wall_mask.shape
    recovered = wall_mask.copy().astype(np.uint8)

    # 1. BUILD ARCHITECTURAL BARRIER MAP
    barrier_map = build_architecture_barrier_map(image, depth_map)
    if barrier_map.shape[:2] != (h, w):
        barrier_map = cv2.resize(barrier_map, (w, h), interpolation=cv2.INTER_NEAREST)

    # 2. Structural Gap Bridging (Closing gaps behind objects)
    k_w = max(15, int(w / 40))
    k_h = max(15, int(h / 40))
    
    kernel_h = np.ones((1, k_w), np.uint8)
    kernel_v = np.ones((k_h, 1), np.uint8)
    
    # Bridge horizontal gaps
    candidate = cv2.morphologyEx(recovered, cv2.MORPH_CLOSE, kernel_h, iterations=2)
    candidate[barrier_map > 0] = 0
    recovered = np.maximum(recovered, candidate)

    # Bridge vertical gaps
    candidate = cv2.morphologyEx(recovered, cv2.MORPH_CLOSE, kernel_v, iterations=2)
    candidate[barrier_map > 0] = 0
    recovered = np.maximum(recovered, candidate)

    # 3. Aggressive multi-scale closing for large shadow/glare recovery
    for k_size in [25, 45]:
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k_size, k_size))
        candidate = cv2.morphologyEx(recovered, cv2.MORPH_CLOSE, kernel, iterations=1)
        candidate[barrier_map > 0] = 0
        recovered = np.maximum(recovered, candidate)

    # 4. Connectivity Propagation
    mask_dilated = cv2.dilate(recovered, np.ones((15, 15), np.uint8), iterations=2)
    mask_eroded = cv2.erode(mask_dilated, np.ones((15, 15), np.uint8), iterations=2)
    candidate = cv2.bitwise_or(recovered, mask_eroded)
    candidate[barrier_map > 0] = 0
    recovered = np.maximum(recovered, candidate)

    # 5. Final smoothing and re-protection
    recovered = cv2.GaussianBlur(recovered.astype(np.float32), (15, 15), 0)
    recovered = np.clip(recovered, 0, 1)

    return recovered.astype(np.float32)

@time_it
def detect_walls(image):
    """Step 1: Adaptive Scene Segmentation using SegFormer (ADE20K)"""
    try:
        h, w = image.shape[:2]
        
        # Avoid redundant resizing if image is already AI-ready (<= 1024px)
        if max(h, w) > 1024:
            scale_ai = 1024 / max(h, w)
            image_small = cv2.resize(image, (int(w * scale_ai), int(h * scale_ai)))
            h, w = image_small.shape[:2]
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
        
        # --- NEW: SHADOW-AWARE WALL DETECTION ---
        lab = cv2.cvtColor(image_small, cv2.COLOR_RGB2LAB)
        L = lab[:,:,0].astype(np.float32)
        shadow_boost = cv2.GaussianBlur(L, (31, 31), 0)
        # Identify dark regions that might be shadowed walls
        shadow_boost_mask = (shadow_boost < np.percentile(shadow_boost, 45)).astype(np.uint8)
        
        # 2. Extract structural labels
        labels_small = logits.argmax(dim=1)[0].cpu().numpy()
        # Upsample labels using nearest neighbor to preserve category IDs
        labels = cv2.resize(labels_small.astype(np.float32), (w, h), interpolation=cv2.INTER_NEAREST).astype(np.int32)

        # Adaptive confidence threshold with vertical bias
        # Walls typically have higher confidence in the middle vertical band
        conf_mean = np.mean(wall_conf)
        conf_thresh = np.percentile(wall_conf, 35) 
        base_mask = (wall_conf > max(0.4, conf_thresh)).astype(np.uint8)
        
        # Apply Shadow Boost: Dark regions that align with wall probabilities get a boost
        base_mask = np.maximum(base_mask, (shadow_boost_mask * wall_conf > 0.35).astype(np.uint8))
        
        # Structural protection: floor(3), ceiling(5), windowpane(8), mirror(18)
        # Expanded IDs: bed(7), cabinet(10), curtain(11), door(14), furniture(21), shelf(28), rug(31), wardrobe(43), mirror(18), windowpane(8)
        protection_ids = [3, 4, 5, 7, 8, 10, 11, 14, 18, 21, 28, 31, 32, 33, 34, 35, 36, 38, 42, 43, 47, 51, 63, 158]
        structural_protection = np.isin(labels, protection_ids).astype(np.uint8)
        
        # Refine wall mask by removing high-confidence structural elements
        wall_mask = np.logical_and(
            base_mask,
            np.logical_not(structural_protection)
        ).astype(np.uint8)

        # --- NEW: PLANE-AWARE GLOBAL CONTINUITY ---
        # 1. Segment initial mask into disconnected components
        num_labels, labels_im, stats, centroids = cv2.connectedComponentsWithStats(wall_mask)
        
        if num_labels > 2: # Background + 2 or more regions
            # Estimate global plane similarity
            # We want to merge regions that are likely part of the same architectural wall
            # but separated by a TV or decoration
            depth_map_small = None
            try:
                # Use a small depth map for similarity checking
                # We can't use full depth yet as it might not be computed, but we can compute a fast version
                # or use the wall_conf as a proxy for surface stability
                pass
            except: pass

            # 2. Connectivity Graph Logic: Merge nearby large regions
            for i in range(1, num_labels):
                if stats[i, cv2.CC_STAT_AREA] < (h * w * 0.005): continue # Ignore tiny noise
                
                for j in range(i + 1, num_labels):
                    if stats[j, cv2.CC_STAT_AREA] < (h * w * 0.005): continue
                    
                    # Distance between centroids
                    dist = np.sqrt((centroids[i][0] - centroids[j][0])**2 + (centroids[i][1] - centroids[j][1])**2)
                    
                    # If regions are reasonably close (within 25% of image width)
                    # they are candidates for propagation
                    if dist < (w * 0.35):
                        # Use morphological bridging between these specific components
                        pair_mask = np.isin(labels_im, [i, j]).astype(np.uint8)
                        # Bridge the gap
                        kernel_bridge = np.ones((max(11, int(dist/5)), max(11, int(dist/5))), np.uint8)
                        bridged = cv2.morphologyEx(pair_mask, cv2.MORPH_CLOSE, kernel_bridge)
                        # Only add the bridge where it doesn't hit a structural protection element
                        new_connections = np.logical_and(bridged, np.logical_not(structural_protection))
                        wall_mask = np.logical_or(wall_mask, new_connections).astype(np.uint8)

        # 3. Apply semantic recovery
        wall_mask = recover_wall_regions(
            wall_mask,
            structural_protection,
            image_small
        )
        
        return wall_mask.astype(np.uint8), structural_protection, labels
    except Exception as e:
        print(f"Fallback in detect_walls: {e}")
        return np.ones(image.shape[:2], dtype=np.uint8), np.zeros(image.shape[:2], dtype=np.uint8), None

@time_it
def detect_objects(image, use_fast_mode=False):
    """Step 2: Dynamic Object Protection using YOLOv8"""
    global _last_tiered_protection
    try:
        h_orig, w_orig = image.shape[:2]
        max_yolo_dim = 640 if not use_fast_mode else 320
        scale = max_yolo_dim / max(h_orig, w_orig)
        h_orig, w_orig = image.shape[:2]
        object_mask = np.zeros((h_orig, w_orig), dtype=np.uint8)

        # Tiered protection masks (CRITICAL / MEDIUM / SOFT)
        critical_mask = np.zeros((h_orig, w_orig), dtype=np.uint8)  # windows, mirrors, doors, trims
        medium_mask   = np.zeros((h_orig, w_orig), dtype=np.uint8)  # sofas, beds, cabinets
        soft_mask     = np.zeros((h_orig, w_orig), dtype=np.uint8)  # plants, decor, cushions

        # YOLO class -> tier mapping (COCO classes)
        # CRITICAL: 0=person, 62=tv/monitor, 56=chair->skip, use for glass-like objects
        # Pragmatic split based on common interior COCO classes:
        CRITICAL_CLASSES = {62, 63, 67, 72, 73, 74, 75, 76}  # tv, laptop, clock, book, vase, scissors, toaster, sink
        MEDIUM_CLASSES   = {56, 57, 58, 59, 60, 61}           # chair, sofa, potted plant, bed, dining table, toilet
        # Everything else detected -> SOFT tier

        h, w = image.shape[:2]
        # Avoid redundant resizing if image is already AI-ready (<= 640px for YOLO)
        if max(h, w) > 640:
            scale = 640 / max(h, w)
            img_small = cv2.resize(image, (int(w * scale), int(h * scale)))
        else:
            img_small = image

        results = yolo_model.predict(img_small, conf=0.15, verbose=False)
        for res in results:
            if res.masks is None: continue
            for idx, m_data in enumerate(res.masks.data):
                m_cpu = m_data.cpu().numpy()
                m_resized = cv2.resize(m_cpu, (w, h), interpolation=cv2.INTER_LINEAR)
                binary = (m_resized > 0.5).astype(np.uint8)

                # Determine tier from class id
                cls_id = int(res.boxes.cls[idx].item()) if res.boxes is not None and idx < len(res.boxes.cls) else -1
                area = np.sum(binary)

                if cls_id in CRITICAL_CLASSES:
                    k_val = max(7, min(13, int(np.sqrt(area) / 40)))  # Robust shielding for hard objects
                    tier = 'critical'
                elif cls_id in MEDIUM_CLASSES:
                    k_val = max(5, min(9, int(np.sqrt(area) / 55)))
                    tier = 'medium'
                else:
                    k_val = max(3, min(7, int(np.sqrt(area) / 70)))   # Thin margin for soft decor
                    tier = 'soft'

                if k_val % 2 == 0: k_val += 1
                kernel = np.ones((k_val, k_val), np.uint8)
                dilated = cv2.dilate(binary, kernel, iterations=1)

                object_mask[dilated > 0] = 1
                if tier == 'critical':   critical_mask[dilated > 0] = 1
                elif tier == 'medium':   medium_mask[dilated > 0]   = 1
                else:                    soft_mask[dilated > 0]     = 1

        # Store tiered masks for use in finalize_mask
        _last_tiered_protection = {
            'critical': critical_mask,
            'medium':   medium_mask,
            'soft':     soft_mask
        }
        return object_mask
    except Exception:
        _last_tiered_protection = None
        return np.zeros(image.shape[:2], dtype=np.uint8)

# Module-level storage for tiered protection (avoids API changes)
_last_tiered_protection = None


@time_it
def extract_foreground_alpha(image_small):
    """
    Foreground Object Protection using rembg alpha matting
    Provides fine edge preservation for leaves/thin objects.
    """
    global rembg_session
    try:
        from rembg import remove
        from PIL import Image
        import numpy as np
        import cv2

        pil_image = Image.fromarray(image_small)
        # 1. Object Protection using rembg alpha matting
        rgba = remove(
            pil_image,
            session=rembg_session,
            alpha_matting=True,
            alpha_matting_foreground_threshold=240,
            alpha_matting_background_threshold=10,
            alpha_matting_erode_size=3
        )
        rgba = np.array(rgba)
        # Ensure rembg didn't alter the dimensions
        if rgba.shape[:2] != image_small.shape[:2]:
            rgba = cv2.resize(rgba, (image_small.shape[1], image_small.shape[0]), interpolation=cv2.INTER_LANCZOS4)
            
        foreground_alpha = rgba[:, :, 3].astype(np.float32) / 255.0

        # 2. Fine edge preservation for leaves/thin objects
        foreground_alpha = cv2.GaussianBlur(foreground_alpha, (3, 3), 0)
        edge = cv2.Canny((foreground_alpha * 255).astype(np.uint8), 40, 120)
        edge = edge.astype(np.float32) / 255.0

        foreground_alpha = np.maximum(foreground_alpha, edge * 0.35)
        foreground_alpha = np.clip(foreground_alpha * 1.15, 0, 1)

        return foreground_alpha
    except Exception as e:
        print(f"[REMBG ERROR] {e}")
        return None

def build_soft_occlusion_map(image, object_mask, foreground_alpha):
    """
    Step 7.5: PROFESSIONAL SOFT OCCLUSION MAP
    Instead of hard-cutting, we create a tiered transparency map that preserves 
    shadows and plant edges while suppressing texture spill.
    """
    h, w = object_mask.shape
    soft_map = np.zeros((h, w), dtype=np.float32)

    # 1. Foreground alpha from rembg (Highest authority)
    if foreground_alpha is not None:
        if foreground_alpha.shape[:2] != (h, w):
            foreground_alpha = cv2.resize(foreground_alpha, (w, h), interpolation=cv2.INTER_LINEAR)
        alpha = foreground_alpha.astype(np.float32)
        alpha = cv2.GaussianBlur(alpha, (9, 9), 0)
        soft_map = np.maximum(soft_map, alpha * 0.85)

    # 2. YOLO object confidence smoothing
    obj = object_mask.astype(np.float32)
    obj_dist = cv2.distanceTransform((obj > 0).astype(np.uint8), cv2.DIST_L2, 5)
    obj_dist = obj_dist / (obj_dist.max() + 1e-6)
    obj_dist = np.clip(obj_dist * 1.2, 0, 1)
    soft_map = np.maximum(soft_map, obj_dist * 0.55)

    # 3. Edge softness refinement
    soft_map = cv2.GaussianBlur(soft_map, (11, 11), 0)
    return np.clip(soft_map, 0, 1)


@time_it
def build_master_edge_field(image, depth_map=None, use_fast_mode=False):
    """
    Step 3: Multi-Edge Authority Field - Architectural Locking.
    """
    h, w = image.shape[:2]
    diag = np.sqrt(h**2 + w**2)

    # Performance: Fast mode skips expensive Hough and LSD
    if use_fast_mode:
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        canny = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 50, 150).astype(np.float32) / 255.0
        return canny
    h, w = image.shape[:2]
    diag = np.sqrt(h**2 + w**2)

    # === PREPROCESSING: Bilateral filter - suppress texture noise, preserve structure ===
    # d=5 is lightweight; keeps CPU impact minimal
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    gray_smooth = cv2.bilateralFilter(gray, 5, 35, 35)

    # === 1. SCHARR GRADIENT - more rotationally symmetric than Sobel ===
    sx = cv2.Scharr(gray_smooth, cv2.CV_32F, 1, 0)
    sy = cv2.Scharr(gray_smooth, cv2.CV_32F, 0, 1)
    scharr_mag = cv2.magnitude(sx, sy)
    scharr_norm = np.clip(scharr_mag / (np.percentile(scharr_mag, 99) + 1e-6), 0, 1).astype(np.float32)

    # === 2. MULTI-SCALE CANNY FUSION ===
    v = np.median(gray_smooth)
    lower = int(max(0, 0.5 * v))
    upper = int(min(255, 1.5 * v))

    # Scale 1: Full resolution - fine architectural trims and thin edges
    canny_full = cv2.Canny(gray_smooth, lower, upper).astype(np.float32) / 255.0

    # Scale 2: Half resolution - large structural wall/ceiling/floor boundaries
    gray_half = cv2.resize(gray_smooth, (max(1, w // 2), max(1, h // 2)))
    canny_half = cv2.resize(
        cv2.Canny(gray_half, lower, upper), (w, h)
    ).astype(np.float32) / 255.0

    # Fuse: full gets more weight (fine detail), half reinforces large boundaries
    canny_fused = np.clip(canny_full * 0.65 + canny_half * 0.35, 0, 1).astype(np.float32)

    # === 3. HOUGH - length-weighted long structural lines ===
    canny_u8 = (canny_full * 255).astype(np.uint8)
    lines = cv2.HoughLinesP(canny_u8, 1, np.pi / 180, threshold=60,
                            minLineLength=int(diag * 0.06), maxLineGap=8)
    hough_mask = np.zeros((h, w), dtype=np.float32)
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            seg_len = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            # Longer lines -> higher authority (normalized to diagonal)
            weight = float(np.clip(seg_len / (diag * 0.12), 0.3, 1.0))
            cv2.line(hough_mask, (x1, y1), (x2, y2), weight, 2)
    hough_mask = np.clip(hough_mask, 0, 1)

    # === 4. LSD - length-weighted sub-pixel segment detection ===
    lsd_mask = np.zeros((h, w), dtype=np.float32)
    try:
        lsd = cv2.createLineSegmentDetector(cv2.LSD_REFINE_STD)
        lines_lsd, _, _, _ = lsd.detect(gray_smooth.astype(np.float64))
        if lines_lsd is not None:
            for seg in lines_lsd:
                x1, y1, x2, y2 = map(int, seg[0])
                seg_len = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
                if seg_len > diag * 0.015:  # Drop tiny noise segments
                    weight = float(np.clip(seg_len / (diag * 0.08), 0.2, 1.0))
                    cv2.line(lsd_mask, (x1, y1), (x2, y2), weight, 1)
    except Exception:
        pass  # LSD not available - graceful fallback

    # === 5. LAB CHROMINANCE EDGES - color-only boundaries ===
    # Critical for colored furniture/decor on white/neutral walls
    lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB).astype(np.float32)
    color_edge = np.zeros((h, w), dtype=np.float32)
    for c_idx in [1, 2]:  # A and B channels (skip L — already in scharr)
        ch = cv2.normalize(lab[:, :, c_idx], None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        ch_sm = cv2.GaussianBlur(ch, (3, 3), 0)
        cx = cv2.Scharr(ch_sm, cv2.CV_32F, 1, 0)
        cy = cv2.Scharr(ch_sm, cv2.CV_32F, 0, 1)
        ch_mag = cv2.magnitude(cx, cy)
        ch_norm = np.clip(ch_mag / (np.percentile(ch_mag, 97) + 1e-6), 0, 1).astype(np.float32)
        color_edge = np.maximum(color_edge, ch_norm)
    color_edge = np.clip(color_edge, 0, 1).astype(np.float32)

    # === 6. DEPTH DISCONTINUITIES - wall/foreground plane breaks ===
    depth_edge = np.zeros((h, w), dtype=np.float32)
    if depth_map is not None:
        try:
            dm = cv2.resize(depth_map.astype(np.float32), (w, h))
            # Bilateral-filter depth for cleaner discontinuity detection
            dm_smooth = cv2.bilateralFilter(dm, 7, 0.1, 5)
            ddx = cv2.Scharr(dm_smooth, cv2.CV_32F, 1, 0)
            ddy = cv2.Scharr(dm_smooth, cv2.CV_32F, 0, 1)
            depth_mag = cv2.magnitude(ddx, ddy)
            depth_edge = np.clip(depth_mag / (np.percentile(depth_mag, 98) + 1e-6), 0, 1).astype(np.float32)
        except Exception:
            pass

    # === WEIGHTED FUSION ===
    # Re-balanced to favor long architectural geometry (Hough/LSD) for cleaner trims
    master = (scharr_norm  * 0.15
            + canny_fused  * 0.22
            + hough_mask   * 0.28  # Higher authority for long lines
            + lsd_mask     * 0.20  # Higher authority for trims
            + color_edge   * 0.10
            + depth_edge   * 0.05)
    master = np.clip(master, 0, 1).astype(np.float32)

    # Minimal dilation - creates a very tight repulsion field (1200 ratio for sub-pixel precision)
    k_size = max(3, int(diag / 1200))
    if k_size % 2 == 0: k_size += 1
    master_dilated = cv2.dilate(
        (master * 255).astype(np.uint8),
        np.ones((k_size, k_size), np.uint8), iterations=1
    )
    return master_dilated.astype(np.float32) / 255.0


def build_architecture_barrier_map(image, depth_map=None):
    """
    DYNAMIC ARCHITECTURAL BARRIER MAP
    Detects structural stopping boundaries (door frames, hallways, window edges).
    Prevents texture spilling into unintended openings.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

    # 1. Strong structural edges
    edges = cv2.Canny(gray, 80, 160)

    # 2. Vertical geometry response
    sobel_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    vertical_strength = np.abs(sobel_x)
    vertical_strength = vertical_strength / (vertical_strength.max() + 1e-6)
    vertical_mask = (vertical_strength > np.percentile(vertical_strength, 92)).astype(np.uint8)

    # 3. Long line extraction
    line_mask = np.zeros_like(gray)
    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 180, threshold=80,
        minLineLength=int(image.shape[1] * 0.08),
        maxLineGap=10
    )

    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            if length > image.shape[1] * 0.12:
                cv2.line(line_mask, (x1, y1), (x2, y2), 255, 2)

    # 4. Depth discontinuity
    depth_edges = np.zeros_like(gray)
    if depth_map is not None:
        if depth_map.shape[:2] != gray.shape[:2]:
            depth_map = cv2.resize(depth_map, (gray.shape[1], gray.shape[0]))
        depth_dx = cv2.Sobel(depth_map.astype(np.float32), cv2.CV_32F, 1, 0)
        depth_edges = (np.abs(depth_dx) > np.percentile(np.abs(depth_dx), 90)).astype(np.uint8) * 255

    # 5. Merge all barriers
    barrier = np.maximum(edges, line_mask)
    barrier = np.maximum(barrier, vertical_mask * 255)
    barrier = np.maximum(barrier, depth_edges)

    # 6. Dilate slightly
    kernel = np.ones((3,3), np.uint8)
    barrier = cv2.dilate(barrier, kernel, iterations=1)

    return (barrier > 0).astype(np.uint8)


def compute_depth_foreground_suppression(depth_map, object_mask, wall_mask_alpha):
    """
    DEPTH-AWARE FOREGROUND SEPARATION:
    Suppresses wall alpha where objects are demonstrably closer (foreground) than the wall.
    Prevents wallpaper from crossing sofa/plant/TV boundaries using depth discontinuities.
    """
    if depth_map is None: return wall_mask_alpha
    try:
        h, w = wall_mask_alpha.shape
        dm = cv2.resize(depth_map.astype(np.float32), (w, h))
        # MiDaS: smaller value = closer. We invert so foreground = high value.
        dm_inv = 1.0 - dm

        # Estimate wall depth reference: median depth in pure-wall regions
        pure_wall = (wall_mask_alpha > 0.7).astype(bool)
        if np.any(pure_wall):
            wall_depth_ref = np.median(dm_inv[pure_wall])
        else:
            wall_depth_ref = np.median(dm_inv)

        # Objects significantly closer (higher inv-depth) than wall -> force alpha=0
        # Threshold: object must be at least 15% closer than wall reference
        foreground_zone = (dm_inv > wall_depth_ref + 0.15).astype(np.float32)

        # Intersect with YOLO object mask to avoid suppressing dark wall regions
        if object_mask is not None:
            obj = cv2.resize(object_mask.astype(np.float32), (w, h))
            foreground_zone = foreground_zone * obj

        # Smooth transition boundary (avoid hard cuts at suppression edge)
        foreground_zone = cv2.GaussianBlur(foreground_zone, (7, 7), 0)
        suppressed = wall_mask_alpha * np.clip(1.0 - foreground_zone * 1.5, 0, 1)
        return suppressed.astype(np.float32)
    except Exception:
        return wall_mask_alpha


def detect_edges(image, depth_map=None):
    """Step 3: Multi-Edge Authority Field - Architectural Locking.
    Returns uint8 [0,255] master edge map for backward compatibility.
    Internally uses build_master_edge_field for fused edge authority.
    """
    master = build_master_edge_field(image, depth_map=depth_map)
    return (master * 255).astype(np.uint8)


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

def detect_vanishing_points(image):
    """
    Detect architectural vanishing points using Hough Line Transform.
    Returns the primary vanishing point (x, y) or None.
    """
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100, minLineLength=100, maxLineGap=10)
        
        if lines is None: return None
        
        h, w = image.shape[:2]
        intersections = []
        
        # We only care about non-horizontal and non-vertical lines for VPs
        filtered_lines = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if x2 == x1: continue # Vertical
            slope = (y2 - y1) / (x2 - x1)
            if abs(slope) < 0.1 or abs(slope) > 10: continue # Too horizontal or vertical
            filtered_lines.append(line[0])
            
        # Limit processing for performance
        filtered_lines = filtered_lines[:20]
        
        for i in range(len(filtered_lines)):
            for j in range(i + 1, len(filtered_lines)):
                l1 = filtered_lines[i]
                l2 = filtered_lines[j]
                
                # Line intersection
                # x = ((x1y2 - y1x2)(x3 - x4) - (x1 - x2)(x3y4 - y3x4)) / ((x1 - x2)(y3 - y4) - (y1 - y2)(x3 - x4))
                denom = (l1[0] - l1[2]) * (l2[1] - l2[3]) - (l1[1] - l1[3]) * (l2[0] - l2[2])
                if abs(denom) < 1e-6: continue
                
                px = ((l1[0]*l1[3] - l1[1]*l1[2])*(l2[0] - l2[2]) - (l1[0] - l1[2])*(l2[0]*l2[3] - l2[1]*l2[2])) / denom
                py = ((l1[0]*l1[3] - l1[1]*l1[2])*(l2[1] - l2[3]) - (l1[1] - l1[3])*(l2[0]*l2[3] - l2[1]*l2[2])) / denom
                
                # Intersections should be somewhat near the center or reachable
                if -w < px < 2*w and -h < py < 2*h:
                    intersections.append((px, py))
        
        if not intersections: return (w//2, h//2)
        
        # Find the most common intersection point (cluster center)
        # For simplicity, we use the median
        vp_x = np.median([p[0] for p in intersections])
        vp_y = np.median([p[1] for p in intersections])
        
        return (int(vp_x), int(vp_y))
    except Exception as e:
        print(f"[ERROR] VP Detection failed: {e}")
        return None

def detect_planes(image, mask, depth_map):
    """
    Decompose the wall mask into dominant architectural planes (Left, Front, Right).
    Returns a list of (mask, orientation, corners) tuples for perspective warping.
    """
    if depth_map is None: return [(mask, "front", None)]
    
    h, w = mask.shape
    vp = detect_vanishing_points(image)
    if vp is None: vp = (w // 2, h // 2)
    
    # 1. Analyze depth gradients and horizontal profile to find plane transitions
    depth_profile = np.mean(depth_map, axis=0)
    depth_diff = np.abs(np.gradient(depth_profile))
    
    # Identify vertical "seams" (corners) where depth changes sharply
    potential_corners = np.where(depth_diff > np.percentile(depth_diff, 96))[0]
    
    last_x = 0
    min_plane_width = w * 0.12 
    planes = []
    
    # Simple segmentation into Left, Front, Right based on seams
    for corner_x in potential_corners:
        if corner_x - last_x < min_plane_width: continue
        
        plane_mask = np.zeros_like(mask)
        plane_mask[:, last_x:corner_x] = mask[:, last_x:corner_x]
        
        if np.sum(plane_mask) > (h * w * 0.01):
            seg_depth = depth_profile[last_x:corner_x]
            # Heuristic for orientation
            if seg_depth[-1] > seg_depth[0] + 0.03: orientation = "left"
            elif seg_depth[0] > seg_depth[-1] + 0.03: orientation = "right"
            else: orientation = "front"
            
            # Extract polygon corners for this plane
            # We find the convex hull of the mask to get approximate boundaries
            corners = extract_plane_corners(plane_mask, orientation, vp)
            planes.append((plane_mask, orientation, corners))
            last_x = corner_x
            
    # Final segment
    plane_mask = np.zeros_like(mask)
    plane_mask[:, last_x:] = mask[:, last_x:]
    if np.sum(plane_mask) > (h * w * 0.01):
        seg_depth = depth_profile[last_x:]
        if seg_depth[0] > seg_depth[-1] + 0.03: orientation = "right"
        else: orientation = "front"
        corners = extract_plane_corners(plane_mask, orientation, vp)
        planes.append((plane_mask, orientation, corners))
        
    return planes if planes else [(mask, "front", None)]

def extract_plane_corners(mask, orientation, vp):
    """
    Extract the 4 major corners of a wall plane for homography.
    Uses vanishing point geometry for mathematically accurate projection.
    """
    h, w = mask.shape
    coords = np.column_stack(np.where(mask > 0))
    if len(coords) < 10: return None
    
    # Find bounding box
    y_min, x_min = coords.min(axis=0)
    y_max, x_max = coords.max(axis=0)
    
    v_x, v_y = vp
    
    if orientation == "front":
        # Front walls are mostly 2D, but we can add a slight perspective if needed
        return np.float32([[x_min, y_min], [x_max, y_min], [x_min, y_max], [x_max, y_max]])
    
    # Mathematical Vanishing Line Projection
    if orientation == "left":
        # Near edge (Right): x_max
        # Far edge (Left): x_min
        # We project the y_min and y_max from the Near edge toward the VP to find Far edge y-coords
        
        # Slope from Near-Top to VP
        slope_top = (v_y - y_min) / (v_x - x_max + 1e-6)
        y_top_far = y_min + slope_top * (x_min - x_max)
        
        # Slope from Near-Bottom to VP
        slope_bottom = (v_y - y_max) / (v_x - x_max + 1e-6)
        y_bottom_far = y_max + slope_bottom * (x_min - x_max)
        
        pts = np.float32([
            [x_min, y_top_far],    # Top-Far
            [x_max, y_min],        # Top-Near
            [x_min, y_bottom_far], # Bottom-Far
            [x_max, y_max]         # Bottom-Near
        ])
    else: # right
        # Near edge (Left): x_min
        # Far edge (Right): x_max
        
        # Slope from Near-Top to VP
        slope_top = (v_y - y_min) / (v_x - x_min + 1e-6)
        y_top_far = y_min + slope_top * (x_max - x_min)
        
        # Slope from Near-Bottom to VP
        slope_bottom = (v_y - y_max) / (v_x - x_min + 1e-6)
        y_bottom_far = y_max + slope_bottom * (x_max - x_min)
        
        pts = np.float32([
            [x_min, y_min],        # Top-Near
            [x_max, y_top_far],    # Top-Far
            [x_min, y_max],        # Bottom-Near
            [x_max, y_bottom_far]  # Bottom-Far
        ])
        
    return pts

def detect_glass(image):
    """Step 5: Dynamic Glass/Window Detection (HSV + Texture Smoothness)"""
    hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
    s_channel = hsv[:,:,1]
    v_channel = hsv[:,:,2]
    
    # Texture smoothness check (Glass/Windows are usually very smooth)
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    edges = cv2.Sobel(gray, cv2.CV_64F, 1, 1, ksize=3)
    edges_abs = np.abs(edges)
    smooth_mask = cv2.GaussianBlur(edges_abs, (15, 15), 0) < 20
    
    # Glass rule: High brightness + Low saturation + Smoothness
    v_thresh = np.percentile(v_channel, 90) 
    s_thresh = np.percentile(s_channel, 15) 
    
    return ((v_channel > v_thresh) & (s_channel < s_thresh) & smooth_mask).astype(np.uint8)

@time_it
def refine_mask(image, wall_mask, protection_mask, preview_mode=True, session_id=None):
    """Step 6: Fine Segmentation & Boundary Refinement using SAM"""
    # Performance: Default to FAST on CPU unless HD is explicitly requested
    if preview_mode:
        # FAST PATH: Use lightweight morphology instead of heavy SAM
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        refined = cv2.morphologyEx(wall_mask, cv2.MORPH_OPEN, kernel)
        return refined

    try:
        # Cache SAM embeddings for the room to avoid repeated set_image()
        if session_id and session_id in sam_embeddings_cache:
            pass
        else:
            sam_predictor.set_image(image)
            if session_id:
                sam_embeddings_cache[session_id] = True

        wall_y, wall_x = np.where(wall_mask > 0)
        if len(wall_x) == 0: return wall_mask
        
        point_count = min(15, max(5, int(len(wall_x) / 50000)))
        sample_indices = np.linspace(0, len(wall_x) - 1, point_count).astype(int)
        points = np.column_stack((wall_x[sample_indices], wall_y[sample_indices]))
        
        # Performance: Batch point prediction for SAM
        point_labels = np.ones(len(points))
        masks, scores, logits = sam_predictor.predict(
            point_coords=points,
            point_labels=point_labels,
            multimask_output=True
        )
        
        # Select best mask among the 3 predicted by SAM
        m = masks[np.argmax(scores)]
        return m.astype(np.uint8)
    except Exception as e:
        print(f"SAM Refine Error: {e}")
        return wall_mask

@time_it
def finalize_mask(mask, image, edges=None, protection_layer=None, depth_map=None, use_fast_mode=False, foreground_alpha=None):
    """
    Step 8 & 9: Production-Grade Mask Refinement.
    """
    mask = mask.astype(np.uint8)
    h, w = image.shape[:2]
    diag = np.sqrt(h**2 + w**2)
    
    # 1. Performance-Aware Cleanup
    k_size = 5 if not use_fast_mode else 3
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k_size, k_size))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)

    # 2. GLOBAL PLANE RECOVERY (Bridge fragmented wall pieces)
    # Instead of just keeping the largest component, we use a similarity-based approach
    num_labels, labels_cc, stats, centroids = cv2.connectedComponentsWithStats(mask)
    if num_labels > 2:
        max_area = np.max(stats[1:, cv2.CC_STAT_AREA])
        valid_indices = []
        
        # We always keep the primary wall
        primary_idx = np.argmax(stats[1:, cv2.CC_STAT_AREA]) + 1
        valid_indices.append(primary_idx)
        
        # Get depth reference for the primary wall
        dm_resized = cv2.resize(depth_map.astype(np.float32), (w, h)) if depth_map is not None else None
        primary_mask = (labels_cc == primary_idx)
        primary_depth = np.median(dm_resized[primary_mask]) if dm_resized is not None and np.any(primary_mask) else 0

        for i in range(1, num_labels):
            if i == primary_idx: continue
            
            area = stats[i, cv2.CC_STAT_AREA]
            # 1. Keep large enough surfaces (> 1% of total image)
            if area > (h * w * 0.01):
                valid_indices.append(i)
                continue
                
            # 2. Plane Continuity Check: Keep small regions if they share the same plane/depth
            if dm_resized is not None:
                comp_mask = (labels_cc == i)
                comp_depth = np.median(dm_resized[comp_mask])
                # If depth is very similar to primary wall, it's likely a fragmented part (TV/lamp case)
                if abs(comp_depth - primary_depth) < 0.05:
                    valid_indices.append(i)
                    
        mask = np.isin(labels_cc, valid_indices).astype(np.uint8)

    # 3. EDGE-LOCKED GUIDED FILTER REFINEMENT
    gray_guide = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    refined_alpha = fast_guided_filter(gray_guide, mask, radius=max(3, int(diag / 600)), eps=0.0001)
    refined_alpha = np.clip(refined_alpha, 0.0, 1.0).astype(np.float32)

    # 4. ADAPTIVE GAUSSIAN-WEIGHTED EDGE ATTRACTION
    if edges is not None:
        edge_f = edges.astype(np.float32) / 255.0
        # Use a tighter attraction field (5x5 instead of 9x9) for sharper trim snapping
        edge_influence = cv2.GaussianBlur(edge_f, (5, 5), 0)
        edge_influence = np.clip(edge_influence * 2.2, 0, 1)  # Higher authority boost

        hard_alpha = (refined_alpha > 0.5).astype(np.float32)
        refined_alpha = refined_alpha * (1.0 - edge_influence) + hard_alpha * edge_influence

    # 5. Non-linear contrast curve & MASK BOOST
    safe_alpha = np.clip(refined_alpha, 1e-6, 1.0 - 1e-6)
    refined_alpha = np.where(safe_alpha > 0.5,
                             np.power(safe_alpha, 0.6),
                             np.power(safe_alpha, 1.4))
    
    # [INFO] RESTORED QUALITY: Boost mask strength so wallpaper covers fully
    refined_alpha = np.clip(refined_alpha * 1.15, 0, 1).astype(np.float32)

    # 6. DEPTH-AWARE FOREGROUND SUPPRESSION
    obj_mask_for_depth = protection_layer
    refined_alpha = compute_depth_foreground_suppression(depth_map, obj_mask_for_depth, refined_alpha)

    # 7. SOFT OCCLUSION BLENDING (Replaces hard object removal)
    if foreground_alpha is not None or protection_layer is not None:
        occlusion = build_soft_occlusion_map(image, protection_layer, foreground_alpha)
        refined_alpha = refined_alpha * (1.0 - occlusion)

    # 8. TIERED PROTECTION BLENDING
    global _last_tiered_protection
    if _last_tiered_protection is not None:
        tp = _last_tiered_protection
        for tier_name, suppression_strength in [('critical', 1.0), ('medium', 0.98), ('soft', 0.85)]:
            tier_m = tp.get(tier_name)
            if tier_m is None: continue
            if tier_m.shape[:2] != (h, w):
                tier_m = cv2.resize(tier_m, (w, h), interpolation=cv2.INTER_NEAREST)
            dil_k = {'critical': 5, 'medium': 3, 'soft': 2}[tier_name]
            tier_dilated = cv2.dilate(tier_m, np.ones((dil_k, dil_k), np.uint8), iterations=1).astype(np.float32)
            tier_smooth = cv2.GaussianBlur(tier_dilated, (5, 5), 0)
            
            # Robust broadcasting check
            if refined_alpha.shape[:2] != tier_smooth.shape[:2]:
                tier_smooth = cv2.resize(tier_smooth, (refined_alpha.shape[1], refined_alpha.shape[0]), interpolation=cv2.INTER_LINEAR)
                
            refined_alpha = refined_alpha * np.clip(1.0 - tier_smooth * suppression_strength, 0, 1)

    # 9. FINAL ANTI-BLEED PASS
    if edges is not None and protection_layer is not None:
        strong_edge = (edges.astype(np.float32) / 255.0 > 0.5)
        prot_resized = cv2.resize(protection_layer.astype(np.float32), (w, h), interpolation=cv2.INTER_NEAREST)
        bleed_zone = (strong_edge & (prot_resized > 0)).astype(np.float32)
        bleed_zone = cv2.dilate(bleed_zone, np.ones((3, 3), np.uint8), iterations=1).astype(np.float32)
        bleed_zone = cv2.GaussianBlur(bleed_zone, (5, 5), 0)
        refined_alpha = refined_alpha * np.clip(1.0 - bleed_zone * 1.8, 0, 1) # Increased suppression

    # 10. FINAL HARD PROTECTION OVERRIDE
    if protection_layer is not None:
        if protection_layer.shape[:2] != (h, w):
            protection_layer = cv2.resize(protection_layer, (w, h), interpolation=cv2.INTER_NEAREST)
        shield = cv2.dilate(protection_layer, np.ones((3, 3), np.uint8), iterations=1).astype(np.float32)
        refined_alpha = refined_alpha * (1.0 - shield)

    # 11. OBJECT-AWARE WALL MASKING (VFX Pipeline)
    if foreground_alpha is not None:
        if foreground_alpha.shape[:2] != (h, w):
            foreground_alpha = cv2.resize(foreground_alpha, (w, h), interpolation=cv2.INTER_LINEAR)
        refined_alpha = refined_alpha * (1.0 - foreground_alpha)
        refined_alpha = np.clip(refined_alpha, 0, 1)
        refined_alpha = cv2.GaussianBlur(refined_alpha, (7,7), 0)

    return np.clip(refined_alpha, 0, 1).astype(np.float32)

def tile_texture(texture, target_h, target_w, scale=1.0):
    """
    Dynamic High-Fidelity Tiling.
    Automatically balances pattern density so the texture looks "natural" 
    on walls of different resolutions.
    """
    try:
        th, tw = texture.shape[:2]
        
        # [INFO] DYNAMIC SCALING: Ensure the pattern isn't "too dense"
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

def blend_lighting(texture, light_field):
    """
    Professional Multi-Pass Lighting Blend.
    Uses a combination of Multiplication and Soft Light for high-fidelity realism.
    """
    # 1. Multiplicative Pass (Core shadows/highlights)
    texture_f = texture.astype(np.float32)
    # Clip light field to avoid extreme blowouts or pitch black
    light_field_clipped = np.clip(light_field, 0.35, 1.5)
    multiplied = texture_f * np.expand_dims(light_field_clipped, axis=2)
    
    # 2. Soft Light Pass (Preserves local texture detail in highlights)
    # Formula: (1 - 2*b)*a^2 + 2*b*a
    a = texture_f / 255.0
    b = np.expand_dims(light_field_clipped / 1.0, axis=2) # Normalized light
    soft_light = (1.0 - 2.0*b) * (a**2) + 2.0*b*a
    soft_light = np.clip(soft_light * 255.0, 0, 255)
    
    # 3. Dynamic Mixing
    # Use more of the soft light in bright areas to prevent washing out the pattern
    result = cv2.addWeighted(multiplied, 0.7, soft_light, 0.3, 0)
    return result

def perspective_tile(texture, target_h, target_w, scale, orientation="front", corners=None):
    """
    Warp a tiled texture based on architectural plane orientation or polygon corners.
    Uses Homography for professional 3D projection.
    """
    # 1. Generate standard high-res tiling
    tiled = tile_texture(texture, target_h, target_w, scale=scale)
    
    if orientation == "front" and corners is None:
        return tiled
        
    # 2. Geometry-Aware Perspective Warp
    # Source corners (the full tiled texture)
    pts_src = np.float32([[0, 0], [target_w, 0], [0, target_h], [target_w, target_h]])
    
    if corners is not None:
        # PROFESSIONAL PATH: Use extracted wall polygon
        # reorder corners to match [top-left, top-right, bottom-left, bottom-right]
        # Our extract_plane_corners returns that order
        matrix, _ = cv2.findHomography(pts_src, corners)
    else:
        # FALLBACK PATH: Improved hardcoded projection using vanishing lines
        if orientation == "left":
            pts_dst = np.float32([[target_w*0.25, target_h*0.1], [target_w, 0], [target_w*0.25, target_h*0.9], [target_w, target_h]])
        else: # right
            pts_dst = np.float32([[0, 0], [target_w*0.75, target_h*0.1], [0, target_h], [target_w*0.75, target_h*0.9]])
        matrix = cv2.getPerspectiveTransform(pts_src, pts_dst)
        
    warped = cv2.warpPerspective(tiled, matrix, (target_w, target_h), borderMode=cv2.BORDER_REPLICATE)
    return warped

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

def apply_artistic_filter(image, quality_mode=True):
    """
    Architectural Tone Mapping & Premium Visual Filter.
    Now optimized for high-fidelity production rendering.
    """
    try:
        # 1. Local Contrast Enhancement (CLAHE) - Essential for depth and detail
        lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        # Tighter clip limit for more natural look (1.2 instead of 1.5)
        clahe = cv2.createCLAHE(clipLimit=1.2, tileGridSize=(8,8))
        l = clahe.apply(l)
        img = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2RGB)
        
        # 2. Color Balance (Subtle warming for premium feel)
        img = img.astype(np.float32)
        img[:,:,0] *= 1.015 # Subtle Red boost
        img[:,:,2] *= 0.99  # Subtle Blue suppression
        
        # 3. Selective Vibrance
        hsv = cv2.cvtColor(np.clip(img, 0, 255).astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
        hsv[:,:,1] *= 1.04
        img = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)
        
        # 4. Professional Vignette (Cinematic depth)
        if quality_mode:
            h, w = img.shape[:2]
            kernel_x = cv2.getGaussianKernel(w, int(w/1.2))
            kernel_y = cv2.getGaussianKernel(h, int(h/1.2))
            v_mask = (kernel_y * kernel_x.T)
            v_mask = v_mask / v_mask.max()
            v_mask = np.power(v_mask, 0.06) # Restored for 'premium' look
            
            img_f = img.astype(np.float32)
            for i in range(3):
                img_f[:,:,i] *= v_mask
            img = np.clip(img_f, 0, 255).astype(np.uint8)
            
        return img
    except Exception:
        return image

def apply_texture(image, mask, texture, scale=1.0, quality_mode=True, depth_map=None, foreground_alpha=None):
    """
    GEOMETRY-AWARE RENDERING ENGINE
    Implements plane-aware projection and intrinsic lighting preservation.
    """
    try:
        h, w = image.shape[:2]
        
        # --- 1. INTRINSIC LIGHTING PRESERVATION ---
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY).astype(np.float32)
        
        # Optimization: Use fast Gaussian if not in high quality mode
        if not quality_mode:
            illumination = cv2.GaussianBlur(gray, (31, 31), 0)
        else:
            illumination = cv2.bilateralFilter(gray, 11, 50, 50)
        
        wall_avg = np.mean(illumination[mask > 0.5]) if np.any(mask > 0.5) else 128.0
        light_field = illumination / (wall_avg + 1e-6)
        
        # --- 2. PLANE-AWARE PERSPECTIVE PROJECTION ---
        planes = detect_planes(image, mask, depth_map)
        full_texture_map = np.zeros_like(image, dtype=np.float32)
        
        for plane_mask, orientation, corners in planes:
            # Scale adjustment: Side walls need higher density because they are compressed
            plane_scale = scale * (1.5 if orientation != "front" else 1.0)
            warped_plane = perspective_tile(texture, h, w, plane_scale, orientation, corners).astype(np.float32)
            full_texture_map += warped_plane * np.expand_dims(plane_mask, axis=2)
            
        # --- 3. DUAL-SCALE LIGHTING MULTIPLEXER ---
        blended = blend_lighting(full_texture_map, light_field)
        
        # Optimization: Skip secondary lighting pass in fast mode
        if quality_mode:
            try:
                lab_img = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
                l_channel = lab_img[:,:,0].astype(np.float32)
                smooth_light = cv2.GaussianBlur(l_channel, (25, 25), 0)
                mean_light = np.mean(smooth_light[mask > 0.2]) if np.any(mask > 0.2) else 128.0
                lighting_3d = smooth_light / (mean_light + 1e-6)
                blended = blend_lighting(blended, lighting_3d)
            except: pass

        # --- 4. DEPTH-AWARE COMPOSITING ---
        alpha_mask_3d = np.expand_dims(mask, axis=2)
        reconstructed_rgb = image.astype(np.float32)
        
        # New Feature: Object-aware wall masking and VFX compositing
        if foreground_alpha is not None:
            if foreground_alpha.shape[:2] != (h, w):
                foreground_alpha = cv2.resize(foreground_alpha, (w, h), interpolation=cv2.INTER_LINEAR)
            
            # Match Colab's background logic
            background = (blended * alpha_mask_3d) + (reconstructed_rgb * (1.0 - alpha_mask_3d))
            # Match Colab's VFX compositing logic
            fg_alpha_3d = np.expand_dims(foreground_alpha, axis=2)
            result = (reconstructed_rgb * fg_alpha_3d) + (background * (1.0 - fg_alpha_3d))
        else:
            result = (blended * alpha_mask_3d) + (reconstructed_rgb * (1.0 - alpha_mask_3d))
            
        np.clip(result, 0, 255, out=result)
        
        result_uint8 = result.astype(np.uint8)
        
        # New Feature: VFX-style Sharpening (as in Colab)
        if quality_mode:
            kernel_sharp = np.array([
                [-1,-1,-1],
                [-1, 9,-1],
                [-1,-1,-1]
            ])
            sharp = cv2.filter2D(result_uint8, -1, kernel_sharp)
            result_uint8 = cv2.addWeighted(result_uint8, 0.9, sharp, 0.1, 0)
        
        return apply_artistic_filter(result_uint8, quality_mode=quality_mode)
        
    except Exception as e:
        print(f"Rendering Engine Error: {e}")
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

        # 1. PROCESS & PREP (Fixed 1024px resolution for AI)
        image = decode_image(wall_bytes)
        if image is None: return jsonify({'error': 'Invalid image'}), 400
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        h_orig, w_orig = image_rgb.shape[:2]
        max_dim_ai = 1024
        scale_ai = max_dim_ai / max(h_orig, w_orig)
        image_ai = cv2.resize(image_rgb, (int(w_orig * scale_ai), int(h_orig * scale_ai)))
        
        # 2. PARALLEL AI SEGMENTATION & GEOMETRIC UNDERSTANDING
        # We run SegFormer, YOLO, Depth and Rembg concurrently
        print("[DEBUG] Running parallel AI models...", flush=True)
        future_walls = executor.submit(detect_walls, image_ai)
        future_objects = executor.submit(detect_objects, image_ai)
        future_depth = executor.submit(estimate_depth, image_ai)
        future_alpha = executor.submit(extract_foreground_alpha, image_ai)
        
        # Wait for parallel results
        wall_mask, structural_protection, labels = future_walls.result()
        object_mask = future_objects.result()
        depth_map = future_depth.result()
        foreground_alpha = future_alpha.result()
        
        # Sequential post-AI steps (Fast enough at 1024px)
        edges = build_master_edge_field(image_ai, depth_map=depth_map, use_fast_mode=False)
        # Ensure dimensions match before bitwise operation
        if structural_protection.shape[:2] != object_mask.shape[:2]:
            object_mask = cv2.resize(object_mask, (structural_protection.shape[1], structural_protection.shape[0]), interpolation=cv2.INTER_NEAREST)
            
        protection_layer = cv2.bitwise_or(structural_protection, object_mask)
        
        # SAM Refinement (Use cached embedding if same room)
        refined = refine_mask(image_ai, wall_mask, protection_layer, session_id=image_hash)
        
        mask_soft = finalize_mask(refined, image_ai, edges=edges,
                                  protection_layer=protection_layer, depth_map=depth_map,
                                  foreground_alpha=foreground_alpha)
        
        # 3. STORE SESSION (1024px assets for instant material switching)
        # We store AI-ready assets to avoid re-running models on material change
        room_session_cache[image_hash] = {
            'image_ai': image_ai,
            'mask_ai': mask_soft,
            'edges_ai': edges,
            'protection_ai': protection_layer,
            'depth_ai': depth_map,
            'foreground_alpha_ai': foreground_alpha,
            'h_orig': h_orig,
            'w_orig': w_orig,
            'timestamp': time.time()
        }
        
        # Cleanup old sessions if cache is too large
        if len(room_session_cache) > 30:
            oldest_key = list(room_session_cache.keys())[0]
            del room_session_cache[oldest_key]
        
        # Sync with legacy wall_cache for backward compatibility
        wall_cache[image_hash] = room_session_cache[image_hash]
        
        print(f"[INFO] SESSION CREATED: {image_hash} in {time.time() - start_time:.2f}s", flush=True)
        return jsonify({
            'success': True,
            'session_id': image_hash,
            'dimensions': {'w': w_orig, 'h': h_orig},
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
        return jsonify({'error': 'AI Models are still loading.', 'retry': True}), 503
    
    use_fast_mode = request.form.get('mode') == 'fast'
    quality_render = request.form.get('quality') == 'hd'

    try:
        start_total = time.time()
        session_id = request.form.get('session_id') or request.args.get('session_id')
        
        # 1. RETRIEVE OR CREATE SESSION
        if session_id and session_id in room_session_cache:
            print(f"[PERF] Session Hit: {session_id}", flush=True)
            cached = room_session_cache[session_id]
        else:
            # FALLBACK: If no session, process the image from scratch
            if 'wall_image' not in request.files:
                return jsonify({'error': 'Session expired. Please re-upload.'}), 401
            
            print("[INFO] No session found. Processing full pipeline...", flush=True)
            wall_file = request.files['wall_image']
            wall_bytes = wall_file.read()
            image_hash = hashlib.md5(wall_bytes).hexdigest()
            
            # Check if this hash is already in cache
            if image_hash in room_session_cache:
                cached = room_session_cache[image_hash]
            else:
                # Process the image (simplified internal call to logic used in upload_room)
                # For optimal performance, we redirect to a internal processor
                image_bgr = decode_image(wall_bytes)
                image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
                h_orig, w_orig = image_rgb.shape[:2]
                
                # Scale for AI processing
                scale_ai = 1024 / max(h_orig, w_orig)
                image_ai = cv2.resize(image_rgb, (int(w_orig * scale_ai), int(h_orig * scale_ai)))
                
                # Run AI pipeline
                future_walls = executor.submit(detect_walls, image_ai)
                future_objects = executor.submit(detect_objects, image_ai, use_fast_mode=use_fast_mode)
                future_depth = executor.submit(lambda: None)
                future_alpha = executor.submit(extract_foreground_alpha, image_ai)
                
                wall_mask, structural, _ = future_walls.result()
                obj_mask = future_objects.result()
                depth = future_depth.result()
                foreground_alpha = future_alpha.result()
                
                # Use faster edges in fallback mode
                edges = build_master_edge_field(image_ai, depth_map=depth, use_fast_mode=use_fast_mode)
                # Ensure dimensions match before bitwise operation
                if structural.shape[:2] != obj_mask.shape[:2]:
                    obj_mask = cv2.resize(obj_mask, (structural.shape[1], structural.shape[0]), interpolation=cv2.INTER_NEAREST)
                    
                prot = cv2.bitwise_or(structural, obj_mask)
                refined = refine_mask(image_ai, wall_mask, prot, preview_mode=not quality_render, session_id=image_hash)
                final_m = finalize_mask(refined, image_ai, edges=edges, protection_layer=prot, depth_map=depth, foreground_alpha=foreground_alpha)
                
                cached = {
                    'image_ai': image_ai,
                    'mask_ai': final_m,
                    'edges_ai': edges,
                    'protection_ai': prot,
                    'depth_ai': depth,
                    'foreground_alpha_ai': foreground_alpha,
                    'h_orig': h_orig,
                    'w_orig': w_orig
                }
                room_session_cache[image_hash] = cached
        
        image_ai = cached['image_ai']
        mask_ai = cached['mask_ai']
        depth_ai = cached['depth_ai']
        h_orig, w_orig = cached['h_orig'], cached['w_orig']

        # 2. RENDER-TIME RESOLUTION MANAGEMENT
        target_dim = 1024 if quality_render else 768
        scale = target_dim / max(h_orig, w_orig)
        new_w, new_h = int(w_orig * scale), int(h_orig * scale)
        
        image_render = cv2.resize(image_ai, (new_w, new_h))
        mask_render = cv2.resize(mask_ai, (new_w, new_h))
        depth_render = cv2.resize(depth_ai, (new_w, new_h)) if depth_ai is not None else None
        
        foreground_alpha_ai = cached.get('foreground_alpha_ai')
        foreground_alpha_render = cv2.resize(foreground_alpha_ai, (new_w, new_h)) if foreground_alpha_ai is not None else None

        # 3. TEXTURE RETRIEVAL
        texture_url = request.form.get('texture_url')
        texture_hash = hashlib.md5(texture_url.encode()).hexdigest() if texture_url else "upload"
        
        if texture_hash in texture_cache:
            texture = texture_cache[texture_hash]
        else:
            if 'texture_image' in request.files:
                texture = decode_image(request.files['texture_image'].read())
            else:
                import requests
                texture = decode_image(requests.get(texture_url).content)
            
            if texture is not None:
                texture = cv2.cvtColor(texture, cv2.COLOR_BGR2RGB)
                texture_cache[texture_hash] = texture

        if texture is None: return jsonify({'error': 'Texture error'}), 400

        # 4. APPLY TEXTURE
        result_rgb = apply_texture(
            image_render, 
            mask_render, 
            texture, 
            scale=1.0, 
            quality_mode=not use_fast_mode,
            depth_map=depth_render,
            foreground_alpha=foreground_alpha_render
        )
        
        # 5. ENCODE & RETURN
        result_bgr = cv2.cvtColor(result_rgb, cv2.COLOR_RGB2BGR)
        is_success, buffer = cv2.imencode(".webp", result_bgr, [cv2.IMWRITE_WEBP_QUALITY, 70])
        import base64
        data_uri = f"data:image/webp;base64,{base64.b64encode(buffer).decode('utf-8')}"
        
        total_time = (time.time() - start_total) * 1000
        print(f"[PERF] Total Process took {total_time:.2f}ms", flush=True)
        
        return jsonify({
            'resultUrl': data_uri,
            'timings': {'total': round(total_time, 2)},
            'cache_hit': True,
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

# ==========================================
# AI COPILOT CONVERSATIONAL ROUTES
# =========================================================

@app.route('/api/ai-chat', methods=['POST'])
def ai_chat():
    """
    CONVERSATIONAL AI PARSER:
    Converts natural language user requests into structured tasks.
    """
    if not client:
        return jsonify({'error': 'OpenAI API key not configured'}), 500

    try:
        data = request.json
        prompt = data.get('prompt')
        session_id = data.get('session_id')
        
        if not prompt:
            return jsonify({'error': 'Missing prompt'}), 400

        # System Prompt for Interior Design Parsing
        system_message = """
        You are an AI Interior Design Copilot. Your task is to analyze user requests.
        IMPORTANT: Your architecture is now DIRECT and SYNCHRONOUS. Do NOT mention queues, background tasks, or workers.
        
        If the user is just saying hello, greeting you, or asking general questions, return:
        { "action": "chat", "response": "A friendly response to the user." }
        
        If the user is asking to edit a room, return a JSON task:
        Available Actions:
        1. 'recolor': Change color/texture.
        2. 'redesign': Complete overhaul (Creative Concept).
        3. 'add': Add an object.
        4. 'remove': Remove an object.
        
        Output format for tasks:
        {
          "action": "recolor" | "redesign" | "add" | "remove",
          "target": "wall" | "floor" | "cabinet" | "sofa" | "all" | string,
          "color": string | null,
          "style": string | null,
          "description": string,
          "response": "I'm starting your AI concept visualization now! Please wait while I generate your inspiration preview."
        }
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" }
        )
        
        # Calculate Cost for GPT-4o
        usage = response.usage
        input_cost = (usage.prompt_tokens / 1000000) * 5.00
        output_cost = (usage.completion_tokens / 1000000) * 15.00
        total_cost = input_cost + output_cost
        
        print(f"\n[AI COST] GPT-4o Chat: ${total_cost:.6f} (Tokens: {usage.total_tokens})", flush=True)
        
        import json
        task_json = json.loads(response.choices[0].message.content)
        
        # Validation for Chat vs Task
        if task_json.get('action') == 'chat':
            return jsonify({
                'success': True,
                'task': task_json,
                'cost': f"${total_cost:.6f}",
                'response': task_json.get('response', "Hello! How can I help you design your space today?")
            })

        return jsonify({
            'success': True,
            'task': task_json,
            'cost': f"${total_cost:.6f}",
            'response': task_json.get('response', f"I understand! You want to {task_json.get('action')} the {task_json.get('target')}.")
        })

    except Exception as e:
        print(f"AI Chat Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai-redesign', methods=['POST'])
@time_it
def ai_redesign():
    """
    AI REDESIGN ENDPOINT (Synchronous):
    Uses DALL-E for room redesign based on existing CV masks.
    Simple request -> result flow.
    """
    if not client:
        return jsonify({'error': 'OpenAI API key not configured'}), 500

    try:
        data = request.json
        user_prompt = data.get('prompt')
        session_id = data.get('session_id')
        target = data.get('target', 'all')
        
        if not user_prompt:
            return jsonify({'error': 'Missing prompt'}), 400

        if not session_id or session_id not in room_session_cache:
            return jsonify({'error': 'Session expired. Please upload a room first.'}), 400
            
        session = room_session_cache[session_id]
        image_rgb = session['image_ai']
        
        print(f"[AI REDESIGN] Generating for: {user_prompt}", flush=True)
        
        # Mandatory Backend Preservation Layer
        preservation = (
            "STRICTLY PRESERVE original room measurements, dimensions, and geometry. "
            "Keep original wall, door, and window positions exactly. Do not modify structure or camera perspective. "
            "ONLY transform interiors, furniture, and textures."
        )

        # Use DALL-E 3 for high-quality redesign
        full_prompt = (
            f"A professional high-fidelity interior design photo of this room redesigned as a {user_prompt}. "
            f"{preservation} Transform all materials and decor into a luxury {user_prompt} aesthetic. "
            f"Ultra-realistic, 8k, architectural digest style."
        )
        
        response = client.images.generate(
            model="dall-e-3",
            prompt=full_prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        result_url = response.data[0].url
        cost = 0.040

        print(f"[AI COST] DALL-E 3 Redesign: ${cost:.3f}", flush=True)
        return jsonify({
            'success': True,
            'resultUrl': result_url,
            'cost': f"${cost:.3f}",
            'message': "AI concept visualization ready!"
        })

    except Exception as e:
        print(f"AI Redesign Error: {e}")
        return jsonify({'error': str(e)}), 500

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

# ============================================================
# AI COPILOT — GEOMETRY LOCKED INTERIOR REDESIGN ENGINE
# Replicates the Colab notebook exactly
# ============================================================
ROOM_PROMPTS = {
    "bedroom": [
        "Modern blue and white master bedroom, keep exact same room measurements and geometry, edit only existing room, stylish king size bed, elegant blue and white wardrobes with soft LED lights, modern TV unit and lowers, premium curtains, dressing table with mirror, wall mounted AC, false ceiling lights, clean luxury interior, realistic lighting, modern aesthetic, ultra realistic render",
        "Luxury bedroom makeover in blue and white theme, preserve original room size and structure, modern bed design, full wall wardrobes, sleek lowers and storage cabinets, soft curtains, dressing table with round mirror, split AC, warm LED ceiling lights, stylish and premium interior design, realistic architecture visualization",
        "Elegant modern bedroom interior, do not change room dimensions, edit same room only, blue and white color combination, cozy king bed, glossy wardrobes with hidden lights, stylish lowers, beautiful curtains, compact dressing table and mirror, AC unit, minimalist luxury bedroom, cinematic lighting, photorealistic render",
        "Contemporary master bedroom design in navy blue and white colors, maintain same room measurements and perspective, premium bed with cushions, modern wardrobes, TV lowers and cabinets, soft flowing curtains, dressing table with LED mirror, wall AC, elegant ceiling lighting, bright and classy luxury interior",
        "Stylish blue and white bedroom renovation, preserve exact room geometry and wall positions, modern upholstered bed, sleek custom wardrobes, matching lowers, elegant curtains, dressing table and mirror setup, split AC, warm ambient lighting, modern luxury bedroom, ultra detailed realistic interior render"
    ],
    "living_room": [
        """
        ultra luxury modern living room. 
        SCENE ANALYSIS: Identify the central wall. PLACE A LARGE CINEMATIC FLAT-SCREEN TV on the wall. Align a luxury L-shaped sofa perfectly on the floor. 
        INSTRUCTIONS: Enhance existing wall niches/arches with decor. Use marble textures, warm LED lighting, and indoor plants. 
        STRICT GEOMETRY LOCK: Keep all structural lines, arches, and windows intact.
        """
    ],
    "kitchen": [
        """
        ultra modern modular kitchen with premium matte cabinets and marble countertops. 
        SCENE ANALYSIS: Follow the existing wall lines for cabinet placement. 
        INSTRUCTIONS: Add a sophisticated kitchen island and warm under-cabinet lighting. 
        STRICT GEOMETRY LOCK: Do not change room structure.
        """
    ],
    "bathroom": [
        """
        ultra luxury hotel-style bathroom with Italian marble. 
        SCENE ANALYSIS: Place a floating vanity and large backlit mirror. 
        INSTRUCTIONS: Add golden fittings and ambient LED lighting. 
        STRICT GEOMETRY LOCK: Preserve mirror and window positions.
        """
    ]
}


# ============================================================
# LEONARDO.AI INTEGRATION (CANVAS INPAINTING)
# ============================================================


def leonardo_upload_canvas_images(init_bytes, mask_bytes):
    """Uploads both init and mask images to Leonardo for Canvas inpainting."""
    try:
        # 1. Get presigned URLs for BOTH
        payload = {
            "initExtension": "png",
            "maskExtension": "png"
        }
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {LEONARDO_API_KEY}"
        }
        
        response = requests.post(f"{LEONARDO_API_URL}/canvas-init-image", json=payload, headers=headers)
        if not response.ok:
            print(f"[LEONARDO UPLOAD ERROR] {response.text}")
            return None, None
            
        data = response.json().get("uploadCanvasInitImage", {})
        
        # Extract Init details
        init_id = data.get("initImageId")
        init_url = data.get("initUrl")
        init_fields = json.loads(data.get("initFields", "{}"))
        
        # Extract Mask details
        mask_id = data.get("masksImageId")
        mask_url = data.get("masksUrl")
        mask_fields = json.loads(data.get("masksFields", "{}"))
        
        if not init_id or not mask_id:
            return None, None
            
        # 2. Upload Init Image
        # S3 requires the file to be the LAST field in the form
        files = {'file': ('init.png', init_bytes, 'image/png')}
        requests.post(init_url, data=init_fields, files=files)
        
        # 3. Upload Mask Image
        files_mask = {'file': ('mask.png', mask_bytes, 'image/png')}
        requests.post(mask_url, data=mask_fields, files=files_mask)
        
        return init_id, mask_id
    except Exception as e:
        print(f"[LEONARDO UPLOAD EXCEPTION] {e}")
        return None, None

def leonardo_generate_inpaint(prompt, init_id, mask_id):
    """Triggers a Leonardo Canvas Inpainting generation."""
    try:
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {LEONARDO_API_KEY}"
        }
        
        payload = {
            "prompt": prompt,
            "modelId": LEONARDO_MODEL_ID,
            "num_images": 1,
            "width": 1024,
            "height": 768,
            "init_strength": 0.2, # Very High change (0.8 inpaint strength)
            "guidance_scale": 15, # Maximum guidance to follow prompt strictly
            "canvasRequest": True,
            "canvasRequestType": "INPAINT",
            "canvasInitId": init_id,
            "canvasMaskId": mask_id
        }
        
        response = requests.post(f"{LEONARDO_API_URL}/generations", json=payload, headers=headers)
        if not response.ok:
            print(f"[LEONARDO GEN ERROR] {response.text}")
            return None
            
        generation_id = response.json().get("sdGenerationJob", {}).get("generationId")
        return generation_id
    except Exception as e:
        print(f"[LEONARDO GEN EXCEPTION] {e}")
        return None

def leonardo_wait_for_result(generation_id):
    """Polls Leonardo for the generation result."""
    try:
        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {LEONARDO_API_KEY}"
        }
        
        for _ in range(30): # Poll for up to 60 seconds
            response = requests.get(f"{LEONARDO_API_URL}/generations/{generation_id}", headers=headers)
            if response.ok:
                data = response.json().get("generations_by_pk", {})
                status = data.get("status")
                
                if status == "COMPLETE":
                    images = data.get("generated_images", [])
                    if images:
                        return images[0].get("url")
                elif status == "FAILED":
                    return None
            
            time.sleep(2)
        return None
    except Exception as e:
        print(f"[LEONARDO POLL EXCEPTION] {e}")
        return None


@app.route('/api/ai-copilot-generate', methods=['POST'])
def ai_copilot_generate_leonardo():
    """
    GEOMETRY LOCKED AI INTERIOR ENGINE (POWERED BY LEONARDO.AI)
    """
    import random
    import io

    if not LEONARDO_API_KEY:
        return jsonify({'success': False, 'error': 'Leonardo API key not configured'}), 500

    try:
        if 'room_image' not in request.files:
            return jsonify({'success': False, 'error': 'No room image uploaded'}), 400

        room_file = request.files['room_image']
        room_type = request.form.get('room_type', 'bedroom')
        additional_prompt = request.form.get('additional_prompt', '')
        custom_prompt = request.form.get('custom_prompt', '')

        print(f"\n[LEONARDO COPILOT] Starting generation...", flush=True)
        # 1. Image Normalization
        image_bytes = room_file.read()
        nparr = np.frombuffer(image_bytes, np.uint8)
        original_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if original_cv is None:
            return jsonify({'success': False, 'error': 'Invalid image format'}), 400

        # 2. GEOMETRY LOCK (Canny Skeleton)
        skeleton = None
        if geometry_engine:
            print("[LEONARDO COPILOT] Extracting Architectural Skeleton...", flush=True)
            try:
                skeleton = geometry_engine.extract_architectural_skeleton(original_cv)
                # Save Canny debug overlay
                edge_overlay = geometry_engine.create_edge_overlay(original_cv, skeleton)
                edge_path = os.path.join(app.config['UPLOAD_FOLDER'], f"debug_canny_{int(time.time())}.png")
                cv2.imwrite(edge_path, edge_overlay)
                print(f"[LEONARDO COPILOT] Geometry Skeleton Ready. Debug: {edge_path}", flush=True)
            except Exception as e:
                print(f"[WARNING] Canny Edge Extraction failed: {e}", flush=True)

        # 3. SEMANTIC MASKING (Production Engine)
        masks = None
        if segmentation_engine:
            print("[LEONARDO COPILOT] Running Semantic Segmentation...", flush=True)
            try:
                masks = segmentation_engine.generate_masks(original_cv, room_type=room_type, skeleton=skeleton)
                # Save debug mask for verification
                debug_path = os.path.join(app.config['UPLOAD_FOLDER'], f"debug_mask_{int(time.time())}.png")
                cv2.imwrite(debug_path, masks['debug'])
                print(f"[LEONARDO COPILOT] Semantic Masks Ready. Debug: {debug_path}", flush=True)
            except Exception as e:
                print(f"[WARNING] Semantic Segmentation failed: {e}. Falling back to trapezoid.", flush=True)

        # 3. DEPTH ESTIMATION (Spatial Conditioning)
        depth_data = None
        if depth_engine:
            print("[LEONARDO COPILOT] Running Depth Estimation...", flush=True)
            try:
                depth_map = depth_engine.generate_depth_map(original_cv)
                depth_data = depth_engine.analyze_spatial_zones(depth_map)
                
                # Save depth debug overlay
                depth_overlay = depth_engine.create_depth_overlay(original_cv, depth_map)
                depth_path = os.path.join(app.config['UPLOAD_FOLDER'], f"debug_depth_{int(time.time())}.png")
                cv2.imwrite(depth_path, depth_overlay)
                
                print(f"[LEONARDO COPILOT] Depth Analysis Ready. Floor Depth: {depth_data['avg_floor_depth']:.2f}", flush=True)
            except Exception as e:
                print(f"[WARNING] Depth Estimation failed: {e}", flush=True)
        if not masks:
            h, w = original_cv.shape[:2]
            floor_mask = np.zeros((h, w), dtype=np.uint8)
            mask_top = int(h * 0.20)
            pts = np.array([[(int(w * 0.10), mask_top), (int(w * 0.90), mask_top), (w, h), (0, h)]], dtype=np.int32)
            cv2.fillPoly(floor_mask, pts, 255)
            masks = {
                'protected': np.zeros((h, w), dtype=np.uint8), # No protection in fallback
                'editable': floor_mask,
                'alpha': cv2.GaussianBlur(floor_mask.astype(np.float32), (31, 31), 0) / 255.0,
                'debug': np.zeros((h, w, 3), dtype=np.uint8) # Empty black debug image
            }

        # 4. PROMPT ORCHESTRATION
        if room_type == "other":
            selected_prompt = custom_prompt if custom_prompt else "luxury modern interior"
        else:
            prompts = ROOM_PROMPTS.get(room_type, ROOM_PROMPTS["bedroom"])
            selected_prompt = random.choice(prompts)

        # Build a cleaner, non-redundant prompt
        final_prompt = (
            f"Transform this EXACT room into: {selected_prompt}. "
            f"User request: {additional_prompt}."
        )

        # 5. GENERATION & RESTORATION (Production Pipeline)
        print("[LEONARDO COPILOT] Triggering Production Pipeline...", flush=True)
        if generation_engine:
            # The redesign_room method handles: Upload -> Generate -> Poll -> Composite (Restoration)
            final_composite, err = generation_engine.redesign_room(
                original_image=original_cv,
                style_prompt=final_prompt,
                masks=masks,
                image_strength=0.3,
                depth_data=depth_data # Pass depth metadata for spatial anchoring
            )
            
            if err:
                return jsonify({'success': False, 'error': f"Generation Pipeline Error: {err}"}), 500
                
            # Upload final result to R2
            _, buffer = cv2.imencode('.png', final_composite)
            public_url, upload_err = upload_to_r2(buffer.tobytes(), f"results/copilot_{int(time.time())}.png")
            
            if upload_err:
                return jsonify({'success': False, 'error': f"Result upload failed: {upload_err}"}), 500

            return jsonify({
                'success': True,
                'result_url': public_url,
                'message': 'AI room generated successfully via Production Pipeline',
                'room_type': room_type
            })
        else:
            return jsonify({'success': False, 'error': 'Generation Engine not initialized'}), 500

    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


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
