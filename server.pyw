import os
import sys
import uuid
import shutil
import requests
import pandas as pd
import numpy as np
import cv2
import librosa
import uvicorn
import threading
import webview
import time
import hashlib
import secrets
from datetime import datetime
import subprocess
import sqlite3
import asyncio
import aiosqlite
import json
import html
import gc
import re
import logging
import logging.handlers
from typing import Optional, Dict, List, Union
from pathlib import Path
import traceback
from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException
from pydantic import BaseModel, Field
from pydantic import ConfigDict
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import platform
import smtplib
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from cryptography.fernet import Fernet

# --- COMPETITOR ANALYSIS LIBRARY ---
try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False

# --- VISUAL INTELLIGENCE LIBRARIES (Phase 3) ---
try:
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
except ImportError:
    DEEPFACE_AVAILABLE = False

try:
    from colorthief import ColorThief
    COLORTHIEF_AVAILABLE = True
except ImportError:
    COLORTHIEF_AVAILABLE = False


# ═══════════════════════════════════════════════════════════
# LOGGING & ERROR MANAGEMENT (SaaS Level)
# ═══════════════════════════════════════════════════════════
# PyInstaller EXE compatible crossroads
if getattr(sys, 'frozen', False):
    # In EXE mode: APP_DIR = side of exe (writable), BUNDLE_DIR = inside bundle (read only)
    APP_DIR = Path(os.path.dirname(sys.executable)).resolve()
    BUNDLE_DIR = Path(sys._MEIPASS).resolve()
else:
    APP_DIR = Path(os.path.dirname(os.path.abspath(__file__))).resolve()
    BUNDLE_DIR = APP_DIR

# Compatibility with legacy code
BASE_DIR = APP_DIR
os.chdir(APP_DIR)

# log directory
LOGS_DIR = APP_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# ═══════════════════════════════════════════════════════════
# SECURITY SERVICE (app/services/security.py)
# ═══════════════════════════════════════════════════════════
from app.services.security import CryptoManager, hash_password, verify_password, generate_verification_code, CryptoDecryptionError


# Main application logger
app_logger = logging.getLogger("yt_analiz")
app_logger.setLevel(logging.DEBUG)

# File handler (public server log)
_main_handler = logging.handlers.RotatingFileHandler(
    str(LOGS_DIR / "server.log"), maxBytes=5*1024*1024, backupCount=3, encoding="utf-8"
)
_main_handler.setFormatter(logging.Formatter(
    "[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
))
app_logger.addHandler(_main_handler)

# Console handler disabled (to prevent Unicode error)
# _console_handler = logging.StreamHandler()
# _console_handler.setLevel(logging.INFO)
# _console_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
# app_logger.addHandler(_console_handler)

# Crash log file (legacy compatibility)
LOG_FILE = str(LOGS_DIR / "crash.log")

_user_loggers: Dict[int, logging.Logger] = {}

def get_user_logger(user_id: int) -> logging.Logger:
    """Returns a per-user logger. Writes to logs/user_X.log."""
    if user_id in _user_loggers:
        return _user_loggers[user_id]
    logger = logging.getLogger(f"yt_analiz.user_{user_id}")
    logger.setLevel(logging.DEBUG)
    handler = logging.handlers.RotatingFileHandler(
        str(LOGS_DIR / f"user_{user_id}.log"), maxBytes=5*1024*1024, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter(
        f"[%(asctime)s] [%(levelname)s] [user_id={user_id}] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(handler)
    _user_loggers[user_id] = logger
    return logger


def log_exception(exc_type, exc_value, exc_traceback):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n--- ERROR TIME: {time.ctime()} ---\n")
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
    app_logger.critical(f"Unhandled exception: {exc_value}", exc_info=(exc_type, exc_value, exc_traceback))


sys.excepthook = log_exception
try:
    sys.stdout = open(str(LOGS_DIR / "stdout.log"), "a", encoding="utf-8")
    sys.stderr = sys.stdout
except Exception as e:
    app_logger.error(f"Error [stdout_redirect]: {str(e)}", exc_info=True)

templates_dir = str(BUNDLE_DIR / "templates")
static_dir = str(BUNDLE_DIR / "static")
output_dir = APP_DIR / "shorts_output"

# --- DATABASE LAYER (app/database/db.py) ---
from app.database.db import db_path, get_db, get_async_db, init_db, migrate_data


temp_dir = APP_DIR / "temp_videos"
temp_dir.mkdir(exist_ok=True)

# In EXE mode templates/static is already in the package; Build in development mode
if not getattr(sys, 'frozen', False):
    Path(templates_dir).mkdir(exist_ok=True)
    Path(static_dir).mkdir(exist_ok=True)
output_dir.mkdir(exist_ok=True)

def _load_pdf_lang():
    try:
        # translations.xlsx can be in both BUNDLE_DIR and APP_DIR
        xlsx_path = BUNDLE_DIR / 'translations.xlsx'
        if not xlsx_path.exists():
            xlsx_path = APP_DIR / 'translations.xlsx'
        df = pd.read_excel(str(xlsx_path), sheet_name='pdf', dtype=str).fillna('')
        result = {}
        for _, row in df.iterrows():
            key = str(row['key']).strip()
            if not key:
                continue
            for lang in ['tr', 'en', 'es']:
                if lang not in result:
                    result[lang] = {}
                result[lang][key] = str(row[lang]).strip()
        # Set up the comparison_headers list specifically
        for lang_code in ['tr', 'en', 'es']:
            if lang_code in result:
                result[lang_code]['comparison_headers'] = [
                    result[lang_code].get('comparison_headers_metric', 'Metrik'),
                    result[lang_code].get('comparison_headers_this', 'Bu Video'),
                    result[lang_code].get('comparison_headers_avg', 'Eski Ortalaman'),
                    result[lang_code].get('comparison_headers_diff', 'Fark'),
                ]
        return result
    except Exception as e:
        print(f"translations.xlsx could not be read, falling back to empty dict: {e}")
        return {'tr': {}, 'en': {}, 'es': {}}

PDF_LANG = _load_pdf_lang()



# --- PDF FONT INTEGRATION (SAFE) ---
# First look in the project folder, then in the system folders, last resort Helvetica
def _try_register_arial():
    """
    Search order for arial.ttf / arialbd.ttf:
      1. BASE_DIR (project folder)
      2. Windows system fonts folder (C:/Windows/Fonts)
      3. Helvetica fallback
    """
    candidates = [
        (str(BASE_DIR / 'arial.ttf'),    str(BASE_DIR / 'arialbd.ttf')),
    ]
    if platform.system() == 'Windows':
        win_fonts = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts'
        candidates.append((str(win_fonts / 'arial.ttf'), str(win_fonts / 'arialbd.ttf')))

    for reg_path, bold_path in candidates:
        if os.path.isfile(reg_path) and os.path.isfile(bold_path):
            try:
                pdfmetrics.registerFont(TTFont('Arial', reg_path))
                pdfmetrics.registerFont(TTFont('Arial-Bold', bold_path))
                return 'Arial', 'Arial-Bold'
            except Exception:
                pass  # Corrupt font file → go to next step
    return 'Helvetica', 'Helvetica-Bold'

FONT_REGULAR, FONT_BOLD = _try_register_arial()


INDUSTRY_STANDARDS = {
    'gaming': {'tempo': 8.8, 'seo': 7.5, 'retention': 4.5},
    'education': {'tempo': 4.5, 'seo': 9.5, 'retention': 7.0},
    'vlog': {'tempo': 7.5, 'seo': 6.5, 'retention': 5.5},
    'finance': {'tempo': 5.0, 'seo': 8.5, 'retention': 6.5},
    'shorts': {'tempo': 9.5, 'seo': 5.0, 'retention': 8.5},
    'default': {'tempo': 7.0, 'seo': 8.0, 'retention': 6.0}
}

FFMPEG_AVAILABLE = False


def run_cmd(cmd_list, timeout=None):
    kwargs = {'stdout': subprocess.DEVNULL, 'stderr': subprocess.DEVNULL}
    if os.name == 'nt':
        kwargs['creationflags'] = 0x08000000
    return subprocess.run(cmd_list, check=True, timeout=timeout, **kwargs)


FFMPEG_AVAILABLE = False
GPU_CODEC = "libx264"  # default CPU codec

def detect_gpu_codec():
    """
    Tries NVIDIA, AMD, and Intel GPU codecs in order.
    Returns the first working one; falls back to libx264 (CPU) if none work.
    """
    candidates = [
        ("h264_nvenc", "NVIDIA"),
        ("h264_amf", "AMD"),
        ("h264_qsv", "Intel"),
    ]
    for codec, brand in candidates:
        try:
            test_cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", "nullsrc=s=64x64:d=1",
                "-c:v", codec,
                "-f", "null", "-"
            ]
            result = subprocess.run(
                test_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=8,
                creationflags=0x08000000 if os.name == 'nt' else 0
            )
            if result.returncode == 0:
                print(f"✅ GPU Codec found: {codec} ({brand})")
                return codec
        except Exception:
            pass
    print("ℹ️ No GPU codec found, falling back to CPU (libx264).")
    return "libx264"


def check_ffmpeg():
    global FFMPEG_AVAILABLE, GPU_CODEC
    try:
        run_cmd(["ffmpeg", "-version"], timeout=5)
        FFMPEG_AVAILABLE = True
        GPU_CODEC = detect_gpu_codec()
    except Exception as e:
        app_logger.error(f"Error [check_ffmpeg]: FFmpeg not found or could not be executed. {e}")
        FFMPEG_AVAILABLE = False


check_ffmpeg()


# ═══════════════════════════════════════════════════════════
# HARDWARE / PERFORMANCE AUTO-PILOT
# ═══════════════════════════════════════════════════════════
SYSTEM_CAPS = {
    "cpu_cores": 1,
    "cpu_brand": "",
    "gpu_codec": "libx264",
    "cuda_available": False,
    "cuda_devices": 0,
    "optimal_threads": 2,
    "ram_gb": 0,
    "platform": platform.system(),
    "fast_mode": False,
}


def detect_system_capabilities():
    """Detects hardware profile at system startup."""
    global SYSTEM_CAPS
    # CPU
    cpu_count = os.cpu_count() or 1
    SYSTEM_CAPS["cpu_cores"] = cpu_count
    SYSTEM_CAPS["cpu_brand"] = platform.processor() or "Unknown"
    SYSTEM_CAPS["gpu_codec"] = GPU_CODEC
    SYSTEM_CAPS["optimal_threads"] = max(2, cpu_count - 1)

    # RAM (platform independent, without psutil)
    try:
        if platform.system() == "Windows":
            import ctypes
            kernel32 = ctypes.windll.kernel32
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            mem = MEMORYSTATUSEX()
            mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
            SYSTEM_CAPS["ram_gb"] = round(mem.ullTotalPhys / (1024**3), 1)
    except Exception:
        pass

    # CUDA (OpenCV)
    try:
        cuda_count = cv2.cuda.getCudaEnabledDeviceCount()
        if cuda_count > 0:
            SYSTEM_CAPS["cuda_available"] = True
            SYSTEM_CAPS["cuda_devices"] = cuda_count
    except Exception:
        pass

    # Fast mode: Use aggressive settings if you have 8+ cores or GPU codecs
    SYSTEM_CAPS["fast_mode"] = (cpu_count >= 8 or GPU_CODEC != "libx264")

    app_logger.info(
        f"🖥️ System profile: CPU={cpu_count} cores, RAM={SYSTEM_CAPS['ram_gb']}GB, "
        f"GPU={GPU_CODEC}, CUDA={'✅' if SYSTEM_CAPS['cuda_available'] else '❌'}, "
        f"Fast Mode={'ON' if SYSTEM_CAPS['fast_mode'] else 'OFF'}"
    )


detect_system_capabilities()


# ═══════════════════════════════════════════════════════════
# AI SERVICE (app/services/ai_service.py)
# ═══════════════════════════════════════════════════════════
from app.services.ai_service import (
    get_groq_api_key,
    generate_ai_game_feedback,
    analyze_image_with_gemini,
    ADVISORY_TONE_RULE,
    ADVISORY_TONE_RULE_CREATIVE,
)


# ═══════════════════════════════════════════════════════════
# E-MAIL SERVICE (app/services/email_service.py)
# ═══════════════════════════════════════════════════════════
from app.services.email_service import send_verification_email, send_report_email


# init_db and migrate_data → imported from app/database/db.py (PHASE 1)
init_db()


# ═══════════════════════════════════════════════════════════
# COMPETITOR ANALYSIS SERVICE (app/services/competitor.py)
# ═══════════════════════════════════════════════════════════
from app.services.competitor import (
    extract_core_keywords,
    compute_kill_switch,
    CompetitorAnalyzer,
    check_content_consistency,
    COMPETITOR_FOUND_STATUSES,
    COMPETITOR_LOOKUP_FAILED,
)


def cleanup_temp_videos():
    try:
        now = time.time()
        for f in temp_dir.glob("v_*.mp4"):
            if now - f.stat().st_mtime > 10800:
                try:
                    f.unlink()
                except Exception as e:
                    app_logger.warning(f"Error [cleanup_temp_videos]: {f} could not be deleted: {e}")
    except Exception as e:
        app_logger.error(f"Error [cleanup_temp_videos] general error: {e}")



# ═══════════════════════════════════════════════════════════
# ANALYSIS ENGINE (app/services/analysis_engine.py)
# ═══════════════════════════════════════════════════════════
from app.services.analysis_engine import INDUSTRY_STANDARDS, AnalysisEngine


def get_dynamic_timeout(video_path: str, min_timeout: int = 120) -> Optional[int]:
    """
    Calculates a dynamic FFmpeg timeout based on video duration.
    Rule: max(min_timeout, video_duration * 2)
    Provides sufficient margin even for 20GB+ files.
    Returns None if duration cannot be determined (no timeout).
    """
    try:
        probe_cmd = ["ffmpeg", "-i", video_path, "-hide_banner"]
        probe_kwargs = {'capture_output': True, 'text': True, 'timeout': 10}
        if os.name == 'nt':
            probe_kwargs['creationflags'] = 0x08000000
        result = subprocess.run(probe_cmd, **probe_kwargs)
        match = re.search(r'Duration:\s*(\d+):(\d+):(\d+)', result.stderr)
        if match:
            h, m, s = int(match.group(1)), int(match.group(2)), int(match.group(3))
            duration_sec = h * 3600 + m * 60 + s
            return max(min_timeout, duration_sec * 2)
    except Exception:
        pass
    return None


def _copy_uploads(video_file_obj, csv_file_obj, thumb_file_obj, v_path, c_path, t_path):
    """Copies uploaded files to disk (intended to run inside a threadpool)."""
    with open(v_path, "wb") as f:
        shutil.copyfileobj(video_file_obj, f)
    if csv_file_obj and c_path:
        with open(c_path, "wb") as f:
            shutil.copyfileobj(csv_file_obj, f)
    if thumb_file_obj and t_path:
        with open(t_path, "wb") as f:
            shutil.copyfileobj(thumb_file_obj, f)


app = FastAPI(title="YouTube Analiz Pro V4.0 — SaaS Edition")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# ── Log Pydantic 422 Validation error details ──────────────────────────
from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Logs 422 Pydantic validation errors and returns a meaningful JSON response."""
    try:
        body = await request.body()
        body_str = body.decode('utf-8', errors='replace')
    except Exception:
        body_str = "<unreadable>"
    app_logger.error(
        f"[VALIDATION ERROR] endpoint={request.url.path}\n"
        f"  Incoming body: {body_str}\n"
        f"  Validation errors: {exc.errors()}"
    )
    return JSONResponse(
        status_code=422,
        content={
            "error": "The submitted data format is invalid.",
            "detail": exc.errors(),
            "body": body_str
        }
    )

@app.exception_handler(CryptoDecryptionError)
async def crypto_exception_handler(request: Request, exc: CryptoDecryptionError):
    """
    Fail-Fast (Phase 1) Rule: Silently returning an empty string when decryption fails is FORBIDDEN.
    This global handler returns an honest 500 error with a meaningful message
    whenever a CryptoDecryptionError is raised in any API endpoint.
    """
    app_logger.error(f"[CRYPTO_ERROR] endpoint={request.url.path} message={str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "CRYPTO_ERROR",
            "details": str(exc),
            "detail": str(exc)  # Some frontend fetches may look for "detail"
        }
    )
# Static files and Template engine (PyInstaller BUNDLE_DIR compatible)
app.mount("/static", StaticFiles(directory=static_dir), name="static")
app.mount("/shorts", StaticFiles(directory=str(output_dir)), name="shorts")
templates = Jinja2Templates(directory=templates_dir)


# ═══════════════════════════════════════════════════════════
# GLOBAL ERROR MANAGER (SaaS Level)
# ═══════════════════════════════════════════════════════════
@app.middleware("http")
async def global_error_handler(request: Request, call_next):
    """Catches all unexpected errors and returns an error code to the user."""
    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        error_code = str(uuid.uuid4())[:8].upper()
        # Try to extract the user ID
        user_id = 0
        try:
            if request.method == "POST":
                body = await request.body()
                if b"user_id" in body:
                    import urllib.parse
                    parsed = urllib.parse.parse_qs(body.decode("utf-8", errors="ignore"))
                    user_id = int(parsed.get("user_id", ["0"])[0])
        except Exception as parse_e:
            app_logger.debug(f"User ID parse error in middleware: {parse_e}")
        # logging
        app_logger.error(
            f"[ERR-{error_code}] endpoint={request.url.path} user_id={user_id} — {type(exc).__name__}: {exc}",
            exc_info=True
        )
        if user_id > 0:
            get_user_logger(user_id).error(
                f"[ERR-{error_code}] endpoint={request.url.path} — {type(exc).__name__}: {exc}",
                exc_info=True
            )
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Something went wrong. Error code: {error_code}. Please send this code to the support team.",
                "error_code": error_code
            }
        )


# ═══════════════════════════════════════════════════════════
# GOOGLE LOGIN INFRASTRUCTURE
# ═══════════════════════════════════════════════════════════
@app.get("/api/auth/google/url")
async def google_auth_url():
    """Generates the Google OAuth2 authorization URL."""
    try:
        db = await get_async_db()
        try:
            async with db.execute("SELECT value FROM app_settings WHERE key='google_client_id'") as cursor:
                row = await cursor.fetchone()
            client_id = row[0] if row else ""
            async with db.execute("SELECT value FROM app_settings WHERE key='google_redirect_uri'") as cursor:
                row = await cursor.fetchone()
            redirect_uri = row[0] if row else "http://127.0.0.1:8000/api/auth/google/callback"
        finally:
            await db.close()

        if not client_id:
            return {"error": "Google Client ID is not configured. Please add it from the Settings page."}

        scope = "openid email profile"
        auth_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={client_id}&redirect_uri={redirect_uri}&response_type=code"
            f"&scope={scope}&access_type=offline&prompt=consent"
        )
        return {"url": auth_url}
    except Exception as e:
        app_logger.error(f"Google auth URL creation error: {e}", exc_info=True)
        return {"error": "Google auth URL could not be created."}


@app.get("/api/auth/google/callback")
async def google_auth_callback(code: str = ""):
    """Google OAuth2 callback — token exchange and user creation/login."""
    if not code:
        return HTMLResponse("<h2>Error: Authorization code could not be retrieved.</h2>")
    try:
        db = await get_async_db()
        try:
            async with db.execute("SELECT key, value FROM app_settings WHERE key IN ('google_client_id', 'google_client_secret', 'google_redirect_uri')") as cursor:
                settings = {row[0]: row[1] async for row in cursor}

            client_id = settings.get('google_client_id', '')
            client_secret = settings.get('google_client_secret', '')
            redirect_uri = settings.get('google_redirect_uri', 'http://127.0.0.1:8000/api/auth/google/callback')

            if not client_id or not client_secret:
                return HTMLResponse("<h2>Google OAuth configuration is incomplete.</h2>")

            # token exchange
            token_resp = requests.post("https://oauth2.googleapis.com/token", data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code"
            }, timeout=10)

            if token_resp.status_code != 200:
                app_logger.error(f"Google token exchange error: {token_resp.text}")
                return HTMLResponse("<h2>Sign-in with Google failed.</h2>")

            token_data = token_resp.json()
            access_token = token_data.get("access_token", "")

            # Get user information
            user_info_resp = requests.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10
            )
            if user_info_resp.status_code != 200:
                return HTMLResponse("<h2>Google user information could not be retrieved.</h2>")

            guser = user_info_resp.json()
            google_id = guser.get("id", "")
            email = guser.get("email", "")
            name = guser.get("name", email.split("@")[0] if email else "GoogleUser")
            profile_pic = guser.get("picture", "")

            # Check if there are users
            async with db.execute("SELECT id, username FROM users WHERE google_id=?", (google_id,)) as cursor:
                existing = await cursor.fetchone()

            if existing:
                user_id = existing[0]
                username = existing[1]
                await db.execute(
                    "UPDATE users SET access_token=?, profile_pic=? WHERE id=?",
                    (access_token, profile_pic, user_id)
                )
            else:
                # Create unique username
                base_username = re.sub(r'[^a-zA-Z0-9_]', '', name)[:20] or "user"
                username = base_username
                counter = 1
                while True:
                    async with db.execute("SELECT id FROM users WHERE username=?", (username,)) as cursor:
                        if not await cursor.fetchone():
                            break
                    username = f"{base_username}_{counter}"
                    counter += 1

                await db.execute(
                    "INSERT INTO users (username, password_hash, email, is_verified, profile_pic, google_id, access_token, auth_provider) VALUES (?, '', ?, 1, ?, ?, ?, 'google')",
                    (username, email, profile_pic, google_id, access_token)
                )
                await db.commit()
                async with db.execute("SELECT last_insert_rowid()") as cursor:
                    row = await cursor.fetchone()
                    user_id = row[0]

            await db.commit()
        finally:
            await db.close()

        # Create session and redirect
        session_json = json.dumps({"user_id": user_id, "username": username})
        db_session = await get_async_db()
        try:
            await db_session.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES ('active_session', ?)", (session_json,))
            await db_session.commit()
        finally:
            await db_session.close()

        app_logger.info(f"✅ Google login successful: user_id={user_id}, username={username}")
        # XSS protection: json.dumps uses double quotes, preventing single quote injection
        import json as _json
        session_json_safe = _json.dumps(session_json)  # JSON string wrapped in double quotes
        return HTMLResponse(f"""
            <html><body>
            <script>
                localStorage.setItem('yt_user', {session_json_safe});
                window.location.href = '/';
            </script>
            <p>Logging in...</p>
            </body></html>
        """)
    except Exception as e:
        app_logger.error(f"Google auth callback error: {e}", exc_info=True)
        return HTMLResponse("<h2>An error occurred during Google sign-in.</h2>")


@app.post("/api/settings/google_oauth")
async def save_google_oauth(request: Request):
    """Save Google OAuth Client ID and Secret."""
    try:
        data = await request.json()
        client_id = data.get("client_id", "").strip()
        client_secret = data.get("client_secret", "").strip()
        redirect_uri = data.get("redirect_uri", "http://127.0.0.1:8000/api/auth/google/callback").strip()

        if not client_id or not client_secret:
            return {"success": False, "error": "Client ID and Secret cannot be empty."}

        db = await get_async_db()
        try:
            await db.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES ('google_client_id', ?)", (client_id,))
            await db.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES ('google_client_secret', ?)", (client_secret,))
            await db.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES ('google_redirect_uri', ?)", (redirect_uri,))
            await db.commit()
        finally:
            await db.close()
        return {"success": True}
    except Exception as e:
        app_logger.error(f"Google OAuth settings save error: {e}")
        return {"success": False, "error": "Save error."}


@app.post("/create_channel")
async def create_channel(
    name: str = Form(...),
    content_type: str = Form(""),
    target_audience: str = Form(""),
    purpose: str = Form(""),
    channel_rules: str = Form(""),
    user_id: int = Form(1)
):
    try:
        db = await get_async_db()
        try:
            cursor = await db.execute("INSERT INTO channels (name, content_type, target_audience, purpose, channel_rules, user_id) VALUES (?, ?, ?, ?, ?, ?)",
                      (name, content_type, target_audience, purpose, channel_rules, user_id))
            await db.commit()
            channel_id = cursor.lastrowid
            return {"success": True, "channel_id": channel_id, "name": name}
        finally:
            await db.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/auth/register")
async def register(request: Request):
    try:
        data = await request.json()
        username = data.get("username", "").strip()
        password = data.get("password", "")
        email = data.get("email", "").strip()
        lang = data.get("lang", "tr")

        if not username or len(username) < 3:
            return {"error": "Username must be at least 3 characters long."}
        if not password or len(password) < 6:
            return {"error": "Password must be at least 6 characters long."}
        if " " in username:
            return {"error": "Username cannot contain spaces."}
        if not email or "@" not in email:
            return {"error": "Please enter a valid email address."}

        pw_hash = hash_password(password)
        db = await get_async_db()
        try:
            try:
                cursor = await db.execute("INSERT INTO users (username, password_hash, email, is_verified) VALUES (?, ?, ?, 0)",
                          (username, pw_hash, email))
                await db.commit()
                user_id = cursor.lastrowid
            except sqlite3.IntegrityError:
                return {"error": "This username is already taken."}

            # Generate verification code
            code = generate_verification_code()
            from datetime import timedelta
            expires_at = (datetime.now() + timedelta(minutes=15)).strftime('%Y-%m-%d %H:%M:%S')
            await db.execute("INSERT INTO email_verifications (user_id, code, expires_at) VALUES (?, ?, ?)",
                      (user_id, code, expires_at))
            await db.commit()
        finally:
            await db.close()

        print(f"SENDING EMAIL: {email}, code: {code}")
        mail_sent = send_verification_email(email, code, lang)
        print(f"MAIL SONUCU: {mail_sent}")
        return {
            "success": True,
            "user_id": user_id,
            "username": username,
            "needs_verification": True,
            "mail_sent": mail_sent,
            "email": email
        }
    except Exception:
        traceback.print_exc()
        return {"error": "An unexpected error occurred during registration."}


@app.post("/api/auth/login")
async def login(request: Request):
    try:
        data = await request.json()
        username = data.get("username", "").strip()
        password = data.get("password", "")
        if not username or not password:
            return {"error": "Username and password cannot be empty."}
        db = await get_async_db()
        try:
            async with db.execute("SELECT id, password_hash, is_verified, email FROM users WHERE username=?", (username,)) as cursor:
                row = await cursor.fetchone()
        finally:
            await db.close()
        
        if not row:
            return {"error": "User not found."}
        user_id, stored_hash, is_verified, user_email = row
        if not stored_hash:
            return {"error": "Cannot sign in to this account."}
        if not verify_password(password, stored_hash):
            return {"error": "Incorrect password."}
        if is_verified == 0 and user_email:
            return {"error": "EMAIL_NOT_VERIFIED", "email": user_email, "user_id": user_id}
        return {"success": True, "user_id": user_id, "username": username}
    except Exception:
        traceback.print_exc()
        return {"error": "An unexpected error occurred during login."}


@app.post("/api/auth/verify")
async def verify_email(request: Request):
    try:
        data = await request.json()
        user_id = data.get("user_id")
        code = data.get("code", "").strip()

        if not user_id or not code:
            return {"error": "Missing information."}

        db = await get_async_db()
        try:
            async with db.execute("""SELECT id, expires_at, verified FROM email_verifications
                         WHERE user_id=? AND code=?
                         ORDER BY created_at DESC LIMIT 1""", (user_id, code)) as cursor:
                row = await cursor.fetchone()

            if not row:
                return {"error": "Incorrect code."}

            ver_id, expires_at, verified = row
            if verified:
                return {"error": "This code has already been used."}

            if datetime.now() > datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S'):
                return {"error": "The code has expired. Please register again."}

            await db.execute("UPDATE users SET is_verified=1 WHERE id=?", (user_id,))
            await db.execute("UPDATE email_verifications SET verified=1 WHERE id=?", (ver_id,))
            await db.commit()

            async with db.execute("SELECT username FROM users WHERE id=?", (user_id,)) as cursor:
                urow = await cursor.fetchone()

            return {"success": True, "user_id": user_id, "username": urow[0] if urow else ""}
        finally:
            await db.close()
    except Exception:
        traceback.print_exc()
        return {"error": "An error occurred during verification."}


@app.post("/api/auth/resend")
async def resend_verification(request: Request):
    try:
        data = await request.json()
        user_id = data.get("user_id")
        lang = data.get("lang", "tr")

        db = await get_async_db()
        try:
            async with db.execute("SELECT email FROM users WHERE id=?", (user_id,)) as cursor:
                row = await cursor.fetchone()
            if not row:
                return {"error": "User not found."}

            email = row[0]
            code = generate_verification_code()
            from datetime import timedelta
            expires_at = (datetime.now() + timedelta(minutes=15)).strftime('%Y-%m-%d %H:%M:%S')
            await db.execute("INSERT INTO email_verifications (user_id, code, expires_at) VALUES (?, ?, ?)",
                      (user_id, code, expires_at))
            await db.commit()
        finally:
            await db.close()

        mail_sent = send_verification_email(email, code, lang)
        return {"success": True, "mail_sent": mail_sent}
    except Exception:
        traceback.print_exc()
        return {"error": "Code could not be sent."}


@app.get("/api/profile")
async def get_profile(user_id: int = 1):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id, username, created_at FROM users WHERE id=?", (user_id,))
        row = c.fetchone()
        if not row:
            conn.close()
            return {"error": "User not found."}
        uid, uname, created = row
        c.execute("SELECT COUNT(*) FROM channels WHERE user_id=?", (uid,))
        channel_count = c.fetchone()[0]
        c.execute("""SELECT COUNT(*), AVG(a.overall_score) FROM analyses a
                    JOIN channels ch ON a.channel_id = ch.id WHERE ch.user_id=?""", (uid,))
        analysis_row = c.fetchone()
        analysis_count = analysis_row[0] or 0
        avg_score = round(analysis_row[1], 1) if analysis_row[1] else 0.0
        c.execute("""SELECT a.id, a.video_name, a.overall_score, a.timestamp, ch.name
                    FROM analyses a JOIN channels ch ON a.channel_id = ch.id
                    WHERE ch.user_id=? ORDER BY a.timestamp DESC""", (uid,))
        recent = [{"id": r[0], "video": r[1], "score": r[2], "date": r[3], "channel": r[4]} for r in c.fetchall()]
        conn.close()
        return {"user_id": uid, "username": uname, "created_at": created,
                "channel_count": channel_count, "analysis_count": analysis_count,
                "avg_score": avg_score, "recent_analyses": recent}
    except Exception:
        traceback.print_exc()
        return {"error": "An error occurred while loading the profile."}


@app.get("/api/analyses/{analysis_id}")
async def get_analysis_by_id(analysis_id: int):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT a.id, a.video_name, a.overall_score, a.retention_score, a.tech_score,
                        a.seo_score, a.thumb_score, a.peaks, a.viral_score, a.coach_feedback,
                        a.competitor_data, a.video_description, a.video_tags, a.timestamp, ch.name
                    FROM analyses a JOIN channels ch ON a.channel_id = ch.id
                    WHERE a.id=?""", (analysis_id,))
        row = c.fetchone()
        conn.close()
        if not row:
            return {"error": "Analysis not found."}
        return {
            "analysis_id": row[0],
            "video_name": row[1],
            "overall_score": row[2],
            "retention_score": row[3],
            "tech_score": row[4],
            "seo_score": row[5],
            "thumb_score": row[6] if row[6] is not None else 0,
            "peaks": row[7],
            "viral_score": row[8],
            "coach_feedback": row[9],
            "competitor_data": row[10],
            "video_description": row[11],
            "video_tags": row[12],
            "timestamp": row[13],
            "channel_name": row[14],
            "is_history": True
        }
    except Exception:
        traceback.print_exc()
        return {"error": "An error occurred while loading the analysis."}


@app.delete("/api/analyses/{analysis_id}")
async def delete_analysis(analysis_id: int):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM analyses WHERE id=?", (analysis_id,))
        conn.commit()
        conn.close()
        return {"success": True}
    except Exception:
        traceback.print_exc()
        return {"success": False, "error": "Delete operation failed."}


@app.get("/api/settings/gemini")
async def get_gemini_key():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT value FROM app_settings WHERE key='gemini_api_key'")
    row = c.fetchone()
    conn.close()
    decrypted = CryptoManager.decrypt(row[0]) if row and row[0] else ""
    return {"has_key": bool(decrypted), "key": decrypted}


@app.post("/api/settings/gemini")
async def set_gemini_key(key: str = Form(...)):
    key = key.strip()
    if key == "(saved)":
        return {"success": True}
    if not key:
        return {"success": False, "error": "Invalid Gemini API Key"}
    try:
        test_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        resp = requests.get(test_url, timeout=5)
        if resp.status_code != 200:
            return {"success": False, "error": "Invalid Gemini API Key"}
    except requests.exceptions.RequestException:
        return {"success": False, "error": "Could not connect to Gemini API"}
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES ('gemini_api_key', ?)", (CryptoManager.encrypt(key),))
    conn.commit()
    conn.close()
    return {"success": True}


@app.post("/api/content_finder")
async def content_finder(request: Request):
    try:
        data = await request.json()
        keyword = data.get("keyword", "").strip()
        lang = data.get("lang", "tr")  
        user_id = data.get("user_id", 1)
        if not keyword:
            return {"error": "Please enter a keyword or concept to search for."}
        if not YT_DLP_AVAILABLE:
            return {"error": "yt-dlp is not installed, search is unavailable."}

        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'skip_download': True,
            'max_downloads': 5,
            'socket_timeout': 15,
        }
        search_query = f"ytsearch5:{keyword}"
        videos = []
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_query, download=False)
                if not info or 'entries' not in info or not info['entries']:
                    return {"error": f"No search results found for '{keyword}'."}
                for entry in info['entries']:
                    if not entry:
                        continue
                    views = entry.get('view_count') or 0
                    raw_date = str(entry.get('upload_date', ''))
                    days_passed = 1
                    if raw_date and len(raw_date) == 8:
                        try:
                            d = datetime.strptime(raw_date, '%Y%m%d')
                            days_passed = max(1, (datetime.now() - d).days)
                        except Exception as e:
                            app_logger.debug(f"Error [content_finder date parse]: {e}")
                    view_velocity = views / days_passed if views > 0 else 0
                    videos.append({
                        'id': entry.get('id', ''),
                        'title': entry.get('title', 'Bilinmiyor'),
                        'channel': entry.get('uploader', 'Rakip'),
                        'views': views,
                        'days_passed': days_passed,
                        'view_velocity': round(view_velocity, 1),
                        'url': f"https://youtube.com/watch?v={entry.get('id', '')}",
                        'is_outlier': False
                    })
        except Exception as e:
            traceback.print_exc()
            return {"error": f"Error during YouTube search: {str(e)[:100]}"}

        if not videos:
            return {"error": "No videos found in search results."}

        avg_velocity = sum(v['view_velocity'] for v in videos) / len(videos)
        outliers = []
        for v in videos:
            if avg_velocity > 0 and v['view_velocity'] > (avg_velocity * 1.5):
                v['is_outlier'] = True
                outliers.append(v)
        if not outliers and videos:
            top = max(videos, key=lambda x: x['view_velocity'])
            top['is_outlier'] = True
            outliers.append(top)

        ai_ideas = []
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT key, value FROM app_settings WHERE key IN ('groq_api_key', 'gemini_api_key')")
        api_keys = {row[0]: row[1] for row in c.fetchall()}
        groq_api_key = api_keys.get('groq_api_key', '')
        gemini_api_key = api_keys.get('gemini_api_key', '')

        if (groq_api_key or gemini_api_key) and outliers:
            outlier_titles = [v['title'] for v in outliers[:3]]

            lang_prompts = {
                "tr": f"""Kullanıcı '{keyword}' konseptinde YouTube videoları çekiyor.
Şu an algoritmayı domine eden patlamış video başlıkları:
{json.dumps(outlier_titles, ensure_ascii=False)}

3 YEPYENİ VİDEO FİKRİ üret. Her fikir için:
1. "title": Merak uyandıran başlık
2. "hook": İlk 5 saniyede söylenecek kanca cümle
3. "thumbnail": Thumbnail tasarım önerisi

SADECE JSON Array döndür, Türkçe yaz:
[{{"title":"...","hook":"...","thumbnail":"..."}}]""",

                "en": f"""The user is making YouTube videos about '{keyword}'.
Currently trending video titles dominating the algorithm:
{json.dumps(outlier_titles, ensure_ascii=False)}

Generate 3 BRAND NEW VIDEO IDEAS. For each idea provide:
1. "title": A curiosity-inducing title
2. "hook": Opening sentence for the first 5 seconds
3. "thumbnail": Thumbnail design suggestion

Return ONLY a JSON Array, answer in English:
[{{"title":"...","hook":"...","thumbnail":"..."}}]""",

                "es": f"""El usuario está haciendo videos de YouTube sobre '{keyword}'.
Títulos de videos virales que dominan el algoritmo actualmente:
{json.dumps(outlier_titles, ensure_ascii=False)}

Genera 3 IDEAS DE VIDEO NUEVAS. Para cada idea proporciona:
1. "title": Un título que genere curiosidad
2. "hook": Frase de apertura para los primeros 5 segundos
3. "thumbnail": Sugerencia de diseño de miniatura

Devuelve SOLO un Array JSON, responde en Español:
[{{"title":"...","hook":"...","thumbnail":"..."}}]"""
            }

            prompt = lang_prompts.get(lang, lang_prompts["en"]) + f"\n\n{ADVISORY_TONE_RULE_CREATIVE}"

            
            if groq_api_key:

                try:
                    resp = requests.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={"Authorization": f"Bearer {groq_api_key}", "Content-Type": "application/json"},
                        json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}],
                              "temperature": 0.7, "max_tokens": 800},
                        timeout=20
                    )
                    if resp.status_code == 200:
                        ai_text = resp.json()["choices"][0]["message"]["content"]
                        if "```json" in ai_text:
                            ai_text = ai_text.split("```json")[1].split("```")[0]
                        elif "```" in ai_text:
                            ai_text = ai_text.split("```")[1].split("```")[0]
                        match = re.search(r'\[.*\]', ai_text, re.DOTALL)
                        if match:
                            ai_ideas = json.loads(match.group(), strict=False)
                except Exception:
                    traceback.print_exc()

        try:
            c.execute("INSERT INTO content_ideas (user_id, keyword, generated_ideas_json, search_results_json) VALUES (?, ?, ?, ?)",
                      (user_id, keyword, json.dumps(ai_ideas, ensure_ascii=False), json.dumps(videos, ensure_ascii=False)))
            conn.commit()
        except Exception as e:
            app_logger.error(f"Error [content_finder db save]: {e}")
        conn.close()

        return {"success": True, "keyword": keyword, "videos": videos,
                "ai_ideas": ai_ideas, "has_api_key": bool(groq_api_key)}

    except Exception as e:
        traceback.print_exc()
        return {"error": "A server error occurred while running the content finder."}


@app.get("/channels")
async def get_channels(user_id: int = 1):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, name, content_type, target_audience, purpose, channel_rules FROM channels WHERE user_id=? ORDER BY created_at DESC", (user_id,))
    channels = [{"id": row[0], "name": row[1], "content_type": row[2], "target_audience": row[3], "purpose": row[4], "channel_rules": row[5] or ""} for row in c.fetchall()]
    conn.close()
    return channels


@app.delete("/channels/{channel_id}")
async def delete_channel(channel_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM analyses WHERE channel_id=?", (channel_id,))
    c.execute("DELETE FROM channels WHERE id=?", (channel_id,))
    conn.commit()
    conn.close()
    return {"success": True}


@app.put("/channels/{channel_id}")
async def edit_channel(channel_id: int, name: str = Form(...), content_type: str = Form(""), target_audience: str = Form(""), purpose: str = Form(""), channel_rules: str = Form("")):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE channels SET name=?, content_type=?, target_audience=?, purpose=?, channel_rules=? WHERE id=?", (name, content_type, target_audience, purpose, channel_rules, channel_id))
        conn.commit()
        conn.close()
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


@app.post("/analyze")
async def analyze_video(
    video_file: UploadFile = File(...),
    csv_file: Optional[UploadFile] = File(None),
    thumb_file: Optional[UploadFile] = File(None),
    title: str = Form(""),
    description: str = Form(""),
    tags: str = Form(""),
    is_shorts: bool = Form(False),
    pro_mode: bool = Form(False),
    competitor_url: str = Form(""),
    channel_id: int = Form(...),
    user_id: int = Form(1),
    lang: str = Form("tr"),
):
    cleanup_temp_videos()

    uid = str(uuid.uuid4())[:8]
    analysis_start_time = time.time()
    v_path = str(temp_dir / f"v_{uid}.mp4")
    c_path = f"c_{uid}.csv" if csv_file else None
    t_path = f"t_{uid}.png" if thumb_file and not is_shorts else None

    try:
        if not video_file.filename:
            raise HTTPException(status_code=400, detail="No uploaded video file selected.")

        # --- NON-BLOCKING: File copying (heavy I/O) ---
        await run_in_threadpool(
            _copy_uploads,
            video_file.file, csv_file.file if csv_file else None,
            thumb_file.file if thumb_file else None,
            v_path, c_path, t_path
        )

        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT content_type, target_audience, purpose, name FROM channels WHERE id=?", (channel_id,))
        ch_data = c.fetchone()
        conn.close()

        c_type = ch_data[0] if ch_data else "Genel"
        c_aud = ch_data[1] if ch_data else ""
        c_purp = ch_data[2] if ch_data else ""
        ch_name = ch_data[3] if ch_data else ""

        # --- NON-BLOCKING: Heavy CPU/IO analysis operations ---
        tech = await run_in_threadpool(AnalysisEngine.analyze_video_tech, v_path, pro_mode)
        v_tempo = await run_in_threadpool(AnalysisEngine.analyze_visual_tempo, v_path, pro_mode)
        a_tempo = await run_in_threadpool(AnalysisEngine.analyze_audio_per_sec, v_path, pro_mode)
        golden_frame_sec = int(np.argmax(v_tempo)) if v_tempo else 0

        # --- NON-BLOCKING: Scene change and motion analysis (Stage 3) ---
        scene_changes = await run_in_threadpool(
            AnalysisEngine.analyze_scene_changes, v_path, c_type)

        # --- NON-BLOCKING: Competitor analysis (network I/O) ---
        # The rival is a bonus, not a prerequisite. Everything above already cost the
        # user minutes of processing, so a failed or inconclusive lookup only drops
        # the comparison — it never discards the analysis.
        # Duration and format are part of "comparable": a 40-second clip is not a fair
        # rival for a 20-minute video, and vice versa.
        comp_lookup = await run_in_threadpool(
            CompetitorAnalyzer.get_competitor, c_type, tags, competitor_url, ch_name, title,
            tech.get("duration"), is_shorts)
        competitor_status = comp_lookup.get('status', COMPETITOR_LOOKUP_FAILED)
        competitor_data = comp_lookup.get('competitor')
        if competitor_status not in COMPETITOR_FOUND_STATUSES or not competitor_data:
            competitor_data = None
            app_logger.info(
                f"Rakip kıyası atlandı (status={competitor_status}): {comp_lookup.get('detail', '')}")

        # The user's own metadata travels in the same blob: the PDF reads tags,
        # description, thumbnail data and viral segments back out of it, so it has to
        # be stored whether or not a rival was found.
        user_hashtags = [h.lower() for h in re.findall(r'#(\w+)', str(description))]
        user_hashtags = list(dict.fromkeys([h for h in user_hashtags if h]))
        user_meta = {
            'user_title_len': len(title),
            'user_tags': [t.strip() for t in tags.split(',') if t.strip()],
            'user_hashtags': user_hashtags,
            'user_description': description,
        }
        if competitor_data:
            competitor_data.update(user_meta)

        kill_switch_active = False
        if competitor_data:
            comp_title_for_ks = competitor_data.get('title', '')
            kill_switch_active = compute_kill_switch(title, comp_title_for_ks)

        retention = {"score": 5.0, "worst_drop_sec": 0, "drop_percent": 0, "has_csv": False, "early_drop_sec": 0}
        if c_path:
            retention["has_csv"] = True
            try:
                df = pd.read_csv(c_path, skipinitialspace=True)
                df.columns = df.columns.str.strip().str.lower()
                ret_keywords = ['retention', 'izlenme', 'görüntüleme', 'elde tutma', 'kitle tutma']
                ret_col = next((col for col in df.columns if any(kw in col.lower() for kw in ret_keywords)), None)
                if ret_col:
                    df[ret_col] = df[ret_col].astype(str).str.replace('%', '', regex=False).str.replace(',', '.', regex=False)
                    df[ret_col] = pd.to_numeric(df[ret_col], errors='coerce')
                    intro = df[ret_col].dropna().iloc[:30]
                    if len(intro) > 5:
                        start = intro.iloc[0]
                        worst_idx = intro.diff().idxmin()
                        drop_p = (start - intro.min()) / start * 100
                        retention = {
                            "score": round(max(0, min(10, 10 - (drop_p * 0.13)))),
                            "worst_drop_sec": int(worst_idx),
                            "drop_percent": round(drop_p, 1),
                            "has_csv": True,
                            "early_drop_sec": int(intro[:10].idxmin())
                        }
            except Exception as e:
                app_logger.warning(f"Hata [analyze_video CSV parse]: {e}")

        # --- NON-BLOCKING: Thumbnail analysis (DeepFace + contrast + vibrant) ---
        thumb_data = (await run_in_threadpool(AnalysisEngine.analyze_thumbnail, t_path)) if t_path else {
            "score": 0.0, "face_detected": False, "face_count": 0, "faces": [],
            "contrast_ratio": 0.0, "text_space_score": 0.0,
            "vibrant_color_match": 0.0, "visual_summary": ""
        }
        thumb_score = thumb_data["score"]

        seo_score = 0.0
        seo_score += 3.5 if 35 <= len(title) <= 70 else 2.0
        seo_score += min(3.5, len([t for t in tags.split(',') if t.strip()]) * 0.5)
        hook_words = ['nasıl', 'neden', 'en iyi', '2024', 'şok', 'sır', '!', '?', 'sonunda', 'efsane', 'bittirdik']
        if any(w in title.lower() for w in hook_words):
            seo_score += 1.5
        seo_score = min(10.0, round(seo_score, 1))

        # Shorts: retention=0.50, tech=0.35, seo=0.15 → total 1.00
        # Normal: retention=0.45, tech=0.28, seo=0.17, thumb=0.10 → total 1.00
        weights = {"retention": 0.50 if is_shorts else 0.45, "tech": 0.35, "seo": 0.15 if is_shorts else 0.17, "thumb": 0.0 if is_shorts else 0.10}
        if not t_path and not is_shorts:
            weights["retention"], weights["tech"], weights["seo"] = 0.45, 0.35, 0.20
        overall = round(retention["score"] * weights["retention"] + tech["tech_score"] * weights["tech"] + seo_score * weights["seo"] + thumb_score * weights["thumb"], 1)

        # ── Visual Intelligence Summary (Phase 3) ──
        vi_parts = []
        if thumb_data.get("face_detected") and thumb_data.get("faces"):
            primary_face = thumb_data["faces"][0]
            emo = primary_face.get("dominant_emotion", "neutral")
            emo_conf = primary_face.get("emotion_scores", {}).get(emo, 0)
            gaze = "looking at camera" if primary_face.get("looking_at_camera") else "looking away"
            vi_parts.append(
                f"Thumbnail: Face detected with '{emo}' emotion "
                f"({emo_conf:.0f}% confidence), {gaze}."
            )
        elif thumb_data.get("face_detected"):
            vi_parts.append("Thumbnail: Face detected (basic analysis).")
        else:
            vi_parts.append("Thumbnail: No face detected or could not be identified.")

        if thumb_data.get("contrast_ratio", 0) > 0:
            cr = thumb_data["contrast_ratio"]
            cr_qual = "excellent" if cr >= 0.5 else "good" if cr >= 0.3 else "low"
            vi_parts.append(f"Contrast ratio: {cr_qual} ({cr:.2f}).")

        if thumb_data.get("vibrant_color_match", 0) > 0:
            vcm = thumb_data["vibrant_color_match"]
            vi_parts.append(f"Vibrant color match: {vcm}/10.")

        if thumb_data.get("text_space_score", 0) > 0:
            tss = thumb_data["text_space_score"]
            vi_parts.append(f"Text space score: {tss}/10.")

        if scene_changes:
            sc = scene_changes
            vi_parts.append(
                f"Scene analysis: {sc.get('cut_count', 0)} cuts detected, "
                f"{sc.get('cut_frequency', 0)} cuts/min, "
                f"avg motion intensity {sc.get('avg_motion_intensity', 0)}."
            )

        visual_insights_str = " ".join(vi_parts)

        dynamic_feedback = await AnalysisEngine.generate_dynamic_feedback(
            c_type, c_aud, c_purp, tech["tech_score"], retention["score"],
            tech["peaks"], lang=lang, thumb_insights=thumb_data,
            visual_insights_str=visual_insights_str)
        dynamic_feedback_tr = await AnalysisEngine.generate_dynamic_feedback(
            c_type, c_aud, c_purp, tech["tech_score"], retention["score"],
            tech["peaks"], lang="tr", thumb_insights=thumb_data,
            visual_insights_str=visual_insights_str)
        dynamic_feedback_en = await AnalysisEngine.generate_dynamic_feedback(
            c_type, c_aud, c_purp, tech["tech_score"], retention["score"],
            tech["peaks"], lang="en", thumb_insights=thumb_data,
            visual_insights_str=visual_insights_str)
        dynamic_feedback_es = await AnalysisEngine.generate_dynamic_feedback(
            c_type, c_aud, c_purp, tech["tech_score"], retention["score"],
            tech["peaks"], lang="es", thumb_insights=thumb_data,
            visual_insights_str=visual_insights_str)
        

        result = {
            "overall_score": overall, "retention_score": retention["score"], "retention_data": retention,
            "tech_score": tech["tech_score"], "tech_data": tech, "seo_score": seo_score,
            "thumb_score": thumb_score if not is_shorts else None, "thumb_data": thumb_data,
            "peaks": tech["peaks"], "viral_score": tech["viral_score"],
            "title": title, "tags": tags, "is_shorts_mode": is_shorts, "pro_mode": pro_mode,
            "coaching_mode": "PROACTIVE" if retention["has_csv"] else "PREDICTIVE",
            "visual_tempo": v_tempo, "audio_tempo": a_tempo, "golden_frame_sec": golden_frame_sec,
            "dynamic_feedback": dynamic_feedback,
            "dynamic_feedback_tr": dynamic_feedback_tr,
            "dynamic_feedback_en": dynamic_feedback_en,
            "dynamic_feedback_es": dynamic_feedback_es,
            "competitor_data": competitor_data,
            "competitor_status": competitor_status,
            "user_meta": user_meta,
            "industry_std": AnalysisEngine.get_industry_standard(c_type),
            "viral_segments": AnalysisEngine.find_viral_segments(
                tech, visual_tempo=v_tempo, scene_changes=scene_changes),
            "scene_changes": scene_changes,
            "visual_intelligence_summary": visual_insights_str,
            "ffmpeg_available": FFMPEG_AVAILABLE,
            "yt_dlp_available": YT_DLP_AVAILABLE,
            "critical_warning": f"Hook {retention['score']}/10 | Tempo {tech['tech_score']}/10 | Peaks {tech['peaks']} total",
            "kill_switch_active": kill_switch_active,
            "temp_video_name": f"v_{uid}.mp4",
            "analysis_duration_sec": round(time.time() - analysis_start_time, 1)
        }
        result["analysis_id"] = await AnalysisEngine.save_analysis(channel_id, result, user_id)
        result["channel_comparison"] = await AnalysisEngine.get_channel_averages(channel_id)
        result["system_caps"] = SYSTEM_CAPS

        # ── Automatic Email Report Sending ──
        email_sent = False
        try:
            db_mail = await get_async_db()
            try:
                async with db_mail.execute("SELECT email, is_verified FROM users WHERE id=?", (user_id,)) as c_mail:
                    u_row = await c_mail.fetchone()
                async with db_mail.execute("SELECT key, value FROM app_settings WHERE key IN ('smtp_email', 'smtp_password')") as c_mail:
                    smtp_rows = {r[0]: r[1] async for r in c_mail}
            finally:
                await db_mail.close()

            user_email = u_row[0] if u_row and u_row[0] else ""
            has_smtp = bool(smtp_rows.get('smtp_email') and smtp_rows.get('smtp_password'))

            if user_email and has_smtp:
                # Create and send PDF (in thread pool)
                analysis_id = result["analysis_id"]
                _title = result.get("title", "Video")

                # Non-blocking: Notify Frontend that SMTP settings are ready
                # The actual email is triggered via /api/send_report when the user exports a PDF
                email_sent = True  # SMTP configuration available, sending can be triggered
                app_logger.info(f"SMTP ready, analysis report can be sent by email: user={user_email}")
        except Exception:
            pass

        result["email_sent"] = email_sent
        result["user_has_email"] = bool(user_email and has_smtp)
        return result

    except Exception as e:
        traceback.print_exc()
        if os.path.exists(v_path):
            try:
                os.remove(v_path)
            except Exception as e:
                app_logger.warning(f"Hata [create_short clean v_path]: {e}")
        return {"error": str(e)}
    finally:
        for p in [c_path, t_path]:
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except Exception as e:
                    app_logger.warning(f"Hata [create_short clean {p}]: {e}")


@app.post("/create_short")
async def create_short(
    start: float = Form(...),
    duration: float = Form(...),
    temp_filename: str = Form(...),
    video_file: Optional[UploadFile] = File(None)
):
    if not FFMPEG_AVAILABLE:
        return {"error": "FFmpeg was not found on this system."}

    uid = str(uuid.uuid4())[:8]
    output_name = f"short_{uid}.mp4"
    output_path = output_dir / output_name
    temp_in = None

    try:
        saved_path = temp_dir / temp_filename
        if temp_filename != "MISSING" and saved_path.exists():
            temp_in = str(saved_path)
        elif video_file:
            temp_in = str(temp_dir / f"fallback_{uid}.mp4")
            # --- NON-BLOCKING: File copying ---
            def _copy_fallback():
                with open(temp_in, "wb") as f:
                    shutil.copyfileobj(video_file.file, f)
            await run_in_threadpool(_copy_fallback)
        else:
            return {"error": "Video file not found. Please re-analyse the video."}

        # Set parameters based on GPU codec
        if GPU_CODEC == "libx264":
            codec_params = ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "18"]
        elif GPU_CODEC == "h264_nvenc":
            codec_params = ["-c:v", "h264_nvenc", "-preset", "p1", "-cq", "23"]
        elif GPU_CODEC == "h264_amf":
            codec_params = ["-c:v", "h264_amf", "-quality", "speed", "-rc", "cqp", "-qp_i", "23"]
        elif GPU_CODEC == "h264_qsv":
            codec_params = ["-c:v", "h264_qsv", "-preset", "veryfast", "-global_quality", "23"]
        else:
            codec_params = ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "18"]

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-i", temp_in,
            "-t", str(duration),
            "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1",
            *codec_params,
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            str(output_path)
        ]

        # --- NON-BLOCKING: FFmpeg subprocess ---
        def _run_ffmpeg_short():
            return subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                creationflags=0x08000000 if os.name == 'nt' else 0
            )
        process = await run_in_threadpool(_run_ffmpeg_short)

        if process.returncode != 0:
            print(f"FFmpeg Error Details: {process.stderr}")
            return {"error": f"Cut operation failed: {process.stderr[:100]}"}

        return {
            "success": True,
            "filename": output_name,
            "download_url": f"/shorts/{output_name}"
        }

    except Exception as e:
        traceback.print_exc()
        return {"error": f"System Error: {str(e)}"}


@app.get("/export_pdf/{analysis_id}")
async def export_pdf(analysis_id: int, lang: str = "tr"):
    # If an invalid language code comes up, switch to Turkish.
    if lang not in PDF_LANG or not PDF_LANG[lang]:
        lang = "tr"
    L = PDF_LANG[lang]


    def esc(txt):
        if txt is None:
            return ""
        s = str(txt)
        s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        s = s.replace('"', "").replace("'", "")
        return s

    conn = get_db()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,))
    analysis = c.fetchone()
    if not analysis:
        raise HTTPException(status_code=404)
    channel_id = analysis['channel_id']
    c2 = conn.cursor()
    c2.execute("SELECT name, content_type FROM channels WHERE id = ?", (channel_id,))
    ch_info = c2.fetchone()
    channel_name = ch_info['name'] if ch_info else "Bilinmeyen Kanal"
    c_type = ch_info['content_type'] if ch_info else "Genel"
    averages = await AnalysisEngine.get_channel_averages(channel_id)
    conn.close()

    overall = float(analysis['overall_score'])
    retention = float(analysis['retention_score'])
    tech = float(analysis['tech_score'])
    seo = float(analysis['seo_score'])
    thumb = float(analysis['thumb_score']) if analysis['thumb_score'] is not None else 0.0
    peaks = int(analysis['peaks'])
    video_name_str = str(analysis['video_name'])

    # Get video_description and video_tags from DB (or extract from competitor_data)
    video_description_str = ""
    video_tags_str = ""
    try:
        video_description_str = str(analysis['video_description'] or "")
    except Exception as e:
        app_logger.debug(f"PDF extract description error: {e}")
    try:
        video_tags_str = str(analysis['video_tags'] or "")
    except Exception as e:
        app_logger.debug(f"PDF extract tags error: {e}")

    # Try getting description and tag from competitor_data as well
    comp_json_raw = analysis['competitor_data']
    if comp_json_raw and (not video_tags_str or not video_description_str):
        try:
            _cd = json.loads(comp_json_raw)
            if not video_tags_str:
                ut = _cd.get('user_tags', [])
                video_tags_str = ', '.join(ut) if isinstance(ut, list) else str(ut)
            if not video_description_str:
                video_description_str = _cd.get('user_description', '')
        except Exception as e:
            app_logger.debug(f"PDF extract competitor info error: {e}")

    pdf_path = output_dir / f"report_{analysis_id}_{lang}.pdf"
    doc = SimpleDocTemplate(
        str(pdf_path), pagesize=letter,
        leftMargin=1.25*inch, rightMargin=1.25*inch,
        topMargin=1.0*inch, bottomMargin=1.0*inch
    )
    elements = []
    styles = getSampleStyleSheet()

    # ── APA Style Definitions ──
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

    # Cover title (centered, large)
    title_s = ParagraphStyle('apa_title',
        fontName=FONT_BOLD, fontSize=16, leading=22,
        alignment=TA_CENTER, spaceAfter=6, textColor=colors.HexColor('#1a0533'))

    # Heading — ALL CAPS
    heading1_s = ParagraphStyle('apa_h1',
        fontName=FONT_BOLD, fontSize=13, leading=18,
        alignment=TA_LEFT, spaceBefore=18, spaceAfter=6,
        textColor=colors.HexColor('#1a0533'),
        borderPad=4)

    # Subheading — First Letter Capitalized
    heading2_s = ParagraphStyle('apa_h2',
        fontName=FONT_BOLD, fontSize=11, leading=16,
        alignment=TA_LEFT, spaceBefore=12, spaceAfter=4,
        textColor=colors.HexColor('#3b0764'))

    # Normal text — justify
    normal_s = ParagraphStyle('apa_normal',
        fontName=FONT_REGULAR, fontSize=10, leading=15,
        alignment=TA_JUSTIFY, spaceAfter=6,
        textColor=colors.HexColor('#1e293b'))

    # Keep the old heading_s = heading1_s
    heading_s = heading1_s

    # Episode counter
    sec = [0]
    def h1(text):
        sec[0] += 1
        return Paragraph(f"{sec[0]}. {text.upper()}", heading1_s)
    def h2(text):
        # Capitalize first letters
        cap = ' '.join(w.capitalize() for w in text.split())
        return Paragraph(cap, heading2_s)

    # ── Cover ──
    elements.append(Paragraph(L['report_title'], title_s))
    elements.append(Spacer(1, 0.1 * inch))
    elements.append(Paragraph(
        f"<b>{L['your_channel']}:</b> {esc(channel_name)}&nbsp;&nbsp;|&nbsp;&nbsp;<b>{L['your_video']}:</b> {esc(video_name_str)}",
        normal_s
    ))
    elements.append(Spacer(1, 0.1 * inch))

    # thin dividing line
    from reportlab.platypus import HRFlowable
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#7c3aed'), spaceAfter=14))

    # ── 1. Viral Potential ──
    elements.append(h1(L['viral_potential'].replace('🔥', '').strip()))
    if peaks >= 5:
        if seo >= 7.0 and thumb >= 5.0:
            viral_txt = (f"<font color='green'><b>{L['viral_high']}</b></font><br/>"
                         + L['viral_high_desc'].format(peaks=peaks, seo=seo))
        else:
            viral_txt = (f"<font color='red'><b>{L['viral_low_pkg']}</b></font><br/>"
                         + L['viral_low_pkg_desc'].format(peaks=peaks, seo=seo, thumb=thumb))
    else:
        viral_txt = f"<b>{L['viral_low'].format(peaks=peaks)}</b>"
    elements.append(Paragraph(viral_txt, normal_s))
    elements.append(Spacer(1, 0.3 * inch))

    # ── 2. Industry Standards ──
    elements.append(h1(L['sector_std'].format(ctype=esc(c_type[:30])).replace('📊', '').strip()))
    ind_std = AnalysisEngine.get_industry_standard(c_type)
    std_data = [
        [L['metric'], L['your_video_col'], L['sector_ideal'], L['status']],
        [L['tempo_score'], f"{tech:.1f}", f"{ind_std['tempo']:.1f}", L['good'] if tech >= ind_std['tempo'] else L['behind']],
        [L['seo_power'], f"{seo:.1f}", f"{ind_std['seo']:.1f}", L['good'] if seo >= ind_std['seo'] else L['behind']],
        [L['retention'], f"{retention:.1f}", f"{ind_std['retention']:.1f}", L['good'] if retention >= ind_std['retention'] else L['behind']]
    ]
    t_std = Table(std_data)
    t_std.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('FONTNAME', (0, 0), (-1, 0), FONT_BOLD),
        ('GRID', (0, 0), (-1, -1), 1, colors.black), ('FONTNAME', (0, 1), (-1, -1), FONT_REGULAR)
    ]))
    elements.append(t_std)
    elements.append(Spacer(1, 0.1 * inch))
    elements.append(Paragraph(f"<font size=8 color='#666666'>{esc(L['sector_note'])}</font>", normal_s))
    elements.append(Spacer(1, 0.3 * inch))

    # ── SEO / Thumbnail Balance Alert ──

    elements.append(Paragraph(f"<font size=8 color='#666666'>{esc(L['sector_note'])}</font>", normal_s))
    elements.append(Spacer(1, 0.2 * inch))

    # ── 3. SEO / Thumbnail Balance Alert ──
    # Case 1: SEO is strong but Thumbnail is weak → search pops up, no clicks
    if seo >= 7.0 and thumb > 0.0 and thumb < 5.0:
        elements.append(h1(L['seo_thumb_warn_title'].replace('⚖️', '').strip()))
        elements.append(Paragraph(
            f"<font color='#d97706'>{L['seo_thumb_warn_msg'].format(seo=seo, thumb=thumb)}</font>",
            normal_s
        ))
        elements.append(Spacer(1, 0.15 * inch))
    elif thumb >= 7.0 and seo < 5.0:
        elements.append(h1(L['seo_thumb_warn_title'].replace('⚖️', '').strip()))
        elements.append(Paragraph(
            f"<font color='#d97706'>{L['thumb_seo_warn_msg'].format(seo=seo, thumb=thumb)}</font>",
            normal_s
        ))
        elements.append(Spacer(1, 0.15 * inch))

    # ── 4. Content Consistency Check ──
    elements.append(h1(L['consistency_title'].replace('🔎', '').strip()))
    consistency = check_content_consistency(video_name_str, video_tags_str, video_description_str)
    if consistency['ok']:
        elements.append(Paragraph(f"<font color='green'><b>{L['consistency_ok']}</b></font>", normal_s))
    else:
        consistency_txt = f"<font color='#ef4444'><b>{L['consistency_warn']}</b></font><br/>"
        for issue in consistency['issues']:
            if issue == 'no_tags':
                consistency_txt += f"• <b>{L['no_tags']}:</b> <font color='#d97706'>{L['no_tags_desc']}</font><br/>"
            elif issue == 'no_desc':
                consistency_txt += f"• <b>{L['no_desc']}:</b> <font color='#d97706'>{L['no_desc_desc']}</font><br/>"
            elif issue == 'title_tags_mismatch':
                consistency_txt += f"• <b>{L['title_tags_mismatch']}:</b> <font color='#ef4444'>{L['title_tags_mismatch_desc']}</font><br/>"
            elif issue == 'title_desc_mismatch':
                consistency_txt += f"• <b>{L['title_desc_mismatch']}:</b> <font color='#d97706'>{L['title_desc_mismatch_desc']}</font><br/>"
        elements.append(Paragraph(consistency_txt, normal_s))
    elements.append(Spacer(1, 0.3 * inch))

    # ── Competitor Analysis ──
    comp_json = analysis['competitor_data']
    face_detected = False

    if comp_json:
        try:
            comp = json.loads(comp_json)
            face_detected = comp.get('face_detected', False)
            raw_channel = comp.get('channel') or 'Rakip Kanal'
            raw_title = comp.get('title') or 'Bilinmiyor'
            comp_channel_upper = esc(raw_channel.upper())
            comp_title = esc(raw_title)
            is_fake_data = comp.get('is_fake', False)
            # Rows written before the rival became optional have no flag but do have a rival.
            has_competitor = comp.get('has_competitor', True)

            if is_fake_data:
                elements.append(Paragraph(L['competitor_disabled'], heading_s))
                elements.append(Paragraph(
                    f"<font color='#ef4444'><b>{L['fake_data_title']}</b></font><br/>"
                    f"<font color='#d97706'>{L['fake_data_desc']}</font><br/><br/>"
                    f"<b>{L['fake_data_action']}</b><br/>"
                    f"{L['fake_data_fix1']}<br/>"
                    f"{L['fake_data_fix2']}",
                    normal_s
                ))
                elements.append(Spacer(1, 0.3 * inch))
                raise ValueError("FAKE_DATA_SKIP")

            v_raw = comp.get('views')
            try:
                views = int(v_raw) if v_raw is not None else 0
            except Exception as e:
                app_logger.debug(f"PDF views extract error: {e}")
                views = 0
            likes = int(comp.get('likes') or 0)
            comments = int(comp.get('comments') or 0)
            upload_date = comp.get('upload_date') or datetime.now().strftime('%Y%m%d')
            try:
                up_dt = datetime.strptime(upload_date, '%Y%m%d')
                days_live = max(1, (datetime.now() - up_dt).days)
                views_per_day = int(views / days_live)
            except Exception as e:
                app_logger.debug(f"PDF views_per_day extract error: {e}")
                views_per_day = views
            engagement = round(((likes + comments) / views * 100), 1) if views > 0 else 0.0
            comp_tags = comp.get('tags') or []
            user_tags = comp.get('user_tags') or []
            if not isinstance(comp_tags, list):
                comp_tags = []
            if not isinstance(user_tags, list):
                user_tags = []
            c_hashtags = comp.get('hashtags') or []
            u_hashtags = comp.get('user_hashtags') or []
            if not isinstance(c_hashtags, list):
                c_hashtags = []
            if not isinstance(u_hashtags, list):
                u_hashtags = []
            u_raw_len = comp.get('user_title_len')
            try:
                user_title_len = int(u_raw_len) if u_raw_len is not None else 0
            except Exception as e:
                app_logger.debug(f"PDF title_len extract error: {e}")
                user_title_len = 0
            is_manual = bool(comp.get('is_manual'))

            def tr_lower(s):
                return str(s).replace('İ', 'i').replace('I', 'ı').lower()

            broad_keywords = ['oyun', 'oyunlar', 'video', 'videolar', 'game', 'gaming', 'türkiye', 'tr',
                              'eğlence', 'komik', 'trend', 'viral', 'youtube', 'youtuber', 'abone', 'izle',
                              'yeni', 'ilk', 'türkçe', 'turkiye']

            raw_desc = comp.get('user_description', "")
            desc_clean = re.sub(r'#\w+', '', str(raw_desc))
            user_corpus_text = video_name_str + " " + channel_name + " " + desc_clean
            user_corpus = extract_core_keywords(user_corpus_text)

            # ── 5. SEO Check-Up ──
            elements.append(h1(L['checkup_title'].replace('🩺', '').strip()))
            checkup_txt = ""
            has_error = False
            user_tags_clean = [str(t).lower().replace('#', '').strip() for t in user_tags if str(t).strip()]
            u_hash_clean = [str(h).lower().replace('#', '').strip() for h in u_hashtags if str(h).strip()]

            broad_used_tags = [t for t in user_tags_clean if t in broad_keywords]
            irrelevant_used_tags = []
            for t in user_tags_clean:
                if t in broad_keywords:
                    continue
                t_words = extract_core_keywords(t)
                if t_words:
                    is_valid = False
                    for tw in t_words:
                        for cw in user_corpus:
                            if tw in cw or cw in tw:
                                is_valid = True
                                break
                        if is_valid:
                            break
                    if not is_valid:
                        irrelevant_used_tags.append(t)

            broad_used_hashes = [h for h in u_hash_clean if h in broad_keywords]
            irrelevant_used_hashes = []
            for h in u_hash_clean:
                if h in broad_keywords:
                    continue
                h_words = extract_core_keywords(h)
                if h_words:
                    is_valid = False
                    for hw in h_words:
                        for cw in user_corpus:
                            if hw in cw or cw in hw:
                                is_valid = True
                                break
                        if is_valid:
                            break
                    if not is_valid:
                        irrelevant_used_hashes.append(h)

            if broad_used_tags or irrelevant_used_tags:
                has_error = True
                checkup_txt += f"<b>{L['tag_errors']}:</b><br/>"
                if broad_used_tags:
                    checkup_txt += f"  - <b>{L['broad_tags_title']}:</b> <font color='#d97706'><b>{', '.join(broad_used_tags)}</b></font><br/>"
                    checkup_txt += f"  <font color='#666666'><em>* {L['broad_tags_note']}</em></font><br/>"
                if irrelevant_used_tags:
                    checkup_txt += f"  - <b>{L['irrelevant_tags_title']}:</b> <font color='#ef4444'><b>{', '.join(irrelevant_used_tags)}</b></font><br/>"
                    checkup_txt += f"  <font color='#666666'><em>* {L['irrelevant_tags_note']}</em></font><br/>"
                    # Neden silinmesi gerektiğini açıkla
                    _why_tag = {
                        'tr': 'Bu etiketler videonuzun başlığında veya açıklamasında geçmiyor. YouTube algoritması tutarsız etiketleri olumsuz değerlendirebilir, bu yüzden kaldırmanızı öneriyoruz.',
                        'en': 'These tags do not appear in your video title or description. YouTube\'s algorithm may negatively evaluate inconsistent tags, which is why we recommend removing them.',
                        'es': 'Estas etiquetas no aparecen en el título o descripción de tu video. El algoritmo de YouTube puede evaluar negativamente las etiquetas inconsistentes, por eso recomendamos eliminarlas.',
                    }
                    checkup_txt += f"  <font color='#888888'><em>→ {_why_tag.get(lang, _why_tag['en'])}</em></font><br/>"

            if broad_used_hashes or irrelevant_used_hashes:
                has_error = True
                checkup_txt += f"<br/><b>{L['hash_errors']}:</b><br/>"
                if broad_used_hashes:
                    checkup_txt += f"  - <b>{L['broad_hashes_title']}:</b> <font color='#d97706'><b>{', '.join(['#' + h for h in broad_used_hashes])}</b></font><br/>"
                    checkup_txt += f"  <font color='#666666'><em>* {L['broad_hashes_note']}</em></font><br/>"
                if irrelevant_used_hashes:
                    checkup_txt += f"  - <b>{L['irrelevant_hashes_title']}:</b> <font color='#ef4444'><b>{', '.join(['#' + h for h in irrelevant_used_hashes])}</b></font><br/>"
                    checkup_txt += f"  <font color='#666666'><em>* {L['irrelevant_hashes_note']}</em></font><br/>"
                    # Neden silinmesi gerektiğini açıkla
                    _why_hash = {
                        'tr': 'Bu hashtag\'ler videonuzun başlığında veya açıklamasında geçmiyor. Kullanmak doğrudan zararlı olmayabilir ancak başlık/açıklamayla uyumlu hashtag\'ler algoritmada daha etkilidir. Bu yüzden kaldırmanızı öneriyoruz.',
                        'en': 'These hashtags do not appear in your video title or description. Using them may not be directly harmful, but hashtags consistent with your title/description are more effective. That\'s why we recommend removing them.',
                        'es': 'Estos hashtags no aparecen en el título o descripción de tu video. Usarlos puede no ser directamente dañino, pero los hashtags consistentes con tu título/descripción son más efectivos. Por eso recomendamos eliminarlos.',
                    }
                    checkup_txt += f"  <font color='#888888'><em>→ {_why_hash.get(lang, _why_hash['en'])}</em></font><br/>"

            if not u_hashtags:
                has_error = True
                checkup_txt += f"<br/><b>{L['missing_hashtag']}:</b> <font color='#ef4444'>{L['missing_hashtag_desc']}</font><br/>"

            if not has_error:
                checkup_txt += f"<font color='green'><b>{L['checkup_ok']}</b></font><br/>"

            elements.append(Paragraph(checkup_txt, normal_s))
            elements.append(Spacer(1, 0.4 * inch))

            # The SEO check-up above is about the user's own video, so it runs either
            # way. Only the head-to-head part needs an actual rival.
            if not has_competitor:
                elements.append(Paragraph(L['competitor_disabled'], heading_s))
                elements.append(Paragraph(
                    f"<font color='#d97706'>{L['no_competitor_desc']}</font>", normal_s))
                elements.append(Spacer(1, 0.3 * inch))
                raise ValueError("NO_COMPETITOR_SKIP")

            is_mismatch_detected = compute_kill_switch(video_name_str, raw_title)
            comp_txt = ""

            if is_mismatch_detected:
                comp_txt += f"<br/><font color='#ef4444'>🚨 <b>{L['mismatch_detected']}</b></font><br/>"
                comp_txt += f"<font color='#d97706'><em>{L['mismatch_desc']}</em></font><br/><br/>"

            elements.append(h1(f"{L['you']} VS. {comp_channel_upper}"))

            if is_manual:
                comp_txt += f"<b>{L['manual_comp']}:</b> {comp_title}<br/><br/>"
            else:
                comp_txt += f"<b>{L['auto_comp']}:</b> {comp_title}<br/><br/>"

            comp_txt += f"<b>{L['xray_title']}:</b><br/>"
            comp_txt += f"• <b>{L['daily_views']}:</b> {views_per_day:,} {L['views_per_day_unit']}<br/>"
            comp_txt += f"• <b>{L['engagement_rate']}:</b> %{engagement} {L['engagement_unit']}<br/>"
            if engagement > 4.0:
                comp_txt += f"<font color='green'><em>{L['engagement_high']}</em></font><br/><br/>"
            else:
                comp_txt += f"<font color='#d97706'><em>{L['engagement_low']}</em></font><br/><br/>"

            u_tags_lower = [str(t).lower() for t in user_tags]
            common = [esc(t) for t in comp_tags if str(t).lower() in u_tags_lower]
            missing = [esc(t) for t in comp_tags if str(t).lower() not in u_tags_lower]
            toxic_keywords_list = [
                'parodi', 'animasyon', 'roleplay', 'rp', 'speedrun',
                'şarkı', 'müzik klip', 'film', 'dizi',
                'roblox', 'fortnite', 'gta', 'cs2', 'csgo',
                'valorant', 'pubg', 'fifa', 'apex', 'warzone',
                'canlı yayın', 'stream', 'twitch',
            ]
            v_title_lower_str = tr_lower(video_name_str)

            comp_txt += f"<b>{L['similarities_title']}:</b><br/>"
            if common:
                comp_txt += L['similarities_yes'].format(tags=', '.join(common)) + "<br/><br/>"
            else:
                comp_txt += L['similarities_no'] + "<br/><br/>"

            comp_txt += f"<b>{L['differences_title']}:</b><br/>"
            comp_txt += f"• <b>{L['title_strategy']}:</b> "
            if len(raw_title) > user_title_len + 15:
                comp_txt += L['title_longer'] + "<br/>"
            else:
                comp_txt += L['title_similar'] + "<br/>"

            if missing:
                comp_txt += f"<br/>• <b>{L['tag_analysis']}:</b><br/>"
                if is_mismatch_detected:
                    comp_txt += f"<font color='#d97706'><em>⚠️ {L['concept_mismatch_warn']}</em></font><br/>"
                perfect_matches, others, toxic_matches = [], [], []
                for t in missing:
                    t_l = tr_lower(t)
                    if t_l in broad_keywords:
                        continue
                    is_toxic = any(tw in t_l and tw not in v_title_lower_str for tw in toxic_keywords_list)
                    if is_toxic:
                        toxic_matches.append(t)
                    elif t_l in v_title_lower_str:
                        perfect_matches.append(t)
                    else:
                        others.append(t)
                if perfect_matches:
                    comp_txt += f"<b>{L['perfect_match_tags']}:</b> <font color='green'><b>{', '.join(perfect_matches)}</b></font><br/><br/>"
                if others:
                    comp_txt += f"<b>{L['inspiration_tags']}:</b> <font color='#c026d3'><b>{', '.join(others[:8])}</b></font><br/><br/>"
                if toxic_matches:
                    comp_txt += f"<b>{L['toxic_tags']}:</b> <font color='#ef4444'><b><strike>{', '.join(toxic_matches[:6])}</strike></b></font><br/>"
                    comp_txt += f"<font color='#666666'><em>* {L['toxic_tags_note']}</em></font><br/><br/>"

            if c_hashtags:
                u_hash_lower = [str(h).lower() for h in u_hashtags]
                missing_hashtags = [esc(h) for h in c_hashtags if str(h).lower() not in u_hash_lower]
                filtered_missing_hashtags = []
                for h in missing_hashtags:
                    h_l = tr_lower(h)
                    if h_l in broad_keywords:
                        continue
                    if not any(tw in h_l and tw not in v_title_lower_str for tw in toxic_keywords_list):
                        filtered_missing_hashtags.append(h)
                if filtered_missing_hashtags:
                    comp_txt += f"• <b>{L['steal_hashtags']}:</b> <font color='#c026d3'><b>{', '.join(['#' + h for h in filtered_missing_hashtags[:5]])}</b></font><br/><br/>"

            # AI Title Generator
            clean_user = re.sub(r'\(.*?\)|\[.*?\]|\{.*?\}', '', video_name_str)
            clean_user = re.split(r'[|#–—]', clean_user)[0]
            clean_user = re.sub(r'\s+', ' ', clean_user).strip()
            if not clean_user or len(clean_user) < 3:
                clean_user = video_name_str[:40]

            if lang == 'en':
                t1 = f"NOBODY SAW THIS COMING! {clean_user}"
                t2 = f"{clean_user} (The Ending Is Shocking) 😱"
                t3 = f"THEY SAID IMPOSSIBLE! {clean_user} 🔥"
            elif lang == 'es':
                t1 = f"¡NADIE ESPERABA ESTO! {clean_user}"
                t2 = f"{clean_user} (El Final Es Impactante) 😱"
                t3 = f"¡DIJERON QUE ERA IMPOSIBLE! {clean_user} 🔥"
            else:  # Turkish fallback titles (intentional — tr-locale content)
                t1 = f"BUNU KİMSE BEKLEMİYORDU! {clean_user}"
                t2 = f"{clean_user} (Oyunun Sonu Çok Garip) 😱"
                t3 = f"İMKANSIZ DENİLDİ! {clean_user} 🔥"

            comp_txt += f"• <b>{L['ai_title_gen']}:</b><br/>"
            comp_txt += f"{L['ai_title_intro']}<br/>"
            comp_txt += f"  <font color='#2563eb'><b>1️⃣ {t1}</b></font><br/>"
            comp_txt += f"  <font color='#2563eb'><b>2️⃣ {t2}</b></font><br/>"
            comp_txt += f"  <font color='#2563eb'><b>3️⃣ {t3}</b></font><br/><br/>"

            comp_txt += f"<b>{L['ai_strategy']}:</b><br/>"
            if views > 10000:
                comp_txt += L['views_high'].format(views=f"{views:,}")
            else:
                comp_txt += L['views_low'].format(views=f"{views:,}")

            elements.append(Paragraph(comp_txt, normal_s))
            elements.append(Spacer(1, 0.4 * inch))

        except ValueError as ve:
            if not any(sentinel in str(ve) for sentinel in ("FAKE_DATA_SKIP", "NO_COMPETITOR_SKIP")):
                traceback.print_exc()
        except Exception as e:
            traceback.print_exc()

    # ═══════════════════════════════════════════════════════════
    # PDF 2.0 — ADVANCED TABLES
    # ═══════════════════════════════════════════════════════════
    # Translation fallbacks (inline since translations.xlsx is binary)
    _pdf2_tr = {
        "emotion_title": "THUMBNAIL EMOTION ANALYSIS",
        "emotion": "Emotion", "score": "Score (%)", "dominant": "Dominant",
        "no_face": "Thumbnail'de yüz bulunamadı veya tespit edilemedi.",
        "visual_title": "VISUAL QUALITY METRICS",
        "metric": "Metric", "value": "Value", "status": "Status",
        "contrast": "Contrast (Michelson)", "vibrant": "Vibrant Color Harmony",
        "text_space": "Text Area Score", "brightness": "Brightness",
        "excellent": "Excellent", "good": "Good", "low": "Low", "medium": "Medium",
        "excitement_title": "EXCITEMENT SCORE SUMMARY",
        "segment": "Segment", "time_range": "Time Range",
        "excitement": "Excitement", "audio": "Audio Den.", "cut": "Cut Den.",
        "motion": "Motion Den.", "no_segments": "No viral segments detected.",
    }
    _pdf2_en = {
        "emotion_title": "THUMBNAIL EMOTION ANALYSIS",
        "emotion": "Emotion", "score": "Score (%)", "dominant": "Dominant",
        "no_face": "No face detected in thumbnail or could not be identified.",
        "visual_title": "VISUAL QUALITY METRICS",
        "metric": "Metric", "value": "Value", "status": "Status",
        "contrast": "Contrast (Michelson)", "vibrant": "Vibrant Color Match",
        "text_space": "Text Space Score", "brightness": "Brightness",
        "excellent": "Excellent", "good": "Good", "low": "Low", "medium": "Medium",
        "excitement_title": "EXCITEMENT SCORE SUMMARY",
        "segment": "Segment", "time_range": "Time Range",
        "excitement": "Excitement", "audio": "Audio Int.", "cut": "Cut Density",
        "motion": "Motion Int.", "no_segments": "No viral segments detected.",
    }
    _pdf2_es = {
        "emotion_title": "ANÁLISIS DE EMOCIÓN DE MINIATURA",
        "emotion": "Emoción", "score": "Puntuación (%)", "dominant": "Dominante",
        "no_face": "No se detectó rostro en la miniatura o no pudo ser identificado.",
        "visual_title": "MÉTRICAS DE CALIDAD VISUAL",
        "metric": "Métrica", "value": "Valor", "status": "Estado",
        "contrast": "Contraste (Michelson)", "vibrant": "Coincidencia de Color Vibrante",
        "text_space": "Puntuación de Espacio de Texto", "brightness": "Brillo",
        "excellent": "Excelente", "good": "Bueno", "low": "Bajo", "medium": "Medio",
        "excitement_title": "RESUMEN DE PUNTUACIÓN DE EMOCIÓN",
        "segment": "Segmento", "time_range": "Rango de Tiempo",
        "excitement": "Emoción", "audio": "Int. Audio", "cut": "Densidad Cortes",
        "motion": "Int. Movimiento", "no_segments": "No se detectaron segmentos virales.",
    }
    P2 = {"tr": _pdf2_tr, "en": _pdf2_en, "es": _pdf2_es}.get(lang, _pdf2_tr)

    # Extract additional data from competitor_data JSON
    _saved_thumb = {}
    _saved_segments = []
    if comp_json:
        try:
            _cd = json.loads(comp_json)
            _saved_thumb = _cd.get('_thumb_data', {})
            _saved_segments = _cd.get('_viral_segments', [])
        except Exception as e:
            app_logger.debug(f"PDF JSON loads error: {e}")

    # ── TABLE 1: Thumbnail Sentiment Analysis ──
    elements.append(PageBreak())
    elements.append(h1(P2["emotion_title"]))
    _faces = _saved_thumb.get("faces", [])
    if _faces:
        emo_headers = [P2["emotion"], P2["score"], P2["dominant"]]
        emo_data = [emo_headers]
        for face_info in _faces[:3]:
            scores = face_info.get("emotion_scores", {})
            dom = face_info.get("dominant_emotion", "neutral")
            for emo_name, emo_val in sorted(scores.items(), key=lambda x: x[1], reverse=True):
                is_dom = "✅" if emo_name == dom else ""
                emo_data.append([emo_name.capitalize(), f"{emo_val:.1f}%", is_dom])
        emo_table = Table(emo_data, colWidths=[2.2*inch, 1.5*inch, 1.2*inch])
        emo_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6b21a8')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), FONT_BOLD),
            ('FONTNAME', (0, 1), (-1, -1), FONT_REGULAR),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f5f3ff')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f5f3ff'), colors.HexColor('#ede9fe')]),
        ]))
        elements.append(emo_table)
        gaze_info = _faces[0].get("looking_at_camera", False)
        gaze_txt = "👀 Looking at camera ✅" if lang == "en" else "👀 Mirando a cámara ✅" if lang == "es" else "👀 Looking at camera ✅"
        if not gaze_info:
            gaze_txt = "👀 Not looking at camera" if lang == "en" else "👀 No mira a cámara" if lang == "es" else "👀 Not looking at camera"
        elements.append(Spacer(1, 0.1 * inch))
        elements.append(Paragraph(f"<font size=9 color='#6b21a8'><b>{gaze_txt}</b></font>", normal_s))
    else:
        elements.append(Paragraph(f"<font color='#94a3b8'><em>{P2['no_face']}</em></font>", normal_s))
    elements.append(Spacer(1, 0.3 * inch))

    # ── TABLE 2: Visual Quality Metrics ──
    elements.append(h1(P2["visual_title"]))
    cr = _saved_thumb.get("contrast_ratio", 0)
    vcm = _saved_thumb.get("vibrant_color_match", 0)
    tss = _saved_thumb.get("text_space_score", 0)
    def _quality_status(val, thresholds=(7.0, 5.0)):
        if val >= thresholds[0]: return P2["excellent"]
        elif val >= thresholds[1]: return P2["good"]
        elif val > 0: return P2["low"]
        return "—"
    def _contrast_status(c_val):
        if c_val >= 0.5: return P2["excellent"]
        elif c_val >= 0.3: return P2["good"]
        elif c_val > 0: return P2["low"]
        return "—"

    vis_data = [
        [P2["metric"], P2["value"], P2["status"]],
        [P2["contrast"], f"{cr:.3f}", _contrast_status(cr)],
        [P2["vibrant"], f"{vcm}/10", _quality_status(vcm)],
        [P2["text_space"], f"{tss}/10", _quality_status(tss)],
    ]
    vis_table = Table(vis_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
    vis_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f766e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), FONT_BOLD),
        ('FONTNAME', (0, 1), (-1, -1), FONT_REGULAR),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f0fdfa')),
    ]))
    elements.append(vis_table)
    elements.append(Spacer(1, 0.3 * inch))

    # ── TABLE 3: Excitement Quotient Summary ──
    elements.append(h1(P2["excitement_title"]))
    if _saved_segments:
        exc_data = [
            [P2["segment"], P2["time_range"], P2["excitement"], P2["audio"], P2["cut"], P2["motion"]]
        ]
        for idx, seg in enumerate(_saved_segments[:5], 1):
            s_start = seg.get("start_sec", 0)
            s_end = seg.get("end_sec", 0)
            time_str = f"{int(s_start//60)}:{int(s_start%60):02d} — {int(s_end//60)}:{int(s_end%60):02d}"
            exc_data.append([
                f"#{idx}",
                time_str,
                f"{seg.get('excitement_score', 0)}/10",
                f"{seg.get('audio_intensity', 0)}/10",
                f"{seg.get('cut_density', 0)}/10",
                f"{seg.get('motion_intensity', 0)}/10",
            ])
        exc_table = Table(exc_data, colWidths=[0.6*inch, 1.4*inch, 0.9*inch, 0.9*inch, 0.9*inch, 0.9*inch])
        exc_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#b91c1c')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), FONT_BOLD),
            ('FONTNAME', (0, 1), (-1, -1), FONT_REGULAR),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#fef2f2')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#fef2f2'), colors.HexColor('#fee2e2')]),
        ]))
        elements.append(exc_table)
    else:
        elements.append(Paragraph(f"<font color='#94a3b8'><em>{P2['no_segments']}</em></font>", normal_s))
    elements.append(Spacer(1, 0.3 * inch))

    # ── 6. Comparison Chart ──
    elements.append(PageBreak())
    elements.append(h1(L['comparison_title']))

    def safe_float(val):
        return float(val) if val is not None else 0.0

    avg_overall = safe_float(averages['avg_overall'])
    avg_ret = safe_float(averages['avg_retention'])
    avg_tech = safe_float(averages['avg_tech'])
    avg_seo = safe_float(averages['avg_seo'])
    avg_thumb = safe_float(averages['avg_thumb'])

    hdrs = L['comparison_headers']
    table_data = [
        hdrs,
        [L['col_overall'], f"{overall:.1f}", f"{avg_overall:.1f}", f"{overall - avg_overall:.1f}"],
        [L['col_retention'], f"{retention:.1f}", f"{avg_ret:.1f}", f"{retention - avg_ret:.1f}"],
        [L['col_tempo'], f"{tech:.1f}", f"{avg_tech:.1f}", f"{tech - avg_tech:.1f}"],
        [L['col_seo'], f"{seo:.1f}", f"{avg_seo:.1f}", f"{seo - avg_seo:.1f}"],
        [L['col_thumbnail'], f"{thumb:.1f}", f"{avg_thumb:.1f}", f"{thumb - avg_thumb:.1f}"]
    ]
    table = Table(table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('FONTNAME', (0, 0), (-1, 0), FONT_BOLD),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12), ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black), ('FONTNAME', (0, 1), (-1, -1), FONT_REGULAR)
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.5 * inch))

    # ── AI Coach ──
    coach_elements = []
    coach_elements.append(h1(L['coach_title'].replace('🥊', '').strip()))
    feedback_from_db = analysis['coach_feedback']
    if feedback_from_db:
        coach_elements.append(h2(L['coach_analysis'].replace('🤖', '').strip()))
        coach_elements.append(Paragraph(esc(feedback_from_db), normal_s))
        coach_elements.append(Spacer(1, 0.2 * inch))

    reasons, actions, positives = [], [], []
    if thumb > 0.0:
        if face_detected:
            positives.append(L['face_ok'])
        else:
            reasons.append(L['face_missing'])
            actions.append(L['face_action'])
    if retention < 6.5:
        reasons.append(L['retention_low'])
        actions.append(L['retention_action'])
    else:
        positives.append(L['retention_ok'].format(score=retention))
    if tech < 7.0:
        reasons.append(L['tech_low'].format(peaks=peaks))
        actions.append(L['tech_action'])
    else:
        positives.append(L['tech_ok'].format(peaks=peaks))
    if seo < 6.0:
        reasons.append(L['seo_low'].format(seo=seo))
        actions.append(L['seo_action'])
    elif seo >= 8.0:
        positives.append(f"SEO optimization is very strong (Score: {seo:.1f}/10)")
        
    cr = _saved_thumb.get("contrast_ratio", 0)
    if cr >= 0.5:
        positives.append(f"Thumbnail contrast is excellent ({cr:.2f}), eye-catching")

    reasons_text = "\n".join([f"• {r}" for r in reasons]) or L['no_weak']
    actions_text = "\n".join([f"• {a}" for a in actions]) or L['no_action']
    positives_text = "\n".join([f"• {p}" for p in positives]) or L['no_strong']

    def esc_nl(s):
        return esc(s).replace(chr(10), '<br/>')

    coach_content = (
        f"<b>{L['weak_points']}:</b><br/>{esc_nl(reasons_text)}<br/><br/>"
        f"<b>{L['urgent_actions']}:</b><br/>{esc_nl(actions_text)}<br/><br/>"
        f"<b>{L['strong_points']}:</b><br/>{esc_nl(positives_text)}"
    )
    coach_elements.append(Paragraph(coach_content, normal_s))
    coach_elements.append(Spacer(1, 0.4 * inch))

    elements.append(KeepTogether(coach_elements))

    # ── Duration footnote ──
    try:
        raw_dur = analysis['analysis_duration_sec']
        dur_sec = float(raw_dur) if raw_dur else 0.0
    except Exception:
        dur_sec = 0.0

    if dur_sec > 0:
        mins = int(dur_sec // 60)
        secs_val = int(dur_sec % 60)
        if mins > 0:
            dur_str = L['duration_min'].format(m=mins, s=secs_val)
        else:
            dur_str = L['duration_sec'].format(s=secs_val)
        elements.append(Spacer(1, 0.3 * inch))
        elements.append(Paragraph(
            f"<font size=8 color='#888888'>{L['duration_note'].format(dur=dur_str, sec=f'{dur_sec:.1f}')}</font>",
            normal_s
        ))

    doc.build(elements)
    safe_video_title = re.sub(r'[^\w\-]', '_', video_name_str)[:30]
    return FileResponse(pdf_path, media_type="application/pdf", filename=f"analysis_report_{safe_video_title}_{analysis_id}.pdf")


@app.get("/export_channel_pdf/{channel_id}")
async def export_channel_pdf(channel_id: int, lang: str = "tr"):
    if lang not in PDF_LANG or not PDF_LANG[lang]:
        lang = "tr"
    L = PDF_LANG[lang]
    def esc(txt):
        if txt is None:
            return ""
        s = str(txt)
        s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        s = s.replace('"', "").replace("'", "")
        return s

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM channels WHERE id=?", (channel_id,))
    channel = c.fetchone()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    c.execute("SELECT video_name, overall_score, retention_score, tech_score, seo_score, timestamp FROM analyses WHERE channel_id=? ORDER BY timestamp DESC", (channel_id,))
    analyses = c.fetchall()
    avgs = await AnalysisEngine.get_channel_averages(channel_id)
    conn.close()

    pdf_path = output_dir / f"kanal_raporu_{channel_id}_{lang}.pdf"
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    title_s, heading_s, normal_s = styles['Title'], styles['Heading2'], styles['Normal']
    title_s.fontName, heading_s.fontName, normal_s.fontName = FONT_BOLD, FONT_BOLD, FONT_REGULAR

    elements.append(Paragraph(f"{L['channel_report_title']}: {esc(channel[1])}", title_s))
    elements.append(Spacer(1, 0.2 * inch))
    elements.append(Paragraph(L['channel_avg_title'], heading_s))

    def safe_float(val):
        return float(val) if val is not None else 0.0

    avg_data = [
        [L['col_overall'], L['col_retention'], L['col_tempo'], L['col_seo'], L['col_thumbnail']],
        [str(safe_float(avgs['avg_overall'])), str(safe_float(avgs['avg_retention'])),
         str(safe_float(avgs['avg_tech'])), str(safe_float(avgs['avg_seo'])), str(safe_float(avgs['avg_thumb']))]
    ]
    t1 = Table(avg_data, colWidths=[1.2 * inch] * 5)
    t1.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.black), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (-1, -1), FONT_BOLD)
    ]))
    elements.append(t1)
    elements.append(Spacer(1, 0.4 * inch))
    elements.append(Paragraph(L['video_history_title'], heading_s))

    if analyses:
        hist_data = [[L['col_video'], L['col_date'], L['col_overall'], L['col_retention'], L['col_tempo'], L['col_seo']]]
        for a in analyses:
            date_str = str(a[5]).split()[0]
            v_name = (esc(a[0][:20]) + '..') if len(a[0]) > 20 else esc(a[0])
            vals = [str(safe_float(x)) for x in a[1:5]]
            hist_data.append([v_name, date_str, vals[0], vals[1], vals[2], vals[3]])
        t2 = Table(hist_data, colWidths=[2 * inch, 1 * inch, 0.8 * inch, 0.8 * inch, 0.8 * inch, 0.8 * inch])
        t2.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6b21a8')), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 0), (-1, 0), FONT_BOLD), ('FONTNAME', (0, 1), (-1, -1), FONT_REGULAR)
        ]))
        elements.append(t2)
    else:
        elements.append(Paragraph(L['no_analysis'], normal_s))

    doc.build(elements)
    safe_name = re.sub(r'[^\w\-]', '_', str(channel[1]))[:30]
    return FileResponse(pdf_path, media_type="application/pdf", filename=f"channel_report_{safe_name}_{channel_id}.pdf")


@app.get("/api/session")
async def get_session():
    db = await get_async_db()
    try:
        async with db.execute("SELECT value FROM app_settings WHERE key='active_session'") as cursor:
            row = await cursor.fetchone()
        if row and row[0]:
            try:
                return {"session": json.loads(row[0])}
            except Exception as e:
                app_logger.warning(f"Error [get_session json load]: {e}")
        return {"session": None}
    finally:
        await db.close()


@app.post("/api/session")
async def save_session(request: Request):
    data = await request.json()
    user_id = data.get("user_id")
    username = data.get("username")
    if not user_id or not username:
        return {"success": False}
    session_data = json.dumps({"user_id": user_id, "username": username})
    db = await get_async_db()
    try:
        await db.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES ('active_session', ?)", (session_data,))
        await db.commit()
    finally:
        await db.close()
    return {"success": True}


@app.delete("/api/session")
async def clear_session():
    db = await get_async_db()
    try:
        await db.execute("DELETE FROM app_settings WHERE key='active_session'")
        await db.commit()
    finally:
        await db.close()
    return {"success": True}


@app.get("/api/settings/groq")
async def get_groq_key():
    db = await get_async_db()
    try:
        async with db.execute("SELECT value FROM app_settings WHERE key='groq_api_key'") as cursor:
            row = await cursor.fetchone()
        return {"has_key": bool(row and row[0])}
    finally:
        await db.close()


@app.post("/api/settings/groq")
async def set_groq_key(key: str = Form(...)):
    if key.strip() == "(saved)":
        return {"success": True}
    db = await get_async_db()
    try:
        await db.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES ('groq_api_key', ?)", (CryptoManager.encrypt(key.strip()),))
        await db.commit()
    finally:
        await db.close()
    return {"success": True}


@app.get("/api/settings/smtp")
async def get_smtp_settings():
    db = await get_async_db()
    try:
        async with db.execute("SELECT key, value FROM app_settings WHERE key IN ('smtp_email', 'smtp_password')") as cursor:
            rows = {r[0]: r[1] async for r in cursor}
        return {"has_smtp": bool(rows.get('smtp_email') and rows.get('smtp_password')),
                "smtp_email": rows.get('smtp_email', '')}
    finally:
        await db.close()


@app.post("/api/settings/smtp")
async def set_smtp_settings(request: Request):
    try:
        data = await request.json()
        email = data.get("email", "").strip()
        password = data.get("password", "").strip()
        if not email or not password:
            return {"success": False, "error": "Email and password cannot be empty."}
        db = await get_async_db()
        try:
            await db.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES ('smtp_email', ?)", (email,))
            await db.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES ('smtp_password', ?)", (CryptoManager.encrypt(password),))
            await db.commit()
        finally:
            await db.close()
        return {"success": True}
    except Exception:
        return {"success": False, "error": "Save error."}


@app.get("/api/chat/sessions")
async def get_chat_sessions(user_id: int = 1):
    db = await get_async_db()
    try:
        async with db.execute("""
            SELECT s.id, s.title, s.created_at,
                COUNT(m.id) as msg_count
            FROM chat_sessions s
            LEFT JOIN chat_messages m ON m.session_id = s.id
            WHERE s.user_id = ?
            GROUP BY s.id
            ORDER BY s.created_at DESC
            LIMIT 50
        """, (user_id,)) as cursor:
            rows = await cursor.fetchall()
        return [{"id": r[0], "title": r[1], "created_at": r[2], "msg_count": r[3]} for r in rows]
    finally:
        await db.close()


@app.post("/api/chat/sessions")
async def create_chat_session(request: Request):
    data = await request.json()
    title = data.get("title", "New Chat")[:80]
    user_id = data.get("user_id", 1)
    db = await get_async_db()
    try:
        await db.execute("INSERT INTO chat_sessions (title, user_id) VALUES (?, ?)", (title, user_id))
        await db.commit()
        async with db.execute("SELECT last_insert_rowid()") as cursor:
            row = await cursor.fetchone()
            sid = row[0]
    finally:
        await db.close()
    return {"id": sid, "title": title}


@app.put("/api/chat/sessions/{session_id}")
async def rename_chat_session(session_id: int, request: Request):
    data = await request.json()
    title = data.get("title", "Chat")[:80]
    user_id = data.get("user_id", 1)
    db = await get_async_db()
    try:
        await db.execute("UPDATE chat_sessions SET title=? WHERE id=? AND user_id=?", (title, session_id, user_id))
        await db.commit()
    finally:
        await db.close()
    return {"success": True}


@app.delete("/api/chat/sessions/{session_id}")
async def delete_chat_session(session_id: int, user_id: int = 1):
    db = await get_async_db()
    try:
        await db.execute("DELETE FROM chat_messages WHERE session_id=? AND session_id IN (SELECT id FROM chat_sessions WHERE user_id=?)", (session_id, user_id))
        await db.execute("DELETE FROM chat_sessions WHERE id=? AND user_id=?", (session_id, user_id))
        await db.commit()
    finally:
        await db.close()
    return {"success": True}


@app.get("/api/chat/sessions/{session_id}/messages")
async def get_session_messages(session_id: int, user_id: int = 1):
    db = await get_async_db()
    try:
        # Verify that the session belongs to this user
        async with db.execute("SELECT id FROM chat_sessions WHERE id=? AND user_id=?", (session_id, user_id)) as cursor:
            if not await cursor.fetchone():
                return []
        async with db.execute("SELECT sender, text FROM chat_messages WHERE session_id=? ORDER BY created_at ASC", (session_id,)) as cursor:
            rows = await cursor.fetchall()
        return [{"sender": r[0], "text": r[1]} for r in rows]
    finally:
        await db.close()


@app.post("/api/chat/sessions/{session_id}/messages")
async def save_session_message(session_id: int, request: Request):
    data = await request.json()
    sender = data.get("sender", "user")
    text = data.get("text", "")
    if not text:
        return {"success": False}
    db = await get_async_db()
    try:
        await db.execute("INSERT INTO chat_messages (session_id, sender, text) VALUES (?,?,?)", (session_id, sender, text))
        await db.commit()
    finally:
        await db.close()
    return {"success": True}


@app.post("/api/chat")
async def ai_chat(request: Request):
    data = await request.json()
    history = data.get("history", [])
    ch_type = data.get("channel_type", "Genel")
    context = data.get("analysis_context", "")
    channel_id = data.get("channel_id", None)

    db = await get_async_db()
    try:
        async with db.execute("SELECT value FROM app_settings WHERE key='groq_api_key'") as cursor:
            row = await cursor.fetchone()
            
        channel_rules_text = ""
        past_feedbacks_text = ""
        if channel_id:
            try:
                async with db.execute("SELECT channel_rules FROM channels WHERE id=?", (channel_id,)) as rules_cursor:
                    rules_row = await rules_cursor.fetchone()
                    if rules_row and rules_row[0]:
                        channel_rules_text = rules_row[0].strip()
            except Exception:
                pass
            try:
                async with db.execute("""
                    SELECT coach_feedback FROM analyses
                    WHERE channel_id=? AND coach_feedback IS NOT NULL AND coach_feedback != ''
                    ORDER BY timestamp DESC LIMIT 5
                """, (channel_id,)) as fb_cursor:
                    fb_rows = await fb_cursor.fetchall()
                    if fb_rows:
                        feedbacks = [r[0] for r in fb_rows if r[0]]
                        if feedbacks:
                            past_feedbacks_text = "\\n".join(
                                [f"[{i+1}] {fb[:300]}" for i, fb in enumerate(reversed(feedbacks))]
                            )
            except Exception:
                pass
    finally:
        await db.close()

    api_key = CryptoManager.decrypt(row[0]) if row and row[0] else ""
    if not api_key:
        return {"error": "NO_KEY", "details": "API key not found. Please enter your Groq API key."}

    attached_file = data.get("attached_file", None)
    file_context = ""
    file_mime = ""
    file_base64 = ""
    file_name = "dosya"
    if attached_file:
        file_type = attached_file.get("type", "")
        file_base64 = attached_file.get("base64", "")
        file_mime = attached_file.get("mime_type", "")
        file_name = attached_file.get("name", "dosya")
        # print(f"ATTACHED FILE: type={file_type}, mime={file_mime}, name={file_name}, b64len={len(file_base64)}")
        if file_type == "image" and file_base64:
            file_context = await analyze_image_with_gemini(file_base64, file_mime)
        elif file_base64:
            try:
                import base64 as b64mod
                decoded_bytes = b64mod.b64decode(file_base64)
                if file_mime == "application/pdf" or file_name.lower().endswith(".pdf"):
                    file_context = await analyze_image_with_gemini(file_base64, "application/pdf")
                else:
                    decoded = decoded_bytes.decode('utf-8', errors='ignore')
                    file_context = f"File uploaded by user ({file_name}):\n{decoded[:3000]}"
            except Exception as e:
                # print(f"FILE PARSE ERROR: {e}")
                file_context = ""
        # print(f"FILE_CONTEXT RESULT: {len(file_context)} characters")

    has_analysis = bool(context and context.strip())

    last_user_msg = ""
    for msg in reversed(history):
        if msg.get("sender") == "user" and not msg.get("isTyping"):
            last_user_msg = msg.get("text", "")
            break

    last_user_msg_lower = last_user_msg.lower()
    title_keywords = ["başlık", "title", "isim", "name", "ne yazayım", "nasıl adlandır", "başlık öner", "başlık yaz"]  # bilingual intent keywords — do not translate
    is_title_question = any(kw in last_user_msg_lower for kw in title_keywords)

    analysis_block = f"User's latest analysis:\n{context}" if has_analysis else "The user has not performed any video analysis yet."

    if file_context:
        analysis_block += f"\n\nUser uploaded additional data for analysis:\n{file_context}"

    if file_context:
        print(f"FILE_CONTEXT PREVIEW: {file_context[:500]}")

    file_uploaded_note = ""
    if file_context:
        file_uploaded_note = """
IMPORTANT: The user has uploaded an image or data file containing YouTube analytics. The extracted data is in the analysis block above under 'User uploaded additional data'.
FILE ANALYSIS PROTOCOL:
1. STRICT FACTS: Read the exact numbers from the data. DO NOT hallucinate numbers (e.g., if it says 3:28, do not invent 6:22). Re-state the actual metrics given.
2. Visualize the Data: Treat the text data as a visual graph in your mind (e.g., Retention graph).
3. Numerical Citations: Do not use generic phrases like "Viewers are leaving". Give specific points like "The sharp 40% drop seen at the 15th second...". Use the precise times and percentages provided.
4. Diagnosis and Cure: Explain the reason for the performance metric (low tempo, unfulfilled promise, etc.) and write a targeted Hook scenario.
5. Hook Rules: Every hook you suggest must strictly include: a Scenario script, a Psychological Trigger, and an On-Screen Visual instruction.
6. Goal: 90%+ target retention rate in the first 30 seconds."""

    title_instruction = ""
    if is_title_question:
        title_instruction = """
TITLE QUESTION RULE — This message is about a title. At the very end of your response, add the following format:
---
💡 My Title Suggestions:
1. [Suggestion 1]
2. [Suggestion 2]
3. [Suggestion 3]
---
Titles should be short, curiosity-inducing and between 50-70 characters."""

    no_analysis_instruction = ""
    if not has_analysis and not file_context:
        no_analysis_instruction = """
NO ANALYSIS RULE — The user has not analyzed any video yet. At the very end of each response add (in the user's language):
---
📊 If you upload your video to YouTube Analytics Pro, I could give you a precise, personalized answer — I'd be able to show you exactly when viewers drop off, your SEO score and competitor comparison.
---"""

    # --- MEMORY SYSTEM: Create memory block ---
    memory_block = ""
    if channel_rules_text:
        memory_block += f"\\n\\n🔒 FIXED CHANNEL RULES (Follow these rules STRICTLY, never break them):\\n{channel_rules_text}"
    if past_feedbacks_text:
        memory_block += f"\\n\\n📚 PAST ANALYSIS NOTES (Last 5 analysis coach comments, oldest to newest):\\n{past_feedbacks_text}"

    system_prompt = f"""IDENTITY: You are 'Analiz Pro AI: Stratejik Veri Analisti' (Strategic Data Analyst) — an elite, data-driven and candid YouTube strategist who advises rather than commands.
Channel Type: {ch_type}
{analysis_block}{memory_block}

⚠️ CRITICAL LANGUAGE RULE:
Detect the exact language of the user's message and respond EXCLUSIVELY in that same language. (User TR -> Respond TR, User EN -> Respond EN, User ES -> Respond ES). NEVER mix languages.

🧠 STRATEGY AND DATA PROCESSING DIRECTIVES:
1. BE DATA-PRECISE: Use the provided analytics (Retention, SEO, Tempo) like a surgeon. If the "Excitement Score" is low or there are "Dead Zones", name the exact timestamps and offer a concrete option for each. Be honest about the data — do not sugarcoat the diagnosis, but keep the remedy a suggestion.
2. VISUAL INTELLIGENCE FILTER: You MUST use the visual data in your strategy:
   - CONTRAST: If contrast is low, tell them it may be hard to read on mobile and offer specific complementary colors (e.g., Purple/Yellow) they could try.
   - EXCITEMENT SCORE & CUTS: Use the scene cut frequency and motion data to offer editing options like "you could add a dynamic zoom here" or "cutting roughly every 4 seconds might keep the pace up".
3. ELITE TONE: Speak like a top-tier strategist managing millions of subscribers. Be direct, specific and useful, use bullet points, **bold** key terms, no unnecessary fluff — but frame every recommendation as an option the creator can take or leave.
4. MANDATORY HOOKS (ANTI-GENERIC): If addressing viewer drop-offs (retention), you MUST provide a specific Hook Formula: 1. Spoken Script, 2. Psychological Trigger, 3. On-Screen Visual Action. NEVER say "surprise them in the first 10 seconds" or "ilk 10 saniyede şaşırt". You must answer HOW exactly with a concrete scenario.
5. BOUNDARIES: You ONLY discuss YouTube algorithms, content strategy, video pacing, and SEO. Reject all off-topic questions by stating your role.
6. NO-HALLUCINATION RULE: Use ONLY the provided Channel Type and Purpose for your strategy. DO NOT suggest random games or content types that were not explicitly provided in the input context. If you do not know the answer to a question, explicitly state "I don't know" (veya "Bilmiyorum"). NEVER make up information or give wrong answers.
7. STRENGTH RECOGNITION: Do not just focus on weaknesses. If SEO score is high, thumbnail contrast is excellent, or retention is stable in the middle, explicitly acknowledge these as strong points.
8. TAG PROTECTION: Never dismiss user tags as irrelevant unless they truly violate YouTube terms. Recognize specific niche tags (like "left 4 dead 2 türkçe" or "komik oyun videoları") as positive targeted keywords.
9. ⚠️ KANAL KURALLARI: Eğer yukarıda 'SABİT KANAL KURALLARI' bölümü varsa, bu kurallar mutlak önceliğe sahiptir. Bu kurallara KESİNLİKLE uy ve hiçbir öneri bu kurallara aykırı olmasın.

10. THUMBNAIL ANALİZ VE HALÜSİNASYON YASAĞI:
    - Mevcut thumbnail'de bir yüz olduğunu VARSAYMAK KESİNLİKLE YASAKTIR.
    - Eğer thumbnail'de gerçekten bir insan yüzü olduğunu kanıtlayan somut bir veri yoksa, 'mutlu yüz', 'kameraya bakıyor', 'şaşırmış surat' gibi jenerik ve sahte ifadeleri ASLA kullanma.
    - Kanal tipi ({ch_type}) bir gaming/aksiyon kanalıysa 'şaşırmış insan yüzü' yerine her zaman: Yüksek kontrastlı oyun içi aksiyon sahneleri, parlayan epik karakterler veya araçlar, dramatik alev/patlama efektleri, büyük ve keskin tipografi önerilmelidir.
    - Gördüğün ekran görüntüsünde (SS) yüz yoksa, 'yüz var' demek yerine dürüstçe görsel tempoyu ve kontrastı analiz et.
    - IMPORTANT: DO NOT describe generic thumbnail elements. Describe the actual visual energy that fits the channel's content type ({ch_type}).
11. RAKİP ANALİZİ VE ÖNERİSİ:
    - Kullanıcının kendi kanalını rakip olarak ASLA önerme. Rakip analizleri her zaman harici kanallar üzerinden yapılmalıdır.

12. {ADVISORY_TONE_RULE}

{title_instruction}
{no_analysis_instruction}
{file_uploaded_note}"""

    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        if msg.get("isTyping"):
            continue
        role = "assistant" if msg.get("sender") == "bot" else "user"
        text = msg.get("text", "")
        if text and not text.startswith("⚠️"):
            messages.append({"role": role, "content": text})

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": messages,
                "max_tokens": 1024,
                "temperature": 0.7
            },
            timeout=20
        )

        res_data = resp.json()

        if resp.status_code != 200:
            err = res_data.get("error", {}).get("message", "Bilinmeyen hata")
            if resp.status_code == 401:
                return {"error": "INVALID_KEY", "details": "Your API key is invalid."}
            if resp.status_code == 429:
                return {"error": "QUOTA", "details": "Quota exceeded. Please wait a moment."}
            return {"error": "API_ERROR", "details": f"Groq error: {err}"}

        reply = res_data["choices"][0]["message"]["content"]
        return {"reply": reply}

    except requests.exceptions.Timeout:
        return {"error": "TIMEOUT", "details": "Server did not respond. Please try again."}
    except Exception as e:
        return {"error": "NETWORK_ERROR", "details": f"Connection error: {str(e)}"}

@app.post("/api/send_report")
async def api_send_report(request: Request):
    """Manual report dispatch — triggered by the 'Resend Report' button on the results screen."""
    data = await request.json()
    analysis_id = data.get("analysis_id")
    user_id = data.get("user_id", 1)
    req_lang = data.get("lang", "tr")
    if not analysis_id:
        return {"success": False, "error": "Analiz ID eksik."}
    try:
        conn = get_db()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT video_name FROM analyses WHERE id=?", (analysis_id,))
        a_row = c.fetchone()
        c.execute("SELECT email FROM users WHERE id=?", (user_id,))
        u_row = c.fetchone()
        conn.close()
        if not a_row or not u_row or not u_row['email']:
            return {"success": False, "error": "User email not found."}

        # Create the PDF first (simulate export_pdf endpoint)
        pdf_path = str(output_dir / f"report_{analysis_id}_{req_lang}.pdf")
        if not os.path.exists(pdf_path):
            # If PDF is not available, pull from local URL
            import urllib.request
            try:
                urllib.request.urlretrieve(
                    f"http://127.0.0.1:8000/export_pdf/{analysis_id}?lang={req_lang}",
                    pdf_path
                )
            except Exception:
                pass

        video_name = a_row['video_name']
        user_email = u_row['email']
        sent = await run_in_threadpool(send_report_email, user_email, pdf_path, video_name, req_lang)
        if sent:
            return {"success": True, "message": "Report sent to your email!"}
        else:
            return {"success": False, "error": "SMTP settings are incomplete or sending failed."}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/translations")
async def get_translations():
    # Search order: BUNDLE_DIR → APP_DIR → BASE_DIR (PyInstaller and dev mode compatible)
    search_paths = [
        BUNDLE_DIR / 'translations.xlsx',
        APP_DIR    / 'translations.xlsx',
        BASE_DIR   / 'translations.xlsx',
    ]

    xlsx_path = None
    for candidate in search_paths:
        if candidate.exists():
            xlsx_path = candidate
            break

    if xlsx_path is None:
        tried = [str(p) for p in search_paths]
        app_logger.error(
            f"[translations] translations.xlsx not found! "
            f"Aranan yollar: {tried}"
        )
        return {
            'error': f"translations.xlsx not found. Searched paths: {tried}",
            'tr': {}, 'en': {}, 'es': {}
        }

    try:
        app_logger.info(f"[translations] Loading: {xlsx_path}")
        df = pd.read_excel(str(xlsx_path), sheet_name='ui', dtype=str).fillna('')
        result = {'tr': {}, 'en': {}, 'es': {}}
        for _, row in df.iterrows():
            key = str(row['key']).strip()
            if not key:
                continue
            for lang in ['tr', 'en', 'es']:
                if lang in df.columns:
                    result[lang][key] = str(row[lang]).strip()
        app_logger.info(
            f"[translations] ✅ Loaded: {len(result.get('tr', {}))} keys "
            f"({xlsx_path.name})"
        )
        return result
    except Exception as e:
        app_logger.error(
            f"[translations] translations.xlsx okunurken hata! "
            f"File: {xlsx_path} | Error type: {type(e).__name__} | Detail: {e}",
            exc_info=True
        )
        return {
            'error': f"Translation file could not be read: {type(e).__name__}: {e}",
            'tr': {}, 'en': {}, 'es': {}
        }


@app.get("/api/test/gemini-models")
async def test_gemini_models():
    db = await get_async_db()
    try:
        async with db.execute("SELECT value FROM app_settings WHERE key='gemini_api_key'") as cursor:
            row = await cursor.fetchone()
    finally:
        await db.close()
    gemini_key = row[0] if row and row[0] else ""
    resp = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={gemini_key}")
    return resp.json()


@app.get("/api/test/gemini-ping")
async def test_gemini_ping():
    db = await get_async_db()
    try:
        async with db.execute("SELECT value FROM app_settings WHERE key='gemini_api_key'") as cursor:
            row = await cursor.fetchone()
    finally:
        await db.close()
    gemini_key = row[0] if row and row[0] else ""
    payload = {"contents": [{"parts": [{"text": "Say hello"}]}]}
    resp = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}",
        json=payload,
        timeout=10
    )
    return {"status": resp.status_code, "body": resp.text[:300]}



# ═══════════════════════════════════════════════════════════
# VIRAL CLONING ENGINE — Chrome Extension Integration
# ═══════════════════════════════════════════════════════════

def _fetch_transcript_sync(video_id: str) -> str:
    # Stage 1: Pull all subtitles with YouTubeTranscriptApi (First choice)
    last_api_error = "YouTubeTranscriptApi not available"  # NameError guard
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        if hasattr(YouTubeTranscriptApi, 'list_transcripts'):
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        else:
            api_instance = YouTubeTranscriptApi()
            transcript_list = api_instance.list(video_id)
            
        transcript = None
        for lang in ['tr', 'en', 'es', 'de', 'fr']:
            try:
                transcript = transcript_list.find_transcript([lang])
                break
            except:
                continue
        if transcript is None:
            transcript = next(iter(transcript_list))
        entries = transcript.fetch()
        return " ".join([t.get('text', '') for t in entries])
    except Exception as api_err:
        last_api_error = str(api_err)
        
    # Step 2: If youtube-transcript-api gives an error (eg: XML Parse Error), FORCED PULL with yt-dlp
    try:
        import yt_dlp
        import requests
        import json
        import re
        
        ydl_opts = {
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['tr', 'en', 'es', 'de', 'fr', '.*'],
            'subtitlesformat': 'json3/vtt/srt',
            'quiet': True,
            'no_warnings': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_id, download=False)
            subs = info.get('requested_subtitles')
            if not subs:
                # If yt-dlp cannot find subtitles, return the first library's error
                raise ValueError(last_api_error)
            
            # First, search for the languages ​​we want
            target_sub = None
            for lang in ['tr', 'en', 'es', 'de', 'fr']:
                if lang in subs:
                    target_sub = subs[lang]
                    break
            
            # If you can't find it, take the first language that comes up.
            if not target_sub:
                target_sub = next(iter(subs.values()))
            
            sub_url = target_sub.get('url')
            if not sub_url:
                raise ValueError(last_api_error)
            
            # Request the subtitle URL
            resp = requests.get(sub_url, timeout=15)
            if resp.status_code != 200:
                raise ValueError(last_api_error)
                
            text_data = resp.text
            
            # YouTube usually returns subtitles in JSON3 format
            if 'events' in text_data:
                try:
                    data = json.loads(text_data)
                    texts = []
                    for event in data.get('events', []):
                        if 'segs' in event:
                            for seg in event['segs']:
                                if 'utf8' in seg:
                                    texts.append(seg['utf8'])
                    if texts:
                        return " ".join(texts).replace('\n', ' ').replace('\r', '')
                except:
                    pass
            
            # Clear if VTT format
            clean_lines = []
            for line in text_data.split('\n'):
                line = line.strip()
                if not line or '-->' in line or line.isdigit() or line.startswith('WEBVTT') or line.startswith('Kind:') or line.startswith('Language:') or line.startswith('Style:'):
                    continue
                # Delete tags such as <c>, <00:00:00.000> in VTT with regex
                line = re.sub(r'<[^>]+>', '', line)
                if line:
                    clean_lines.append(line)
            
            result = " ".join(clean_lines)
            if result.strip():
                return result
            raise ValueError(last_api_error)
            
    except Exception as e:
        # Return errors as a last resort
        raise ValueError(f"Subtitle could not be fetched. API Error: {last_api_error} | Fallback Engine Error: {e}")


# ── Thumbnail Rule: Create dynamically according to content type ─────────────────────
# BUG FIX: Human face PROHIBITED directive for gaming channels.
# The main AI (chat) prompt included this rule, but inside _call_groq_clone
# It wasn't cascade — so the hallucination was being produced. It's now fixed.
def _build_thumbnail_rule(content_type: str) -> str:
    """Returns a thumbnail directive based on content_type."""
    gaming_keywords = ['oyun', 'gaming', 'game', 'fps', 'rpg', 'minecraft', 'valorant',
                       'left 4 dead', 'cod', 'gta', 'esport', 'turnuva']
    is_gaming = any(kw in content_type.lower() for kw in gaming_keywords)

    if is_gaming:
        return (
            "3. ABSOLUTE THUMBNAIL RULE — GAMING CHANNEL: "
            "This is a GAMING channel. Human faces are STRICTLY FORBIDDEN in thumbnail descriptions. "
            "NEVER write phrases like 'mutlu bir yüz', 'yüze bakıyor', 'insan yüzü', 'shocked face', or any face/emotion reference. "
            "If you hallucinate a face that does not exist, your output is INVALID. "
            "Instead, focus ONLY on: game UI elements, dramatic in-game moments, bold text overlays, "
            "high-contrast character/item art, explosive effects, or controller/keyboard imagery. "
            "The 'thumbnail' field MUST be a detailed TEXT DESCRIPTION — NEVER a URL or image link."
        )
    else:
        return (
            "3. CRITICAL THUMBNAIL RULE: NEVER generate fake image URLs or links. "
            "The 'thumbnail' field MUST contain a detailed text description of the thumbnail design. "
            "Example: \"Arka planda patlayan bir araba, önde şaşkın bir ifade ve büyük sarı harflerle 'BUNU BEKLEMİYORDUK!' yazısı.\""
        )


async def _call_groq_clone(
    api_key: str, title: str, channel: str, transcript: str,
    content_type: str, purpose: str, views: int = 0,
    tier: str = None, time_window: str = None,
    velocity_per_day: float = None, penetration_ratio: float = None,
    comment_signals: str = None,
    lang: str = "tr",
) -> str:
    """
    Generates a viral cloning concept using Groq Llama-3.
    Wraps the synchronous requests call with run_in_threadpool.
    """
    thumbnail_rule = _build_thumbnail_rule(content_type)

    prompt = f"""Sen üst düzey bir YouTube Algoritma Uzmanı ve Viral İçerik Stratejistisin. 

KULLANICI PROFİLİ: 
Kullanıcının kanal tipi: {content_type}. Kanalın amacı: {purpose}.

GÖREVİN: 
Sana verilen orijinal video başlığı ve altyazı (transcript) verilerini analiz ederek, bu videonun başarısını klonlayacak 3 yeni, özgün ve yüksek potansiyelli video fikri üretmek.

📌 Orijinal Başlık: {title}
📺 Orijinal Kanal: {channel}
📝 Senaryo (ilk 2000 karakter):
{transcript[:2000] if transcript else "Altyazı bulunamadı. Sadece başlığa göre analiz yap."}

{ADVISORY_TONE_RULE_CREATIVE}

KURALLAR:
1. VİRAL ANATOMİ: Videonun neden viral olduğunu (psikolojik tetikleyici ve kanca) analiz et.
2. FİKİR ÜRETİMİ: Orijinal videonun ruhunu kopyalayan 3 farklı video fikri sun.
{thumbnail_rule}
3. NİŞ UYARISI: Analiz ettiğin video, kullanıcının \"{content_type}\" konseptiyle uyuşmuyorsa bir uyarı metni yaz. Uyuşuyorsa boş bırak.
4. KESİN FORMAT KURALI: Çıktın KESİNLİKLE bir dizi (array) [...] OLAMAZ. Çıktın KESİNLİKLE bir obje (object) {{...}} olmak zorundadır. Objenin içinde "viral_anatomi", "nis_uyarisi" ve "fikirler" anahtarları ZORUNLUDUR. SADECE AŞAĞIDAKİ JSON FORMATINDA ÇIKTI VER (Başka hiçbir düz metin yazma):
{{
  "viral_anatomi": "Videonun neden patladığını anlatan 2-3 cümlelik psikolojik analiz.",
  "nis_uyarisi": "Oyun/kaos dışındaysa uyarı metni, yoksa boş string",
  "fikirler": [
    {{
       "title": "...",
       "hook": "...",
       "thumbnail": "..."
    }}
  ]
}}"""

    # -- Predictive Intelligence (one time injection) --
    _eff_tier = tier or ("mega_viral" if views >= 100_000 else "viral" if views >= 5_000 else "potential" if views >= 500 else "dead")
    _pi_ctx = _build_pi_context(tier=_eff_tier, time_window=time_window,
        velocity_per_day=velocity_per_day, penetration_ratio=penetration_ratio,
        comment_signals=comment_signals, views=views)
    if _pi_ctx:
        prompt = _pi_ctx + "\n\n" + prompt

    # ── i18n Directive ── lang='en' ise İngilizce yanıt zorunlu kılınır
    _lang_directive = (
        "\n\nIMPORTANT: Provide ALL your analysis, titles, hooks, thumbnails, "
        "viral_anatomi, nis_uyarisi, and every text field in the JSON output "
        "in ENGLISH language. Do not use Turkish."
        if lang == "en" else ""
    )
    prompt_final = prompt + _lang_directive

    _system_msg = (
        "You are an elite YouTube Content Strategist. Return ONLY valid JSON, nothing else."
        if lang == "en" else
        "Sen elit bir YouTube İçerik Stratejistisin. YALNIZCA geçerli bir JSON döndürürsün, başka hiçbir şey yazmazsın."
    )

    def _post():
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "system", "content": _system_msg},
                             {"role": "user", "content": prompt_final}],
                "max_tokens": 1024,
                "temperature": 0.7,
            },
            timeout=30,
        )
        return resp

    resp = await run_in_threadpool(_post)

    if resp.status_code == 200:
        return resp.json()["choices"][0]["message"]["content"].strip()
    elif resp.status_code == 401:
        raise ValueError("Groq API key is invalid. Please check from the Settings panel.")
    elif resp.status_code == 429:
        raise ValueError("Groq API quota is exhausted. Please wait a moment.")
    else:
        raise ValueError(f"Groq API error: HTTP {resp.status_code}")




def _build_pi_context(tier=None, time_window=None, velocity_per_day=None, penetration_ratio=None, comment_signals=None, views=0):
    """
    Builds Predictive Intelligence context.
    Explains tier, time window, velocity, penetration, and comment signals to the AI.
    Anti-hallucination: if there are no comment signals, the AI is explicitly informed.
    """
    lines = []
    tier_labels = {
        "dead":       "TIER: DEAD -- Bu video hic izlenme kazanamamis. Acil mudahale: baslik/thumbnail autopsy yap.",
        "potential":  "TIER: POTENTIAL -- Video potansiyelini kullanamamis. Bir hamle eksik -- neyi duzeltmeli analiz et.",
        "rising":     "TIER: RISING -- Bu video SU AN YUKSELIYOR! Momentum penceresi acik. Bunu yakala ve anlat.",
        "viral":      "TIER: VIRAL -- Video viral olmus. Basarinin anatomisini cikar, tekrarlanabilir kalibi bul.",
        "mega_viral": "TIER: MEGA VIRAL -- Sadece kazayi kopyalama. Sistemi cikar, tekrarlanabilir unsurlari ayir.",
    }
    if tier and tier in tier_labels:
        lines.append("[PREDICTIVE INTELLIGENCE]")
        lines.append(tier_labels[tier])

    window_labels = {
        "fresh":       "UYARI: Bu video 6 saatten yeni. Izlenme/yorumlar arkadaslik agi etkisi tasiyabilir -- baslik/thumbnail kalitesine odaklan.",
        "burst":       "Video patlama penceresinde (6-48 saat) -- gercek organik momentum.",
        "established": "Video algoritma yayilim evresinde (2-7 gun).",
        "evergreen":   "Video evergreen evresinde (7+ gun) -- trafik arama/oneri bazli.",
    }
    if time_window and time_window in window_labels:
        lines.append(window_labels[time_window])

    if velocity_per_day is not None and velocity_per_day >= 0:
        lines.append(f"Tahmini hiz: {velocity_per_day:,.0f} izlenme/gun.")

    if penetration_ratio is not None and penetration_ratio > 0:
        pstr = "YUKSEK" if penetration_ratio >= 1.0 else "ORTA" if penetration_ratio >= 0.1 else "DUSUK"
        lines.append(f"Abone penetrasyonu: her 100 abonesine {penetration_ratio*100:.1f} izlenme -- {pstr} baglilik.")

    # Anti-hallucination armor: pass as real signal if there is interpretation data;
    # Otherwise, warn the AI ​​not to generate fictitious comments.
    if comment_signals and comment_signals.strip():
        lines.append(f"Yorum sinyalleri (gercek veri): {comment_signals[:300].strip()}")
    elif lines:  # Report missing only if there is other PI data
        lines.append("Yorum sinyali yok -- yorumlar kapali veya henuz yuklenmemis. HAYALI YORUM URETME.")

    return "\n".join(lines)

def calculate_chaos_score(transcript: str, titles: list[str]) -> dict:
    import re
    import statistics

    transcript = (transcript or "").strip()
    titles = titles or []

    # 1. Rage Intensity (0-10)
    rage_words = ['lan', 'ya', 'abi', 'noldu', 'niye', 'nasıl', 'imkansız', 'yok artık', 'git', 'olmaz', 'berbat', 'şok', 'çıldırdım', 'delirdim']
    words = re.findall(r'\b\w+\b', transcript.lower())
    total_words = len(words)
    rage_count = sum(1 for w in words if w in rage_words)
    
    transcript_lower = transcript.lower()
    rage_count += transcript_lower.count("yok artık")
    
    if total_words > 0:
        rage_score = min(10.0, (rage_count / total_words) * 200.0)
    else:
        rage_score = 0.0

    # 2. Tempo Variance (0-10)
    sentences = re.split(r'[.?!]', transcript)
    sentences = [s.strip() for s in sentences if s.strip()]
    lengths = [len(s.split()) for s in sentences]
    
    tempo_score = 0.0
    if len(lengths) > 1: # Fail-Fast: ZeroDivisionError / ValueError protection
        stdev = statistics.stdev(lengths)
        tempo_score = min(10.0, stdev / 1.5)

    # 3. Title Aggressiveness (0-10)
    agg_chars = 0
    total_title_chars = 0
    for t in titles:
        agg_chars += t.count('!') + t.count('?')
        total_title_chars += len(t)
        
    if total_title_chars > 0:
        title_score = min(10.0, (agg_chars / total_title_chars) * 100.0)
    else:
        title_score = 0.0

    # Overall Chaos Score
    final_score = (rage_score * 0.50) + (tempo_score * 0.30) + (title_score * 0.20)
    final_score = round(final_score, 1)

    # FatherClutch Clause
    if final_score < 6:
        verdict = "The competitor's style is not especially high-energy, so leaning into your own style could help you stand out.\n<br><span style='font-size:11px; color:#94a3b8; font-style:italic;'>(Note: This assessment comes from our mathematical algorithm that analyses the aggressiveness of the competitor's titles, speaking pace, and emotionally loaded word count.)</span>"
    else:
        verdict = "The competitor is just as aggressive in style — your edge could come from niche expertise."

    return {
        "score": final_score,
        "verdict": verdict,
        "details": {
            "rage_score": round(rage_score, 1),
            "tempo_score": round(tempo_score, 1),
            "title_score": round(title_score, 1)
        }
    }

def extract_channel_stats_sync(channel_url: str):
    import yt_dlp
    import time as _time

    if not channel_url.endswith('/videos'):
        base_url = channel_url.split('/featured')[0].split('/shorts')[0].split('/streams')[0].rstrip('/')
        channel_url = f"{base_url}/videos"

    opts = {
        'extract_flat': True,
        'playlist_end': 5,
        'quiet': True,
        'no_warnings': True,
        # STRESS TEST FIX #6: yt-dlp rate-limit and IP ban protection
        # Opening sockets too quickly triggers 429; A little sleep can be added.
        'sleep_interval': 1,        # minimum 1s wait between requests
        'max_sleep_interval': 3,    # maksimum 3sn
        'socket_timeout': 15,
    }

    # Exponential Backoff: Try 3 times on 429 or temporary network error (1s → 3s → 9s)
    last_error = None
    for attempt in range(3):
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(channel_url, download=False)
            break  # Success → exit loop
        except Exception as e:
            last_error = e
            err_str = str(e).lower()
            is_rate_limit = '429' in err_str or 'too many requests' in err_str or 'rate' in err_str
            is_temporary  = 'timeout' in err_str or 'connection' in err_str or 'network' in err_str

            if (is_rate_limit or is_temporary) and attempt < 2:
                wait_secs = 3 ** attempt  # 1, 3, 9 seconds
                app_logger.warning(
                    f"[Channel Battles] yt-dlp error (attempt {attempt+1}/3): {e} | "
                    f"{wait_secs}sn sonra tekrar deneniyor..."
                )
                _time.sleep(wait_secs)
            else:
                # Persistent error or 3rd attempt: throw
                if '429' in err_str or 'too many requests' in err_str:
                    raise ValueError(
                        "YouTube applied rate-limiting (HTTP 429). "
                        "Channel Battles can be retried in a few minutes. "
                        "Scanning too frequently increases the risk of an IP ban."
                    )
                raise ValueError(f"Channel data could not be fetched: {e}")
    else:
        # All attempts fail
        raise ValueError(f"Channel data could not be fetched in 3 attempts: {last_error}")

    entries = info.get('entries', [])
    if not entries:
        raise ValueError("Channel videos not found.")
        
    total_views = 0
    count = 0
    video_urls = []
    recent_titles = []
    for v in entries:
        if v and v.get('url'):
            video_urls.append(v['url'])
        if v and v.get('title'):
            recent_titles.append(v['title'])
        if v and v.get('view_count'):
            total_views += v['view_count']
            count += 1
            
    # If extract_flat did not return view_counts (None),
    # We capture the metadata of the first 3 videos individually (faster and more stable)
    if count == 0 and video_urls:
        single_opts = {
            'extract_flat': False,
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 5
        }
        with yt_dlp.YoutubeDL(single_opts) as ydl_single:
            for v_url in video_urls[:3]:
                try:
                    v_info = ydl_single.extract_info(v_url, download=False)
                    if v_info and v_info.get('view_count'):
                        total_views += v_info['view_count']
                        count += 1
                except:
                    pass
                    
    if count == 0:
        avg_views = "Bilinmiyor"
    else:
        avg_views = int(total_views / count)
        
    # Transcript Capture and Chaos Metric
    transcript = ""
    try:
        if video_urls:
            first_url = video_urls[0]
            if 'v=' in first_url:
                v_id = first_url.split('v=')[-1].split('&')[0]
            else:
                v_id = first_url.split('/')[-1].split('?')[0]
            transcript = _fetch_transcript_sync(v_id)
    except Exception:
        pass
        
    chaos_metrics = calculate_chaos_score(transcript, recent_titles[:5])
        
    return {
        "channel_name": info.get('uploader', info.get('title', 'Bilinmeyen Kanal')),
        "avg_views": avg_views,
        "recent_titles": recent_titles[:5],
        "video_count_analyzed": count if count > 0 else len(video_urls),
        "chaos_metrics": chaos_metrics
    }

async def _call_groq_battle(api_key: str, my_data: dict, rival_data: dict) -> str:
    import requests
    
    prompt = f"""
Sen keskin zekalı, elit bir YouTube Strateji Uzmanısın. Jenerik kurumsal dilden ("SEO'yu artır", "Kaliteyi yükselt") nefret edersin.

{ADVISORY_TONE_RULE}

[KULLANICININ VERİLERİ]
- Kanalın Kalite Puanı: {my_data.get('avg_score', 0)} / 10

[RAKİP KANAL: {rival_data.get('channel_name', 'Bilinmiyor')}]
- Ortalama İzlenme: {rival_data.get('avg_views', 0)}
- Son Yüklediği Videolar: {', '.join(rival_data.get('recent_titles', []))}

[GÖREVİN]
Bana "Savaş Raporu" formatında kısa ve vurucu bir analiz yaz. Kurumsal ChatGPT ağzını ASLA kullanma.
Aşağıdaki formatın DIŞINA ÇIKMA:

⚔️ RAKİP ANALİZİ:
(Rakibin son videolarına bakarak ne tarz bir kitleyi elinde tuttuğunu 1-2 cümleyle, net ve sivri bir dille özetle. Örn: "Rakip sürekli teknoloji incelemeleriyle kolaya kaçıyor.")

🔥 GERİLLA TAKTİKLERİ:
(Kullanıcının kalite puanı {my_data.get('avg_score', 0)}. Rakibin 'Son Yüklediği Videolar' listesinden bir videoyu hedef alarak, kullanıcının o konunun TAM TERSİ BİR AÇIYLA (Zıtlık, Eleştiri, Kışkırtma veya Merak Boşluğu) rakibin izleyicisini nasıl çekebileceğine dair 2 spesifik video fikri/kancası ver. Kesinlikle "kaliteyi artır", "sosyal medya kullan" gibi genel geçer şeyler yazma! Spesifik ol ama öneri olarak sun: "Şu videonun başlığını şöyle çevirebilirsin" gibi.)
"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "Sen keskin ama tavsiye dilini bozmayan bir YouTube stratejistisin."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 1024
    }
    
    def _post():
        return requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
    
    resp = await run_in_threadpool(_post)
    if resp.status_code == 200:
        return resp.json()["choices"][0]["message"]["content"].strip()
    else:
        raise ValueError(f"Groq API error: HTTP {resp.status_code}")


class CloneVideoRequest(BaseModel):
    """Chrome eklentisinden gelen video metadata modeli."""
    # extra='ignore': unknown fields from the plugin (e.g. 'error') will not trigger 422
    model_config = ConfigDict(extra="ignore")

    url:       str = Field(default="", description="Tam YouTube video URL'si")
    videoId:   str = Field(default="", description="YouTube video ID (v= parametresi)")
    title:     str = Field(default="No Title", description="Video title")
    channel:   str = Field(default="Unknown Channel", description="Channel name")
    thumbnail: str = Field(default="", description="Thumbnail URL")
    views:     int = Field(default=0,  description="Izlenme sayisi")
    # -- Predictive Intelligence --
    upload_date:       Optional[str]   = Field(default=None)
    subscriber_count:  Optional[int]   = Field(default=None)
    velocity_per_day:  Optional[float] = Field(default=None)
    time_window:       Optional[str]   = Field(default=None)
    tier:              Optional[str]   = Field(default=None)
    penetration_ratio: Optional[float] = Field(default=None)
    comment_signals:   Optional[str]   = Field(default=None)
    user_id:   int = Field(default=0, description="User ID")
    target_channel_id: Optional[int] = Field(default=None, description="Seçili kanalın ID'si (çoklu kanal senaryosu)")
    # -- i18n --
    lang:      str = Field(default="tr", description="UI language: 'tr' or 'en'")

class AnalyzeChannelRequest(BaseModel):
    channel_url: str
    user_id: int
    lang: str = "tr"

@app.post("/api/extension/analyze_channel")
async def extension_analyze_channel(payload: AnalyzeChannelRequest):
    api_key = await get_groq_api_key()
    if not api_key:
        return {"error": "Groq API key is not configured."}
        
    try:
        rival_data = await run_in_threadpool(extract_channel_stats_sync, payload.channel_url)
    except Exception as e:
        return {"error": f"Channel data could not be read: {str(e)}"}
        
    db = await get_async_db()
    try:
        async with db.execute("SELECT AVG(overall_score) as avg_score, COUNT(*) as count FROM analyses WHERE user_id = ?", (payload.user_id,)) as c:
            my_stats = await c.fetchone()
    finally:
        await db.close()
        
    my_data = {
        "avg_score": round(my_stats['avg_score'] or 0, 1) if my_stats and my_stats['avg_score'] else 0,
        "total_analyzed_videos": my_stats['count'] if my_stats else 0
    }
    
    try:
        report = await _call_groq_battle(api_key, my_data, rival_data)
        return {"result": report, "rival_name": rival_data["channel_name"], "chaos_metrics": rival_data.get("chaos_metrics")}
    except Exception as e:
        return {"error": f"Battle report could not be generated: {str(e)}"}

class ExtensionLoginRequest(BaseModel):
    username: str
    password: str

@app.post("/api/extension/login")
async def extension_login(req: ExtensionLoginRequest):
    db = await get_async_db()
    try:
        async with db.execute("SELECT id, username, password_hash FROM users WHERE username = ?", (req.username,)) as cursor:
            user = await cursor.fetchone()
            
        if not user:
            raise HTTPException(status_code=401, detail="Invalid username or password.")
            
        if not verify_password(req.password, user['password_hash']):
            raise HTTPException(status_code=401, detail="Invalid username or password.")
            
        return {"success": True, "user_id": user['id'], "username": user['username']}
    finally:
        await db.close()

@app.get("/api/extension/recent_analyses")
async def extension_recent_analyses(user_id: int):
    db = await get_async_db()
    try:
        async with db.execute(
            "SELECT id, video_name, overall_score, timestamp FROM analyses WHERE user_id = ? ORDER BY id DESC LIMIT 5",
            (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            
        analyses = []
        for r in rows:
            analyses.append({
                "id": r['id'],
                "video_name": r['video_name'],
                "score": round(r['overall_score'] or 0, 1),
                "date": r['timestamp']
            })
        return {"success": True, "analyses": analyses}
    finally:
        await db.close()

def extract_rabbit_hole_sync(query: str):
    import yt_dlp
    from datetime import datetime
    
    opts = {
        'extract_flat': 'in_playlist',
        'quiet': True,
        'no_warnings': True
    }
    
    search_query = f"ytsearch10:{query}"
    
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(search_query, download=False)
        entries = info.get('entries', [])
        
        if not entries:
            raise ValueError("No videos found in this niche.")
            
        results = []
        today = datetime.now()
        
        for v in entries:
            upload_date_str = v.get('upload_date')
            view_count = v.get('view_count', 0)
            
            if not view_count:
                continue
                
            days = 1
            if upload_date_str:
                try:
                    upload_date = datetime.strptime(upload_date_str, '%Y%m%d')
                    days_diff = (today - upload_date).days
                    days = max(1, days_diff)
                except Exception:
                    days = 1
                    
            velocity = view_count / days
            
            results.append({
                "title": v.get('title', 'Bilinmeyen Video'),
                "channel": v.get('uploader', 'Bilinmeyen Kanal'),
                "url": v.get('url', ''),
                "view_count": view_count,
                "velocity": int(velocity)
            })
                
        if not results:
            raise ValueError("No valid data found.")
            
        # Sort by velocity descending
        results.sort(key=lambda x: x['velocity'], reverse=True)
        return results[:3]

class RabbitHoleRequest(BaseModel):
    query: str
    user_id: Optional[Union[int, str]] = 0
    lang: str = "tr"

async def analyze_rabbit_hole_compatibility(api_key: str, title: str, channel: str, content_type: str, purpose: str, lang: str = "tr") -> str:
    import requests
    _lang_rule = (
        "Respond in ENGLISH."
        if lang == "en" else "Türkçe cevap ver."
    )
    prompt = f"User's channel concept: {content_type} (Goal: {purpose}). Is this trending video (Title: {title}, Channel: {channel}) compatible with the user's concept? If not (e.g. Esports tournament, official announcement, or serious tutorial etc.) say 'Incompatible' and explain why. If it aligns with the concept, say 'Compatible'. Your output must be at most 2 short sentences. {_lang_rule}"
    
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 100
    }
    resp = await run_in_threadpool(lambda: requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=10))
    if resp.status_code == 200:
        return resp.json()["choices"][0]["message"]["content"].strip()
    return "Analysis could not be performed."

@app.post("/api/extension/rabbit_hole")
async def extension_rabbit_hole(payload: RabbitHoleRequest):
    try:
        top_outliers = await run_in_threadpool(extract_rabbit_hole_sync, payload.query)
        if not top_outliers:
            return {"error": "No outlier trend found in this niche."}
            
        api_key = await get_groq_api_key()
        if api_key:
            content_type = "General Content"
            purpose = "Entertaining the Audience"
            if payload.user_id:
                db = await get_async_db()
                try:
                    async with db.execute("SELECT content_type, purpose FROM channels WHERE user_id = ? LIMIT 1", (payload.user_id,)) as c:
                        channel_row = await c.fetchone()
                        if channel_row:
                            content_type = channel_row['content_type'] or content_type
                            purpose = channel_row['purpose'] or purpose
                finally:
                    await db.close()

            for v in top_outliers:
                analysis = await analyze_rabbit_hole_compatibility(api_key, v['title'], v['channel'], content_type, purpose, lang=payload.lang)
                v['uyumluluk'] = analysis
                
        return {"success": True, "outliers": top_outliers}
    except Exception as e:
        app_logger.error(f"Rabbit Hole Error: {e}", exc_info=True)
        return {"error": "No outlier trend found in this niche or a network error occurred."}


# ═══════════════════════════════════════════════════════════
# PROPHET'S PICK — Automatic Viral Recommendation System
# Dynamically detects 3 "Outlier" videos that fit the user's niche.
# Automatically detects 3 "Outlier" videos.
# It uses the existing extract_rabbit_hole_sync module (KISS).
# 3 queries run in PARALLEL with asyncio → max ~2sec loading.
# ═══════════════════════════════════════════════════════════

class ProphetPicksRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: Optional[Union[int, str]] = 0

async def _generate_prophet_queries(api_key: str, content_type: str, purpose: str) -> list[str]:
    import requests, json, re
    prompt = f"""Kullanıcının kanalı konsepti: {content_type} (Amaç: {purpose}).
Bu kanalın ana nişiyle BİREBİR alakalı, şu an YouTube'da trend olabilecek 3 spesifik "YouTube arama sorgusu" (search query) üret.
KURALLAR:
1. Asla genel kelimeler (örn: "komedi", "eğlence", "oyun", "kaos") kullanma. Doğrudan içeriğin ana konusunu/oyununu barındıran çok spesifik sorgular üret (Örn: "Rocket League rage", "Rocket League funny moments", "Rocket League challenge").
2. Alakasız TV şovları, genel vloglar veya farklı oyunlar çıksın İSTEMİYORUZ. Yalnızca kanalın hedef nişine (oyunsa o oyuna, teknoloiyse o teknolojiye) odaklan!
3. YALNIZCA geçerli bir JSON dizisi döndür, başka HİÇBİR ŞEY yazma.
Örnek Format: ["spesifik_sorgu_1", "spesifik_sorgu_2", "spesifik_sorgu_3"]"""

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5,
        "max_tokens": 100
    }
    resp = await run_in_threadpool(lambda: requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=10))
    if resp.status_code == 200:
        content = resp.json()["choices"][0]["message"]["content"].strip()
        content = re.sub(r"```(?:json)?", "", content).replace("```", "").strip()
        try:
            queries = json.loads(content)
            if isinstance(queries, list) and len(queries) >= 3:
                return queries[:3]
        except:
            pass
    return [f"{content_type} trend", f"{content_type} 2024", f"{content_type} yeni"]

@app.post("/api/extension/prophet_picks")
async def extension_prophet_picks(payload: ProphetPicksRequest):
    """
    Detects 3 'Outlier' videos currently trending on YouTube
    that match the user's own niche.
    - 3 different niche queries (via Groq) are generated based on the user's channel concept.
    - 3 queries run IN PARALLEL (asyncio.gather).
    - Videos uploaded in the last 48 hours are prioritized.
    - The user's own channel videos are skipped (dynamic self-filtering).
    - The 3 videos with the highest velocity are selected.
    """
    try:
        db = await get_async_db()
        content_type = "General Content"
        purpose = "Entertaining the Audience"
        channel_names = []
        if payload.user_id:
            try:
                async with db.execute("SELECT name, content_type, purpose FROM channels WHERE user_id = ?", (payload.user_id,)) as c:
                    rows = await c.fetchall()
                    if rows:
                        content_type = rows[0]['content_type'] or content_type
                        purpose = rows[0]['purpose'] or purpose
                        for r in rows:
                            if r['name']:
                                channel_names.append(r['name'].lower().strip())
            finally:
                await db.close()

        api_key = await get_groq_api_key()
        if api_key:
            queries = await _generate_prophet_queries(api_key, content_type, purpose)
        else:
            queries = [f"{content_type} trend", f"{content_type} new", f"{content_type} popular"]

        # Run 3 queries IN PARALLEL (in threadpool, async-safe)
        results_per_query = await asyncio.gather(
            run_in_threadpool(extract_rabbit_hole_sync, queries[0]),
            run_in_threadpool(extract_rabbit_hole_sync, queries[1]),
            run_in_threadpool(extract_rabbit_hole_sync, queries[2]),
            return_exceptions=True  # If one query fails, the others continue to work
        )

        from datetime import datetime, timezone
        now = datetime.now()

        # Combine all results
        all_videos = []
        for idx, result in enumerate(results_per_query):
            if isinstance(result, Exception):
                app_logger.warning(f"[Prophet Picks] Sorgu {idx+1} hata: {result}")
                continue
            if not isinstance(result, list):
                continue
            for v in result:
                # Dynamic Self-comparison bug fix: User's own videos are skipped
                channel_lower = (v.get("channel") or "").lower().strip()
                is_own_channel = False
                for c_name in channel_names:
                    if c_name and (c_name in channel_lower or channel_lower in c_name):
                        is_own_channel = True
                        break
                
                if is_own_channel:
                    app_logger.info(f"[Prophet Picks] Self-filtering: {v.get('title')[:50]} skipped.")
                    continue
                # Add to list with velocity score
                all_videos.append(v)

        if not all_videos:
            return {"error": "No currently trending videos found."}

        # Remove duplicate URLs (the same video may appear in multiple queries)
        seen_urls = set()
        unique_videos = []
        for v in all_videos:
            url = v.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_videos.append(v)

        # Sort by Velocity (highest first)
        unique_videos.sort(key=lambda x: x.get("velocity", 0), reverse=True)
        
        # Get the top 10 fastest rising videos
        top_candidates = unique_videos[:10]
        
        # ── AI Compatibility Filter with Groq (Fastest Only) ──
        async def check_comp(v):
            if not api_key: return v, True # If you don't have an API key, pass it by force.
            try:
                comp = await analyze_rabbit_hole_compatibility(
                    api_key, v.get("title", ""), v.get("channel", ""), content_type, purpose
                )
                return v, ("uyumsuz" not in comp.lower() and "uyumlu" in comp.lower())
            except Exception:
                return v, True # If there is an error, pass it anyway

        # Analyze 10 videos in parallel (Very fast, Groq returns in <1 second)
        comp_results = await asyncio.gather(*(check_comp(v) for v in top_candidates), return_exceptions=True)
        
        top_picks = []
        for result in comp_results:
            if isinstance(result, Exception): continue
            v, is_compatible = result
            if is_compatible:
                top_picks.append(v)
            if len(top_picks) == 3:
                break
                
        # If the artificial intelligence cannot find even 3 compatible ones, fill in the ones you have (Fallback).
        if len(top_picks) < 3:
            for v in top_candidates:
                if v not in top_picks:
                    top_picks.append(v)
                if len(top_picks) == 3:
                    break

        app_logger.info(f"[Prophet Picks] {len(top_picks)} recommendations selected.")
        return {"success": True, "picks": top_picks}

    except Exception as e:
        app_logger.error(f"[Prophet Picks] Kritik Hata: {e}", exc_info=True)
        return {"error": "Prophet Picks could not be loaded."}


@app.post("/api/extension/clone_video")
async def extension_clone_video(payload: CloneVideoRequest):
    """
    Receives video data from the Chrome extension.
    1. Fetches transcript (youtube-transcript-api, inside thread-pool)
    2. Generates viral concept with Groq
    3. Returns the result as JSON

    Beklenen JSON body:
        { "url": "...", "videoId": "...", "title": "...", "channel": "...", "thumbnail": "..." }
    """
    # ── Log (debug) incoming data completely ─────────────────
    app_logger.info(f"[clone_video] Eklentiden gelen veri: {payload.model_dump()}")

    url      = payload.url.strip()
    video_id = payload.videoId.strip()
    title    = payload.title.strip() or "No Title"
    channel  = payload.channel.strip() or "Bilinmeyen Kanal"

    if not video_id and "v=" in url:
        from urllib.parse import urlparse, parse_qs
        video_id = parse_qs(urlparse(url).query).get("v", [""])[0]

    if not video_id:
        raise HTTPException(status_code=400, detail="Video ID not found. Please provide a valid YouTube URL.")

    app_logger.info(f"[clone_video] video_id={video_id} title='{title[:60]}'") 

    # ── 1. Transcript ──────────────────── ────────────────────
    try:
        transcript = await run_in_threadpool(_fetch_transcript_sync, video_id)
    except Exception as e:
        app_logger.warning(f"[clone_video] Transcript call error (using Fallback): {e}")
        transcript = ""

    if not transcript or transcript.startswith("ERROR:"):
        app_logger.warning(f"[clone_video] Transcript unavailable (using Fallback): {transcript}")
        transcript = ""

    # ── 2. Groq API key ─────────────────────────────────
    api_key = await get_groq_api_key()
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Groq API key is not set. Please add it from the application Settings panel."
        )

    # ── 3. AI Concept Generation ────────────────────────────────
    db = await get_async_db()
    content_type = "General Content"
    purpose = "Entertaining the Audience"
    channel_name_db = ""
    if payload.user_id:
        try:
            # Çoklu kanal: target_channel_id varsa o kanalı kullan, yoksa LIMIT 1
            if payload.target_channel_id:
                _q = "SELECT content_type, purpose, name FROM channels WHERE id = ? AND user_id = ?"
                _p = (payload.target_channel_id, payload.user_id)
            else:
                _q = "SELECT content_type, purpose, name FROM channels WHERE user_id = ? LIMIT 1"
                _p = (payload.user_id,)
            async with db.execute(_q, _p) as c:
                channel_row = await c.fetchone()
                if channel_row:
                    content_type = channel_row['content_type'] or content_type
                    purpose = channel_row['purpose'] or purpose
                    channel_name_db = channel_row['name'] or ""
        finally:
            await db.close()


    try:
        result = await _call_groq_clone(
            api_key, title, channel, transcript, content_type, purpose,
            views=payload.views, tier=payload.tier, time_window=payload.time_window,
            velocity_per_day=payload.velocity_per_day,
            penetration_ratio=payload.penetration_ratio,
            comment_signals=payload.comment_signals,
            lang=payload.lang,
        )
    except ValueError as e:
        app_logger.warning(f"[clone_video] Groq error: {e}")
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        app_logger.error(f"[clone_video] AI error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"AI concept generation failed: {e}")

    app_logger.info(f"[clone_video] ✅ Concept generated: video_id={video_id}")

    return {
        "success":   True,
        "video_id":  video_id,
        "title":     title,
        "channel":   channel,
        "result":    result,
        "transcript_length": len(transcript),
    }


# ═══════════════════════════════════════════════════════════
# A/B TEST SIMULATOR — Multi-Agent Debate Engine
# Persona A: Cruel Critic (temperature=0.3)
# Persona B: Viral Mage (temperature=0.95)
# Judge AI: Selects the winner / blends and produces a single idea
# ═══════════════════════════════════════════════════════════

async def _call_groq_debate(
    api_key: str,
    title: str,
    channel: str,
    transcript: str,
    content_type: str,
    purpose: str,
    views: int = 0,
    tier: str = None,
    time_window: str = None,
    velocity_per_day: float = None,
    penetration_ratio: float = None,
    comment_signals: str = None,
    lang: str = "tr",
) -> dict:
    """
    Two personas run in parallel (asyncio.gather), then the Judge AI makes the decision.
    Output must be a parseable JSON dict — otherwise HTTPException(500) is raised.
    """

    # -- Predictive Intelligence context (calculated once) --
    _debate_tier = tier or ("mega_viral" if views >= 100_000 else "viral" if views >= 5_000 else "potential" if views >= 500 else "dead")
    _debate_pi = _build_pi_context(tier=_debate_tier, time_window=time_window,
        velocity_per_day=velocity_per_day, penetration_ratio=penetration_ratio,
        comment_signals=comment_signals, views=views)

    # Human face ban for gaming channels is injected into both agents
    thumbnail_rule = _build_thumbnail_rule(content_type)

    transcript_excerpt = transcript[:2000] if transcript else "(No subtitle available)"

    # ── Persona A: Cruel Critic ──────────────────── ────────────────────
    prompt_a = f"""Sen keskin, veriye dayalı, CTR (Tıklanma Oranı) odaklı bir YouTube stratejistisin.
Sentimental düşünmez, sadece sayı ve psikoloji konuşursun.
Kullanıcının kanalı: {content_type}. Amaç: {purpose}.

📌 Orijinal Başlık: {title}
📺 Orijinal Kanal: {channel}
📝 Altyazı (ilk 2000 karakter): {transcript_excerpt}

{ADVISORY_TONE_RULE_CREATIVE}

Kurallar:
1. Mantık, kısıtlama ve merak boşluğu kullan — duygusal clickbait değil.
2. {thumbnail_rule}
3. YALNIZCA şu JSON formatında 1 fikir döndür (başka hiçbir şey yazma):
{{"title": "...", "hook": "...", "thumbnail": "..."}}"""

    # ── Persona B: Viral Mage ─────────────────────── ────────────────────────
    prompt_b = f"""Sen uçuk kaçık, kaotik ve clickbait konusunda şeytani bir viral içerik büyücüsüsün.
Mantığı umursamaz, algoritmayı hissedersin. Aşırı duygusal ve dramatik başlıklar üretirsin.
Kullanıcının kanalı: {content_type}. Amaç: {purpose}.

📌 Orijinal Başlık: {title}
📺 Orijinal Kanal: {channel}
📝 Altyazı (ilk 2000 karakter): {transcript_excerpt}

{ADVISORY_TONE_RULE_CREATIVE}

Kurallar:
1. Merak, şok, korku ve aşırı dramatizm kullan. Sınırı zorla.
2. {thumbnail_rule}
3. YALNIZCA şu JSON formatında 1 fikir döndür (başka hiçbir şey yazma):
{{"title": "...", "hook": "...", "thumbnail": "..."}}"""

    # ── i18n: lang direktifine göre system mesajı ve prompt dil eki ─────────────────────────
    _lang_suffix = (
        "\n\nIMPORTANT: Provide ALL output fields (title, hook, thumbnail) "
        "in ENGLISH language only. Do not use Turkish."
        if lang == "en" else ""
    )
    prompt_a += _lang_suffix
    prompt_b += _lang_suffix

    system_json = (
        "You are a YouTube strategist assistant. Return ONLY valid JSON, nothing else."
        if lang == "en" else
        "Sen bir YouTube stratejisti asistanısın. YALNIZCA geçerli JSON döndürürsün, başka hiçbir şey yazmazsın."
    )

    def _post_persona_a():
        return requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": system_json},
                    {"role": "user",   "content": prompt_a},
                ],
                "max_tokens": 512,
                "temperature": 0.3,  # Persona A: cold and analytical
            },
            timeout=30,
        )

    def _post_persona_b():
        return requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": system_json},
                    {"role": "user",   "content": prompt_b},
                ],
                "max_tokens": 512,
                "temperature": 0.95,  # Persona B: chaotic creative
            },
            timeout=30,
        )

    # ── Run in parallel ─────────────────────────── ───────────────────────────
    resp_a, resp_b = await asyncio.gather(
        run_in_threadpool(_post_persona_a),
        run_in_threadpool(_post_persona_b),
    )

    # Fail-Fast: Throw HTTPException directly on HTTP errors
    for label, resp in [("Persona A (Critic)", resp_a), ("Persona B (Mage)", resp_b)]:
        if resp.status_code == 401:
            raise HTTPException(status_code=502, detail="Groq API key is invalid.")
        if resp.status_code == 429:
            raise HTTPException(status_code=429, detail="Groq API quota exceeded. Please wait.")
        if resp.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"{label} Groq error: HTTP {resp.status_code}"
            )

    raw_a = resp_a.json()["choices"][0]["message"]["content"].strip()
    raw_b = resp_b.json()["choices"][0]["message"]["content"].strip()

    # ── JSON parse — Fail-Fast ──────────────────────── ────────────────────────
    def _parse_persona_json(raw: str, label: str) -> dict:
        """Extract and parse the JSON block. Raise HTTPException(500) on error."""
        import re as _re
        # Clear markdown code blocks
        cleaned = _re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()
        # Find the first { ... } block
        match = _re.search(r"\{.*\}", cleaned, _re.DOTALL)
        if not match:
            app_logger.error(f"[clone_debate] {label} JSON parse error — raw response: {raw[:300]}")
            raise HTTPException(
                status_code=500,
                detail=f"{label} did not return valid JSON. Raw response: {raw[:200]}"
            )
        try:
            return json.loads(match.group(), strict=False)
        except json.JSONDecodeError as exc:
            app_logger.error(f"[clone_debate] {label} JSON decode error: {exc} | Raw: {raw[:300]}")
            raise HTTPException(
                status_code=500,
                detail=f"{label} JSON could not be parsed: {exc}"
            )

    idea_a = _parse_persona_json(raw_a, "Persona A (Critic)")
    idea_b = _parse_persona_json(raw_b, "Persona B (Mage)")

    # ── Judge AI: Pick the Winner or Blend and Generate One Idea ──────────────
    # NOTE: _debate_pi is injected AFTER prompt_judge is defined (below)

    prompt_judge = f"""Sen titiz ve vizyoner bir YouTube İçerik Hakemi ve Algoritma Uzmanısın.

KULLANICI PROFİLİ: 
Kullanıcının kanal tipi: {content_type}. Kanalın amacı: {purpose}.

GÖREVİN:
Sana verilen orijinal video verilerini ve diğer yapay zekaların ürettiği fikirleri analiz edip, en viral olmaya yatkın sonucu sentezlemek.

📌 Analiz Edilen Video: {title} ({channel})
🎯 Kanal Nişi: {content_type}
📝 Altyazı: {transcript_excerpt}

--- AJAN A (Eleştirmen) ---
Başlık  : {idea_a.get('title', '')}
Kanca   : {idea_a.get('hook', '')}
Thumbnail: {idea_a.get('thumbnail', '')}

--- AJAN B (Büyücü) ---
Başlık  : {idea_b.get('title', '')}
Kanca   : {idea_b.get('hook', '')}
Thumbnail: {idea_b.get('thumbnail', '')}

{ADVISORY_TONE_RULE_CREATIVE}

KURAL 1 (ZORUNLU BAŞLANGIÇ): 
Bu videonun başarısının altındaki psikolojik tetikleyiciyi "viral_anatomi" alanında açıkla.

KURAL 2 (SENTEZ): 
Ajanların fikirlerini "eleştirmen_fikri" ve "buyucu_fikri" alanlarında özetle.
Sonra bu fikirleri harmanlayıp EN GÜÇLÜ TEK BİR VİDEO FİKRİ sun (kazanan_baslik, kazanan_kanca, kazanan_thumbnail).
{thumbnail_rule}

KURAL 3 (KESİN NİŞ UYARISI): 
Analiz ettiğin orijinal videonun kategorisi kullanıcının "Oyun/Kaos" konseptiyle uyuşmuyorsa, "nis_uyarisi" alanına KESİNLİKLE şu uyarıyı ekle: "⚠️ NİŞ UYARISI: Bu kanalın konsepti senin kanalının (Oyun/Kaos) konseptiyle uyuşmuyor. Klonlama yaparken konsepti kendi nişine uyarlamayı düşünebilirsin." (Uyuşuyorsa boş bırak).

KURAL 4 (KESİN FORMAT KURALI): 
Çıktın KESİNLİKLE bir dizi (array) [...] OLAMAZ. Çıktın KESİNLİKLE bir obje (object) {{...}} olmak zorundadır. Objenin içinde "viral_anatomi", "eleştirmen_fikri", "buyucu_fikri", "kazanan_baslik", "kazanan_kanca", "kazanan_thumbnail" ve "nis_uyarisi" anahtarları ZORUNLUDUR. 

YALNIZCA şu JSON formatında döndür (başka hiçbir şey yazma):
{{
  "viral_anatomi": "...",
  "eleştirmen_fikri": "...",
  "buyucu_fikri": "...",
  "kazanan_baslik": "...",
  "kazanan_kanca": "...",
  "kazanan_thumbnail": "...",
  "nis_uyarisi": "..."
}}"""

    # Inject Predictive Intelligence context into referee prompt (anti-hallucination)
    if _debate_pi:
        prompt_judge = _debate_pi + "\n\n" + prompt_judge

    # ── i18n: Judge prompt'a dil direktifi ekle
    if lang == "en":
        prompt_judge += (
            "\n\nIMPORTANT: Write ALL text fields (viral_anatomi, eleştirmen_fikri, buyucu_fikri, "
            "kazanan_baslik, kazanan_kanca, kazanan_thumbnail, nis_uyarisi) "
            "in ENGLISH language only. Do not use Turkish."
        )

    _judge_system = (
        "You are a YouTube content strategist judge. Return ONLY valid JSON, nothing else."
        if lang == "en" else
        "Sen bir YouTube algoritma hakemısın. YALNIZCA geçerli JSON döndürürsün, başka hiçbir şey yazmazsın."
    )

    def _post_judge():
        return requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": _judge_system},
                    {"role": "user",   "content": prompt_judge},
                ],
                "max_tokens": 768,
                "temperature": 0.5,
            },
            timeout=35,
        )

    resp_judge = await run_in_threadpool(_post_judge)

    if resp_judge.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Judge AI Groq error: HTTP {resp_judge.status_code}"
        )

    raw_judge = resp_judge.json()["choices"][0]["message"]["content"].strip()

    # Fail-Fast: Arbiter JSON parse
    import re as _re2
    cleaned_judge = _re2.sub(r"```(?:json)?", "", raw_judge).replace("```", "").strip()
    match_judge = _re2.search(r"\{.*\}", cleaned_judge, _re2.DOTALL)
    if not match_judge:
        app_logger.error(f"[clone_debate] Judge JSON parse error — raw: {raw_judge[:300]}")
        raise HTTPException(
            status_code=500,
            detail=f"Judge AI did not return valid JSON. Raw response: {raw_judge[:200]}"
        )
    try:
        result_dict = json.loads(match_judge.group(), strict=False)
    except json.JSONDecodeError as exc:
        app_logger.error(f"[clone_debate] Judge JSON decode error: {exc} | Raw: {raw_judge[:300]}")
        raise HTTPException(
            status_code=500,
            detail=f"Judge AI JSON could not be parsed: {exc}"
        )

    # Verify mandatory keys
    required_keys = {"eleştirmen_fikri", "buyucu_fikri", "kazanan_baslik", "kazanan_kanca", "kazanan_thumbnail"}
    missing = required_keys - result_dict.keys()
    if missing:
        app_logger.error(f"[clone_debate] Judge JSON missing key(s): {missing} | Raw: {raw_judge[:300]}")
        raise HTTPException(
            status_code=500,
            detail=f"Judge AI output is missing key(s): {missing}"
        )

    return result_dict


@app.post("/api/extension/clone_debate")
async def extension_clone_debate(payload: CloneVideoRequest):
    """
    A/B Test Simulator — Multi-Agent Debate Endpoint.
    Persona A (Critic) + Persona B (Mage) run in parallel.
    Judge AI selects/blends the best idea and returns JSON.

    Expected JSON body: { "url": "...", "videoId": "...", "title": "...", "channel": "...", "thumbnail": "..." }
    Output: { "success": true, "debate": { eleştirmen_fikri, buyucu_fikri, kazanan_baslik, kazanan_kanca, kazanan_thumbnail } }
    # NOTE: JSON keys are intentionally left in Turkish — they are DB/API contract keys used by the frontend extension.
    """
    app_logger.info(f"[clone_debate] ⚔️ Debate started: {payload.model_dump()}")

    url      = payload.url.strip()
    video_id = payload.videoId.strip()
    title    = payload.title.strip() or "No Title"
    channel  = payload.channel.strip() or "Bilinmeyen Kanal"

    if not video_id and "v=" in url:
        from urllib.parse import urlparse, parse_qs
        video_id = parse_qs(urlparse(url).query).get("v", [""])[0]

    if not video_id:
        raise HTTPException(status_code=400, detail="Video ID not found. Please provide a valid YouTube URL.")

    # ── Transcript ────────────────────────────── ───────────────────────────────
    try:
        transcript = await run_in_threadpool(_fetch_transcript_sync, video_id)
    except Exception as e:
        app_logger.warning(f"[clone_debate] Transcript error (Fallback): {e}")
        transcript = ""

    if not transcript or transcript.startswith("ERROR:"):
        transcript = ""

    # ── API Key ──────────────────────────────── ────────────────────────────────
    api_key = await get_groq_api_key()
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Groq API key is not set. Please add it from the application Settings panel."
        )

    # ── Channel Profile ───────────────────────────── ─────────────────────────────
    content_type    = "General Content"
    purpose         = "Entertaining the Audience"
    channel_name_db = ""
    if payload.user_id:
        db = await get_async_db()
        try:
            # Çoklu kanal: target_channel_id varsa o kanalı kullan, yoksa LIMIT 1
            if payload.target_channel_id:
                _q2 = "SELECT content_type, purpose, name FROM channels WHERE id = ? AND user_id = ?"
                _p2 = (payload.target_channel_id, payload.user_id)
            else:
                _q2 = "SELECT content_type, purpose, name FROM channels WHERE user_id = ? LIMIT 1"
                _p2 = (payload.user_id,)
            async with db.execute(_q2, _p2) as c:
                row = await c.fetchone()
                if row:
                    content_type    = row["content_type"] or content_type
                    purpose         = row["purpose"]      or purpose
                    channel_name_db = row["name"]         or ""
        finally:
            await db.close()

    # ── Multi-Agent Debate ────────────────────────── ───────────────────────────
    debate_result = await _call_groq_debate(
        api_key, title, channel, transcript, content_type, purpose,
        views=payload.views, tier=payload.tier, time_window=payload.time_window,
        velocity_per_day=payload.velocity_per_day,
        penetration_ratio=payload.penetration_ratio,
        comment_signals=payload.comment_signals,
    )

    app_logger.info(f"[clone_debate] ✅ Debate completed: video_id={video_id}")

    return {
        "success":  True,
        "video_id": video_id,
        "title":    title,
        "channel":  channel,
        "debate":   debate_result,
    }



# ═══════════════════════════════════════════════════════════════════════════════
#  🧬 DNA ANALİZ MOTORU  —  v5.5.0 "Elite Calibration"
#
#  Saf Python NLP tabanlı puanlama sistemi.
#  Altyazı → 4 bölüm → 4 puan → Elite Overall Algoritması → Groq Master Prompt
#
#  Overall Algoritması (v5.5.0):
#    1. DR Koruması : Hook≥80 VE Tempo≥80 → CTA/Duygu en az 50 ile değerlendirilir
#    2. Base        : (H×0.40) + (T×0.40) + (D_eff×0.10) + (C_eff×0.10)
#    3. Synergy     : Hook>75 VE Tempo>75 → +20 ("Viral Canavar" bonusu)
#    4. Ceiling     : min(skor, 100)
# ═══════════════════════════════════════════════════════════════════════════════

def _dna_elite_overall(hook: float, retention: float, cta: float, emotion: float) -> float:
    """
    v5.5.0 Elite Calibration Algoritması.

    Mantık:
      - Diminishing Returns (DR) Koruması:
        Hook≥80 VE Tempo≥80 olan videolarda CTA ve Duygu zorunlu olarak
        en az 50 kredi alır. Gerçek bir viral video, güçlü core’u sayesinde
        izleyiciyi otomatik motive eder — eksik CTA bunu silmez.
      - Synergy Bonusu:
        Hook>75 VE Tempo>75 ise "Viral Canavar" olarak etiketlenir, +20 puan.
      - Ceiling: 100 tavanı.

    Örnek (MrBeast): H=81, T=83, D=15, C=18
      DR   : D_eff=50, C_eff=50
      Base : 32.4 + 33.2 + 5.0 + 5.0 = 75.6
      Synergy: +20 → 95.6  (👑 EFSANEVİ)
    """
    # Step 1 — DR Koruması: Elite core = min. 50 kredi
    if hook >= 80.0 and retention >= 80.0:
        eff_cta     = max(cta,     50.0)
        eff_emotion = max(emotion, 50.0)
    else:
        eff_cta     = cta
        eff_emotion = emotion

    # Step 2 — Ağırlıklı Base
    base = (
        (hook      * 0.40) +
        (retention * 0.40) +
        (eff_emotion * 0.10) +
        (eff_cta   * 0.10)
    )

    # Step 3 — Synergy Bonusu (Viral Canavar)
    if hook > 75.0 and retention > 75.0:
        base += 20.0

    # Step 4 — Ceiling
    return round(min(base, 100.0), 1)

def _dna_split_transcript(transcript: str) -> dict:
    """
    Altyazıyı 4 anlamlı bölüme ayırır: Giriş (%20), Gelişme-A (%30),
    Gelişme-B (%30), Sonuç+CTA (%20).
    Kısa metinlerde bölüm sınırları örtüşür ama sıfır olmaz.
    """
    text = (transcript or "").strip()
    if not text:
        return {"intro": "", "dev_a": "", "dev_b": "", "outro": ""}
    words = text.split()
    n = len(words)
    i1 = max(1, int(n * 0.20))
    i2 = max(i1 + 1, int(n * 0.50))
    i3 = max(i2 + 1, int(n * 0.80))
    return {
        "intro": " ".join(words[:i1]),
        "dev_a": " ".join(words[i1:i2]),
        "dev_b": " ".join(words[i2:i3]),
        "outro": " ".join(words[i3:]),
    }


def _dna_hook_score(intro: str) -> float:
    """
    Giriş bölümündeki soru/ünlem ve tetikleyici kelime yoğunluğunu puanlar.
    Power Words (I, Challenge, Million vb.) daha yüksek ağırlık alır.
    Maksimum: 100.
    """
    import re
    if not intro:
        return 0.0

    # Soru, ünlem ve dolar işaretleri (güçlü tetikleyici sinyal)
    punct_count = intro.count("?") + intro.count("!") + intro.count("$")
    
    # Tetikleyici kelimeler ve Power Words
    power_words = [
        "i", "challenge", "million", "secret", "100", "50", "win", "lose",
        "nasıl", "neden", "niye", "ne zaman", "kim", "hangi", "kaç",
        "inanılmaz", "şok", "sır", "hata", "büyük", "en iyi", "en kötü",
        "tehlike", "dikkat", "uyarı", "keşfet", "gizli", "gerçek",
        "how", "why", "what", "shocking", "best", "worst",
        "never", "always", "banned", "exposed", "truth", "revealed",
        "unbelievable", "insane", "crazy", "first", "last", "only",
    ]
    words = re.findall(r'\b\w+\b', intro.lower())
    total_words = max(len(words), 1)
    
    trigger_count = sum(1 for w in words if w in power_words)

    punct_score   = min(45.0, punct_count * 10.0)
    # Power word yoğunluğu çok yüksekse (MrBeast stili kısa vurucu giriş) daha yüksek puan
    trigger_score = min(70.0, (trigger_count / total_words) * 800.0)
    raw = punct_score + trigger_score
    return round(min(100.0, raw * 1.15), 1)


def _dna_retention_score(dev_a: str, dev_b: str) -> float:
    """
    Gelişme bölümlerinin cümle uzunluğu varyansını (Tempo) ve
    geçiş kelimelerini ölçer. MrBeast tarzı kısa, seri cümleler 
    yüksek tempo olarak ödüllendirilir.
    Maksimum: 100.
    """
    import re, statistics
    text = (dev_a + " " + dev_b).strip()
    if not text:
        return 0.0

    sentences = re.split(r'[.?!…;]', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if len(sentences) < 2:
        return 30.0  # Tek cümle, nötr puan

    lengths = [len(s.split()) for s in sentences]
    avg_wps = sum(lengths) / len(lengths)
    
    # Tempo puanı: Kısa seri cümleler (MrBeast style) çok yüksek puan alır
    tempo_score = 0.0
    if avg_wps <= 6:
        tempo_score = 60.0
    elif avg_wps <= 10:
        tempo_score = 50.0
    elif avg_wps <= 15:
        tempo_score = 40.0
    elif avg_wps <= 20:
        tempo_score = 25.0
    else:
        tempo_score = 10.0

    try:
        variance_score = min(20.0, statistics.stdev(lengths) * 2.0)
    except Exception:
        variance_score = 0.0

    # Geçiş kelimeler (akışkanlık sinyali)
    transition_words = [
        "ama", "fakat", "ancak", "oysa", "bununla birlikte", "üstelik",
        "ayrıca", "dahası", "bunun yanı sıra", "çünkü", "zira", "yani",
        "özetle", "sonuç olarak", "ek olarak", "bir yandan", "öte yandan",
        "but", "however", "also", "moreover", "furthermore", "because",
        "therefore", "although", "despite", "yet", "meanwhile", "then",
        "next", "finally", "additionally",
    ]
    words = re.findall(r'\b\w+\b', text.lower())
    total_words = max(len(words), 1)
    trans_count = sum(1 for w in words if w in transition_words)
    transition_score = min(20.0, (trans_count / total_words) * 800.0)

    raw = tempo_score + variance_score + transition_score
    return round(min(100.0, raw * 1.15), 1)


def _dna_cta_score(outro: str) -> float:
    """
    Sonuç bölümündeki aksiyon kelimelerinin varlığını ve yoğunluğunu puanlar.
    Çok çeşitli varyasyonlar desteklenir.
    Maksimum: 100.
    """
    import re
    if not outro:
        return 0.0

    cta_words = [
        # Türkçe
        "abone", "beğen", "yorum", "paylaş", "bildirim", "zil", "tıkla",
        "izle", "takip", "destek", "katıl", "oy ver", "link", "altında",
        "satın al", "açıklama", "ürün", "sponsor",
        # İngilizce
        "subscribe", "like", "comment", "share", "notification", "bell",
        "click", "watch", "follow", "support", "join", "vote", "link",
        "below", "check", "hit", "smash", "buy", "merch", "patreon",
        "sponsor", "description",
    ]
    words = re.findall(r'\b\w+\b', outro.lower())
    total_words = max(len(words), 1)
    cta_count = sum(1 for w in words if w in cta_words)

    raw = min(100.0, (cta_count / total_words) * 2000.0) # Frekans ağırlığı artırıldı
    # Bonus: En az 3 farklı CTA varsa puan artırım
    unique_cta = len(set(w for w in words if w in cta_words))
    bonus = min(30.0, unique_cta * 8.0)
    return round(min(100.0, (raw + bonus) * 1.15), 1)


def _dna_emotion_score(full_text: str) -> float:
    """
    Metindeki duygusal kelime frekansını ölçer.
    Pozitif + negatif + yoğunlaştırıcılar dahil.
    Maksimum: 100.
    """
    import re
    if not full_text:
        return 0.0

    emotion_words = [
        # Pozitif (Türkçe)
        "harika", "muhteşem", "inanılmaz", "mükemmel", "süper", "efsane",
        "seviyorum", "bayıldım", "gurur", "mutlu", "başarı", "kazandı",
        # Negatif (Türkçe)
        "berbat", "rezalet", "korkunç", "nefret", "sinir", "öfke",
        "şok", "dehşet", "trajedi", "mahvetti", "yıkıldı", "çöktü",
        # Yoğunlaştırıcılar (Türkçe)
        "çok", "aşırı", "tam", "kesinlikle", "hiç", "asla", "sadece",
        # Pozitif (İngilizce)
        "amazing", "incredible", "awesome", "perfect", "love", "great",
        "brilliant", "fantastic", "wonderful", "excellent", "best",
        # Negatif (İngilizce)
        "terrible", "awful", "hate", "worst", "horrible", "disgusting",
        "shocking", "tragic", "devastating", "failed", "disaster",
        # Yoğunlaştırıcılar (İngilizce)
        "absolutely", "totally", "completely", "never", "always", "only",
    ]
    words = re.findall(r'\b\w+\b', full_text.lower())
    total_words = max(len(words), 1)
    emotion_count = sum(1 for w in words if w in emotion_words)

    raw = min(100.0, (emotion_count / total_words) * 800.0)
    return round(raw, 1)


async def _call_groq_dna_prompt(
    api_key: str, title: str, channel: str, transcript: str,
    scores: dict, is_estimated: bool = False,
    lang: str = "tr",
) -> str:
    """
    DNA puanlarını ve altyazıyı kullanarak 'Master Prompt' üretir.
    is_estimated=True ise altyazı yerine metadata (başlık/açıklama) kullanıldığını
    Groq'a bildirir; çıktıda 'Tahmini Analiz' notu yer alır.
    """
    import requests as _req

    transcript_preview = (transcript or "")[:3000]
    scores_str = (
        f"Hook Skoru: {scores['hook']}/100 | "
        f"Retention Skoru: {scores['retention']}/100 | "
        f"CTA Skoru: {scores['cta']}/100 | "
        f"Emotion Skoru: {scores['emotion']}/100"
    )

    # Fallback modda Groq'a farklı talimat ver
    if is_estimated:
        analysis_mode_note = (
            "⚠️ ÖNEMLİ: Bu video için altyazı (transcript) bulunamadı. "
            "Analiz video başlığı ve açıklamasına dayanmaktadır. "
            "Bu bir 'TAHMİNİ ANALİZ'dir. "
            "Master Prompt'un başına mutlaka şu notu ekle: "
            "\"📊 [TAHMİNİ ANALİZ — Altyazı Yok]: Bu Master Prompt, videonun başlık ve açıklaması analiz edilerek tahminî olarak oluşturulmuştur. Gerçek altyazı verisi mevcut değildir.\"\n\n"
        )
        data_label = "[VİDEO METAVERİSİ (Başlık + Açıklama) - Altyazı Yok]"
        task_note = (
            "Altyazı olmadığı için tam bir tempo/retention analizi yapılamaz. "
            "Bunun yerine başlık ve açıklamadan çıkarılabilecek tarz, ton ve potansiyel kanca stratejisini tahmin et."
        )
    else:
        analysis_mode_note = ""
        data_label = "[VİDEO ALTYAZISI - İlk 3000 karakter]"
        task_note = "Bu videonun viral başarısını oluşturan unsurları derinlemesine analiz et ve aşağıdaki Master Prompt'u oluştur."

    # Skor seviyesi (Master Prompt tonunu belirler)
    overall = scores.get('overall', 0)
    if overall >= 80:
        tier_context = "Bu video EFSANEVİ düzeyde viral potansiyele sahip. Formülü birebir taklit et."
    elif overall >= 60:
        tier_context = "Bu video GÜÇLÜ bir içerik. Temel yapısını koru, zayıf noktaları güçlendir."
    else:
        tier_context = "Bu video GELİŞTİRİLEBİLİR potansiyelde. Hook ve Tempo'yu kökten yeniden tasarla."

    prompt = f"""Sen bir viral video uzmanısın. Aşağıdaki DNA yapısını kullanarak yeni bir senaryo yaz:

{analysis_mode_note}━━━ ANALİZ EDİLEN VİDEO ━━━
Başlık : {title}
Kanal  : {channel}
DNA Skorları: {scores_str}
Seviye : {tier_context}

━━━ {data_label} ━━━
{transcript_preview if transcript_preview else "Veri mevcut değil. Yalnızca başlık ve puanlara göre tahmini analiz yap."}

━━━ GÖREVİN ━━━
{task_note}

Aşağıdaki 4 bileşeni net talimatlar olarak yaz:

1. 🪝 KANCA TALİMATI (İlk 30 Saniye)
   — İzleyiciyi anında yakalayacak açılış cümlesini/sahnesini belirle.
   — Merak, şok veya vaat unsurlarından hangisini kullanacağını açıkça söyle.
   — Örnek kanca cümlesi ver.

2. ⏱️ TEMPO TALİMATI (Ritim Haritası)
   — Videonun hangi bölümünde hızlanma, hangisinde nefes alması gerektiğini belirt.
   — Cümle uzunluğu ve kesim sıklığına dair somut kural yaz. (örn: "Aksiyonlarda maks. 5 saniyelik plan")

3. 💥 DUYGU TALİMATI (Yoğunluk Haritası)
   — İzleyicide hangi duyguyu ne zaman tetikleyeceğini sırala.
   — En güçlü duygusal anı ("climax") ve nasıl kurulacağını açıkla.

4. 📣 CTA TALİMATI (Aksiyon Çağrısı)
   — Abone/beğeni çağrısının videoya nasıl doğal entegre edileceğini yaz.
   — Zorla değil, izleyicinin kendiliğinden tıklamak isteyeceği bir an yarat.

ÇIKTI FORMATI KURALI:
- Promptun ilk satırı mutlaka şu şablonla başlasın:
  "Sen bir viral video uzmanısın. Aşağıdaki DNA yapısını kullanarak yeni bir senaryo yaz:"
- Madde madde, doğrudan talimat dili kullan. ("Şunu yap", "Bunu söyle", "Bu anda kes")
- Türkçe yaz. Başka açıklama veya giriş cümlesi ekleme. Sadece hazır kullanılabilir promptu ver."""

    # ── i18n: lang='en' ise İngilizce direktif ekle
    _dna_lang_suffix = (
        "\n\nIMPORTANT: Write the ENTIRE Master Prompt (all 4 sections and all instructions) "
        "in ENGLISH language only. Do not use Turkish anywhere."
        if lang == "en" else ""
    )
    prompt += _dna_lang_suffix

    _dna_system = (
        "You are a viral YouTube DNA analyst. Produce only the requested output in English."
        if lang == "en" else
        "Sen viral YouTube içeriğinin genetik kodunu çözen bir DNA analistisin. Yalnızca istenilen çıktıyı üretirsin."
    )

    def _post():
        return _req.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": _dna_system},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 1200,
                "temperature": 0.65,
            },
            timeout=35,
        )

    resp = await run_in_threadpool(_post)
    if resp.status_code == 200:
        return resp.json()["choices"][0]["message"]["content"].strip()
    elif resp.status_code == 401:
        raise ValueError("Groq API anahtarı geçersiz.")
    elif resp.status_code == 429:
        raise ValueError("Groq API kotası doldu. Lütfen bekleyin.")
    else:
        raise ValueError(f"Groq API hatası: HTTP {resp.status_code}")


class DNAAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    videoId:     str = Field(default="", description="YouTube video ID")
    title:       str = Field(default="Başlık Yok")
    channel:     str = Field(default="Bilinmeyen Kanal")
    description: str = Field(default="", description="Video açıklaması (Fallback için)")
    tags:        str = Field(default="", description="Virgülle ayrılmış etiketler (Fallback için)")
    user_id:     int = Field(default=0)
    lang:        str = Field(default="tr", description="UI language: 'tr' or 'en'")


@app.post("/api/extension/dna_analysis")
async def extension_dna_analysis(payload: DNAAnalysisRequest):
    """
    🧬 DNA Analiz Motoru — v5.2.0 "Hibrit DNA"
    1. Transcript çek
    2. Eğer transcript yoksa → Başlık + Açıklama + Etiketlerden Fallback Metin oluştur
    3. 4 bölüme ayır → 4 saf-Python NLP puanı hesapla (hook, retention, cta, emotion)
    4. Fallback modda konuşma temelli metrikler (Tempo/Retention) metadata kalitesiyle simüle edilir
    5. Groq ile Master Prompt üret (fallback modda 'Tahmini Analiz' notu eklenir)
    6. is_estimated flag'iyle birlikte tüm verileri JSON döndür

    KISŞ PRENSİBİ: Hiçbir zaman "Hesaplanamadı" hatası vermez. Her video için anlamlı çıktı üretir.
    """
    app_logger.info(f"[dna_analysis] Başlatıldı: video_id={payload.videoId} title='{payload.title[:50]}'")

    video_id = payload.videoId.strip()
    if not video_id:
        raise HTTPException(status_code=400, detail="Video ID boş olamaz.")

    # ── 1. Transcript Çek ─────────────────────────────────────────────────────
    try:
        transcript = await run_in_threadpool(_fetch_transcript_sync, video_id)
    except Exception as e:
        app_logger.warning(f"[dna_analysis] Transcript çağrı hatası: {e}")
        transcript = ""

    if not transcript or transcript.startswith("HATA:"):
        transcript = ""

    # ── 2. Fallback: Altyazı yoksa Metadata metnini kullan ───────────────────
    is_estimated = False
    analysis_text = transcript

    if not transcript:
        app_logger.info(f"[dna_analysis] Altyazı yok → Metadata Fallback: video_id={video_id}")
        is_estimated = True
        # Başlık + Açıklama + Etiketleri birleştirerek analiz metni oluştur
        metadata_parts = []
        if payload.title and payload.title not in ("Başlık Yok", "Baslik Yok"):
            metadata_parts.append(payload.title)
        if payload.description:
            metadata_parts.append(payload.description[:2000])  # İlk 2000 karakter yeterli
        if payload.tags:
            metadata_parts.append(payload.tags)
        analysis_text = " ".join(metadata_parts).strip()

        if not analysis_text:
            # Son çare: Yalnızca başlığı kullan
            analysis_text = payload.title

    # ── 3. Metin Bölümle ─────────────────────────────────────────────────────
    sections = _dna_split_transcript(analysis_text)
    full_text = analysis_text

    # ── 4. NLP Puanları (Saf Python) ─────────────────────────────────────────
    hook_score      = _dna_hook_score(sections["intro"])
    emotion_score   = _dna_emotion_score(full_text)
    cta_score       = _dna_cta_score(sections["outro"])

    # Retention/Tempo: Altyazı tabanlı bir metriktir.
    # Fallback modda konuşma temposu ölçülemez; bunun yerine
    # başlık/açıklama zenginliğine göre simüle edilir.
    if is_estimated:
        # Metadata kalitesini word count ve cümle çeşitliliğine göre tahmin et
        import re as _re_ret
        word_count = len(full_text.split())
        sentence_count = len(_re_ret.split(r'[.!?]', full_text))
        # Makul bir aralıkta simüle edilmiş Tempo puanı (35–65 arası)
        simulated_retention = min(65.0, max(35.0, round(
            35.0 + min(30.0, (word_count / 50.0)) + min(15.0, sentence_count * 1.5)
        , 1)))
        retention_score = simulated_retention
    else:
        retention_score = _dna_retention_score(sections["dev_a"], sections["dev_b"])

    # ── Elite Calibration Algoritması v5.5.0 ─────────────────────────────────────
    # DR Koruması + Synergy Bonusu + Ceiling
    weighted_overall = _dna_elite_overall(hook_score, retention_score, cta_score, emotion_score)
    scores = {
        "hook":      hook_score,
        "retention": retention_score,
        "cta":       cta_score,
        "emotion":   emotion_score,
        "overall":   weighted_overall,
    }

    app_logger.info(f"[dna_analysis] Puanlar (is_estimated={is_estimated}): {scores}")

    # ── 5. Groq Master Prompt ─────────────────────────────────────────────────
    api_key = await get_groq_api_key()
    dna_prompt = None

    # Groq'a gönderilecek metin: Fallback modda başlık/açıklama kullanılır
    groq_text = analysis_text if is_estimated else transcript

    if api_key:
        try:
            dna_prompt = await _call_groq_dna_prompt(
                api_key, payload.title, payload.channel, groq_text, scores,
                is_estimated=is_estimated, lang=payload.lang
            )
        except Exception as e:
            app_logger.warning(f"[dna_analysis] Master Prompt üretilemedi: {e}")
            dna_prompt = f"Master Prompt üretilemedi: {str(e)}"
    else:
        dna_prompt = "Groq API anahtarı ayarlanmamış — Master Prompt üretilemedi."

    app_logger.info(f"[dna_analysis] ✅ Tamamlandı: video_id={video_id} is_estimated={is_estimated}")

    return {
        "success":              True,
        "is_estimated":         is_estimated,
        "transcript_available": not is_estimated,
        "transcript_length":    len(analysis_text),
        "scores": scores,
        "sections": {
            "intro_words":  len(sections["intro"].split()),
            "dev_words":    len(sections["dev_a"].split()) + len(sections["dev_b"].split()),
            "outro_words":  len(sections["outro"].split()),
        },
        "dna_prompt": dna_prompt,
    }


# ── Kanal DNA'sı: Son 5 Videonun Ortalama DNA Puanları ──────────────────────

class ChannelDNARequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    channel_url: str = Field(default="")
    user_id:     int = Field(default=0)
    lang:        str = Field(default="tr", description="UI language: 'tr' or 'en'")


@app.post("/api/extension/channel_dna")
async def extension_channel_dna(payload: ChannelDNARequest):
    """
    📊 Kanal DNA'sı
    Kanalın son 5 videosunu çek → Her birinin DNA puanlarını hesapla
    → Ortalamaları + Başarı Formülünü döndür.
    Fail-Fast: Altyazı olmayan videolar hesaba katılmaz; sayı bildirilir.
    """
    app_logger.info(f"[channel_dna] Başlatıldı: {payload.channel_url}")

    if not payload.channel_url:
        raise HTTPException(status_code=400, detail="Kanal URL'si boş olamaz.")

    # ── 1. Kanal Videolarını Çek ──────────────────────────────────────────────
    try:
        channel_data = await run_in_threadpool(extract_channel_stats_sync, payload.channel_url)
    except Exception as e:
        return {"success": False, "error": f"Kanal verileri çekilemedi: {str(e)}"}

    # extract_channel_stats_sync sadece 5 video URL'si + başlık döndürür.
    # Biz her videoyu ayrıca DNA analiz edeceğiz.
    channel_name = channel_data.get("channel_name", "Bilinmeyen Kanal")

    # Video ID'lerini çıkar (channel_data içinde video URL'si yoksa yt-dlp ile tekrar çek)
    import re as _re

    channel_url = payload.channel_url
    if not channel_url.endswith('/videos'):
        base_url = channel_url.split('/featured')[0].split('/shorts')[0].split('/streams')[0].rstrip('/')
        channel_url_videos = f"{base_url}/videos"
    else:
        channel_url_videos = channel_url

    video_ids = []
    try:
        import yt_dlp as _ydl_lib
        opts_ids = {
            'extract_flat': True,
            'playlist_end': 5,
            'quiet': True,
            'no_warnings': True,
        }
        with _ydl_lib.YoutubeDL(opts_ids) as ydl:
            info = ydl.extract_info(channel_url_videos, download=False)
            for entry in (info.get('entries') or []):
                if entry and entry.get('id'):
                    video_ids.append(entry['id'])
                elif entry and entry.get('url'):
                    u = entry['url']
                    m = _re.search(r'[?&]v=([^&]+)', u)
                    if m:
                        video_ids.append(m.group(1))
                    else:
                        vid = u.split('/')[-1].split('?')[0]
                        if vid:
                            video_ids.append(vid)
    except Exception as e:
        app_logger.warning(f"[channel_dna] Video ID çekme hatası: {e}")
        return {"success": False, "error": f"Kanal videoları listelenemedi: {str(e)}"}

    if not video_ids:
        return {"success": False, "error": "Kanalda video bulunamadı."}

    # ── 2. Her Video İçin DNA Puanı Hesapla (Hibrit: Altyazı → Metadata Fallback) ─
    all_scores    = []
    analyzed_count = 0
    skipped_count  = 0
    estimated_count = 0
    import re as _re_chan

    for vid_id in video_ids[:5]:
        try:
            tr = await run_in_threadpool(_fetch_transcript_sync, vid_id)
            if not tr or tr.startswith("HATA:"):
                tr = ""

            if tr:
                # ── Gerçek Altyazı Analizi ────────────────────────────────────
                sections = _dna_split_transcript(tr)
                s = {
                    "hook":      _dna_hook_score(sections["intro"]),
                    "retention": _dna_retention_score(sections["dev_a"], sections["dev_b"]),
                    "cta":       _dna_cta_score(sections["outro"]),
                    "emotion":   _dna_emotion_score(tr),
                    "is_estimated": False,
                }
            else:
                # ── Metadata Fallback: Kanalın bilinen videolarından başlık çek ─
                # channel_data içindeki başlıkları kullan (yt-dlp'den gelir)
                recent_titles = channel_data.get("recent_titles") or []
                # Kanalın genel başlık diline göre simüle edilmiş puan üret
                meta_text = " ".join(recent_titles[:5])
                if not meta_text.strip():
                    skipped_count += 1
                    continue
                word_count = len(meta_text.split())
                sentence_count = len(_re_chan.split(r'[.!?]', meta_text))
                simulated_retention = min(60.0, max(30.0, round(
                    30.0 + min(30.0, (word_count / 20.0)), 1
                )))
                s = {
                    "hook":      _dna_hook_score(meta_text),
                    "retention": simulated_retention,
                    "cta":       _dna_cta_score(meta_text),
                    "emotion":   _dna_emotion_score(meta_text),
                    "is_estimated": True,
                }
                estimated_count += 1

            all_scores.append(s)
            analyzed_count += 1
        except Exception as e:
            app_logger.warning(f"[channel_dna] video={vid_id} hata: {e}")
            skipped_count += 1
            continue

    # Hiç veri yoksa (video listesi boş veya tüm videolar hata verdi)
    if not all_scores:
        analyzed_amount = min(len(video_ids), 5)
        return {
            "success": False,
            "error": f"Kanalın son {analyzed_amount} videosu için hiç veri alınamadı.",
            "channel_name": channel_name,
        }

    # ── 3. Ortalama Puanlar ───────────────────────────────────────────────────
    avg_scores = {
        "hook":      round(sum(s["hook"]      for s in all_scores) / len(all_scores), 1),
        "retention": round(sum(s["retention"] for s in all_scores) / len(all_scores), 1),
        "cta":       round(sum(s["cta"]       for s in all_scores) / len(all_scores), 1),
        "emotion":   round(sum(s["emotion"]   for s in all_scores) / len(all_scores), 1),
    }
    # Kanal DNA genel skoru — Elite Calibration v5.5.0
    avg_scores["overall"] = _dna_elite_overall(
        avg_scores["hook"],
        avg_scores["retention"],
        avg_scores["cta"],
        avg_scores["emotion"],
    )

    # ── 4. Başarı Formülü (Groq) ──────────────────────────────────────────────
    api_key = await get_groq_api_key()
    success_formula = None
    if api_key:
        try:
            import requests as _req2
            titles_str = ", ".join(f'"{t}"' for t in (channel_data.get("recent_titles") or [])[:5])
            # i18n
            _formula_lang_rule = (
                "\n\nIMPORTANT: Write the ENTIRE Success Formula summary in ENGLISH language only. Do not use Turkish."
                if payload.lang == "en" else "Türkçe, kısa ve vurucu yaz."
            )
            
            formula_prompt = f"""Sen viral YouTube içerik analistisin.

[KANAL: {channel_name}]
Son videolar: {titles_str}
Ortalama DNA Puanları:
- Hook (Kanca): {avg_scores['hook']}/100
- Retention (Tempo): {avg_scores['retention']}/100
- CTA (Aksiyon Çağrısı): {avg_scores['cta']}/100
- Emotion (Duygu Yoğunluğu): {avg_scores['emotion']}/100

Bu kanalın "Başarı Formülü"nü 3-4 cümleyle özetle. Hangi DNA skoru en güçlü? En zayıf nokta ne? Bu kanala rakip olmak için neler denenebilir? {_formula_lang_rule}

{ADVISORY_TONE_RULE}"""

            def _fpost():
                return _req2.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={
                        "model": "llama-3.3-70b-versatile",
                        "messages": [{"role": "user", "content": formula_prompt}],
                        "max_tokens": 300,
                        "temperature": 0.5,
                    },
                    timeout=20,
                )

            fr = await run_in_threadpool(_fpost)
            if fr.status_code == 200:
                success_formula = fr.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            app_logger.warning(f"[channel_dna] Başarı formülü üretilemedi: {e}")

    channel_is_estimated = estimated_count == analyzed_count and analyzed_count > 0
    app_logger.info(f"[channel_dna] ✅ Tamamlandı: kanal={channel_name} analyzed={analyzed_count} skipped={skipped_count} estimated={estimated_count}")

    return {
        "success":         True,
        "is_estimated":    channel_is_estimated,
        "channel_name":    channel_name,
        "analyzed_count":  analyzed_count,
        "skipped_count":   skipped_count,
        "estimated_count": estimated_count,
        "avg_scores":      avg_scores,
        "success_formula": success_formula,
    }



# ═══════════════════════════════════════════════════════════════════════════════
#  🕵️  RIVAL DNA HIJACKER  —  v6.0.0
#
#  Rakip kanalın DNA puanlarını alır ve kullanıcının kanalına özgü
#  "Guerilla Strateji" (gizli saldırı planı) üretir.
#  Endpoit: POST /api/extension/guerilla_strategy
# ═══════════════════════════════════════════════════════════════════════════════

class GuerillaStrategyRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    # Rakip videonun verileri (Chrome Extension'dan gelir)
    rival_video_id:    str = Field(default="", description="Rakip YouTube video ID")
    rival_title:       str = Field(default="", description="Rakip video başlığı")
    rival_channel:     str = Field(default="", description="Rakip kanal adı")
    rival_channel_url: str = Field(default="", description="Rakip kanal URL'si")
    # Rakip DNA skorları (extension tarafından önceden hesaplanmış olabilir)
    dna_data: Optional[dict] = Field(default=None, description="Rakip kanalın önceden hesaplanan DNA skorları")
    # Kullanıcı bilgisi
    user_id:          int  = Field(default=0)
    target_channel_id: Optional[int] = Field(default=None, description="Seçili kanal ID (çoklu kanal senaryosu)")
    lang:             str  = Field(default="tr", description="UI dili: 'tr' veya 'en'")


@app.post("/api/extension/guerilla_strategy")
async def extension_guerilla_strategy(payload: GuerillaStrategyRequest):
    """
    🕵️ Rival DNA Hijacker — v6.0.0

    1. Rakip kanal/videonun DNA puanlarını al (dna_data payload'dan gelebilir
       veya sıfırdan hesaplanır).
    2. Kullanıcının kendi kanal profilini DB'den çek (content_type, purpose).
    3. Groq ile "Guerilla Strateji" üret:
       - Rakibin en güçlü DNA silahı ne?
       - Kullanıcının hangi alanda rakibi geçebileceği?
       - Rakibin zayıf noktasını hedef alan 3 spesifik aksiyon planı.
    4. Sonucu JSON döndür.
    """
    app_logger.info(f"[guerilla_strategy] Başlatıldı: rival='{payload.rival_channel}' user_id={payload.user_id}")

    # ── 1. Kullanıcı Kanal Profili ────────────────────────────────────────────
    content_type    = "General Content"
    purpose         = "Entertaining the Audience"
    my_channel_name = ""
    if payload.user_id:
        db = await get_async_db()
        try:
            if payload.target_channel_id:
                _gq = "SELECT content_type, purpose, name FROM channels WHERE id = ? AND user_id = ?"
                _gp = (payload.target_channel_id, payload.user_id)
            else:
                _gq = "SELECT content_type, purpose, name FROM channels WHERE user_id = ? LIMIT 1"
                _gp = (payload.user_id,)
            async with db.execute(_gq, _gp) as c:
                row = await c.fetchone()
                if row:
                    content_type    = row["content_type"] or content_type
                    purpose         = row["purpose"]      or purpose
                    my_channel_name = row["name"]         or ""
        finally:
            await db.close()

    # ── 2. Rakip DNA Skorları ─────────────────────────────────────────────────
    # dna_data payload'dan geldiyse kullan; yoksa temel değerler kabul et
    rival_dna = payload.dna_data or {}
    rival_hook      = rival_dna.get("hook",      50.0)
    rival_retention = rival_dna.get("retention", 50.0)
    rival_cta       = rival_dna.get("cta",       50.0)
    rival_emotion   = rival_dna.get("emotion",   50.0)
    rival_overall   = rival_dna.get("overall",   50.0)

    # ── 3. Groq API ───────────────────────────────────────────────────────────
    api_key = await get_groq_api_key()
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Groq API key is not set. Please add it from the application Settings panel."
        )

    _lang_rule = (
        "\n\nIMPORTANT: Write the ENTIRE Guerilla Strategy report in ENGLISH only. Do not use Turkish."
        if payload.lang == "en" else
        "Tüm raporu Türkçe yaz."
    )

    prompt = f"""Sen efsanevi bir YouTube Büyüme Hack'çisi ve rakip istihbarat uzmanısın.

━━━ KENDİ KANAL PROFİLİN ━━━
Kanal Adı  : {my_channel_name or "Bilinmiyor"}
İçerik Tipi: {content_type}
Amaç       : {purpose}

━━━ RAKİP KANAL DNA'SI ━━━
Rakip Kanal : {payload.rival_channel or "Bilinmiyor"}
Rakip Video : {payload.rival_title or "Belirtilmedi"}
Hook Skoru  : {rival_hook}/100
Retention   : {rival_retention}/100
CTA Skoru   : {rival_cta}/100
Emotion     : {rival_emotion}/100
Genel DNA   : {rival_overall}/100

━━━ GÖREVİN ━━━
Bu rakibin DNA verilerini analiz ederek bana SADECE aşağıdaki JSON formatında bir "Guerilla Strateji" raporu üret.
KURAL: Çıktı YALNIZCA geçerli JSON olmalıdır. Başka açıklama veya metin yazma.

{ADVISORY_TONE_RULE}

{{
  "rival_silah": "Rakibin en güçlü DNA silahı ve neden izleyiciyi bağladığı (2 cümle)",
  "benim_avantajim": "Rakibe kıyasla kendi kanalımın hangi alanda üstün olabileceği veya olabileceği fırsat (2 cümle)",
  "zayif_nokta": "Rakibin DNA'sındaki en kritik zayıf nokta (düşük skor veya tutarsızlık)",
  "aksiyon_plani": [
    {{
      "adim": 1,
      "baslik": "Aksiyon başlığı",
      "taktik": "Spesifik ve uygulanabilir taktik açıklaması",
      "hedef_metrik": "Bu aksiyonun hangi DNA metriğini hedeflediği"
    }},
    {{
      "adim": 2,
      "baslik": "Aksiyon başlığı",
      "taktik": "Spesifik ve uygulanabilir taktik açıklaması",
      "hedef_metrik": "Bu aksiyonun hangi DNA metriğini hedeflediği"
    }},
    {{
      "adim": 3,
      "baslik": "Aksiyon başlığı",
      "taktik": "Spesifik ve uygulanabilir taktik açıklaması",
      "hedef_metrik": "Bu aksiyonun hangi DNA metriğini hedeflediği"
    }}
  ],
  "guerilla_ozet": "3-4 cümlelik strateji özeti: rakibin hangi zayıf noktasından ne zaman ve nasıl faydalanabileceğin (öneri dilinde)"
}}{_lang_rule}"""

    def _gpost():
        import requests as _r
        return _r.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are an elite YouTube growth hacker. Produce ONLY valid JSON output, no additional text."
                            if payload.lang == "en" else
                            "Sen elit bir YouTube büyüme hack'çisisin. YALNIZCA geçerli JSON çıktısı üret, başka hiçbir metin yazma."
                        )
                    },
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 900,
                "temperature": 0.6,
            },
            timeout=30,
        )

    try:
        resp = await run_in_threadpool(_gpost)
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Groq API error: HTTP {resp.status_code}")

        raw = resp.json()["choices"][0]["message"]["content"].strip()
        # JSON bloğunu temizle
        _clean = re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()
        _match = re.search(r"\{.*\}", _clean, re.DOTALL)
        if not _match:
            raise HTTPException(status_code=500, detail="AI response did not contain valid JSON.")
        strategy = json.loads(_match.group(), strict=False)
    except HTTPException:
        raise
    except json.JSONDecodeError as e:
        app_logger.error(f"[guerilla_strategy] JSON parse hatası: {e}")
        raise HTTPException(status_code=500, detail=f"AI yanıtı JSON olarak ayrıştırılamadı: {e}")
    except Exception as e:
        app_logger.error(f"[guerilla_strategy] Beklenmeyen hata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Guerilla strateji üretilemedi: {e}")

    app_logger.info(f"[guerilla_strategy] ✅ Tamamlandı: rival='{payload.rival_channel}'")

    return {
        "success":       True,
        "rival_channel": payload.rival_channel,
        "rival_dna":     rival_dna,
        "my_channel":    my_channel_name,
        "content_type":  content_type,
        "strategy":      strategy,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  ✍️  SCRIPT DOCTOR  —  v6.0.0
#
#  Rakip videonun DNA verilerini referans alarak kullanıcının kanalına
#  özgü, viral kanca + senaryo taslağı üretir.
#  Endpoint: POST /api/extension/generate_hook_script
# ═══════════════════════════════════════════════════════════════════════════════

class HookScriptRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    # Hedef video (rakip ya da referans video)
    video_id:    str  = Field(default="", description="Referans YouTube video ID")
    video_url:   str  = Field(default="", description="Referans YouTube video URL")
    title:       str  = Field(default="", description="Video başlığı")
    channel:     str  = Field(default="", description="Kanal adı")
    # Rakip DNA verileri (opsiyonel — varsa daha isabetli sonuç üretilir)
    dna_data:    Optional[dict] = Field(default=None, description="Referans videonun DNA skorları")
    # Kullanıcı bilgisi
    user_id:          int  = Field(default=0)
    target_channel_id: Optional[int] = Field(default=None, description="Seçili kanal ID (çoklu kanal senaryosu)")
    lang:             str  = Field(default="tr", description="UI dili: 'tr' veya 'en'")


@app.post("/api/extension/generate_hook_script")
async def extension_generate_hook_script(payload: HookScriptRequest):
    """
    ✍️ Script Doctor — v6.0.0

    Rakip/referans videonun DNA verilerini ve transcript'ini okuyarak
    kullanıcının kendi kanalına uygun viral bir hook + senaryo taslağı üretir.

    Adımlar:
    1. Transcript çek (opsiyonel — yoksa metadata ile fallback)
    2. Kullanıcı kanal profili DB'den alınır (content_type, purpose)
    3. Groq ile kanca (ilk 30sn) + 3 farklı senaryo taslağı üretilir
    4. Sonuç JSON döndürülür
    """
    app_logger.info(f"[generate_hook_script] Başlatıldı: video_id={payload.video_id} user_id={payload.user_id}")

    # ── Video ID çıkar ────────────────────────────────────────────────────────
    video_id = payload.video_id.strip()
    if not video_id and "v=" in payload.video_url:
        from urllib.parse import urlparse, parse_qs
        video_id = parse_qs(urlparse(payload.video_url).query).get("v", [""])[0]

    # ── 1. Transcript çek ─────────────────────────────────────────────────────
    transcript = ""
    if video_id:
        try:
            transcript = await run_in_threadpool(_fetch_transcript_sync, video_id)
            if not transcript or transcript.startswith("HATA:") or transcript.startswith("ERROR:"):
                transcript = ""
        except Exception as e:
            app_logger.warning(f"[generate_hook_script] Transcript hatası: {e}")
            transcript = ""

    # ── 2. Kullanıcı Kanal Profili ────────────────────────────────────────────
    content_type    = "General Content"
    purpose         = "Entertaining the Audience"
    my_channel_name = ""
    if payload.user_id:
        db = await get_async_db()
        try:
            if payload.target_channel_id:
                _hq = "SELECT content_type, purpose, name FROM channels WHERE id = ? AND user_id = ?"
                _hp = (payload.target_channel_id, payload.user_id)
            else:
                _hq = "SELECT content_type, purpose, name FROM channels WHERE user_id = ? LIMIT 1"
                _hp = (payload.user_id,)
            async with db.execute(_hq, _hp) as c:
                row = await c.fetchone()
                if row:
                    content_type    = row["content_type"] or content_type
                    purpose         = row["purpose"]      or purpose
                    my_channel_name = row["name"]         or ""
        finally:
            await db.close()

    # ── 3. DNA Skoru ──────────────────────────────────────────────────────────
    ref_dna      = payload.dna_data or {}
    ref_hook     = ref_dna.get("hook",      0.0)
    ref_retention= ref_dna.get("retention", 0.0)
    ref_overall  = ref_dna.get("overall",   0.0)

    # ── 4. Groq API ───────────────────────────────────────────────────────────
    api_key = await get_groq_api_key()
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Groq API key is not set. Please add it from the application Settings panel."
        )

    _lang_rule_hs = (
        "\n\nIMPORTANT: Write the ENTIRE hook script output in ENGLISH only. Do not use Turkish."
        if payload.lang == "en" else
        "Tüm çıktıyı Türkçe yaz."
    )

    transcript_preview = (transcript or "")[:2500]
    has_transcript = bool(transcript_preview.strip())

    prompt_hs = f"""Sen dünyanın en iyi YouTube senaryo doktoru ve viral kanca uzmanısın.

━━━ KENDİ KANAL PROFİLİN ━━━
Kanal Adı  : {my_channel_name or "Bilinmiyor"}
İçerik Tipi: {content_type}
Amaç       : {purpose}

━━━ REFERANS VİDEO ━━━
Video Başlık : {payload.title or "Belirtilmedi"}
Kanal        : {payload.channel or "Belirtilmedi"}
Hook Skoru   : {ref_hook}/100  {"(Yüksek kanca — bu formülü analiz et!)" if ref_hook >= 70 else "(Düşük kanca — bu hatadan öğren!)"}
Retention    : {ref_retention}/100
DNA Genel    : {ref_overall}/100

━━━ {"REFERANS VİDEO ALTYAZISI (İlk 2500 karakter)" if has_transcript else "ALTYAZI YOK — SADECE BAŞLIK VE DNA VERİSİ KULLANILACAK"} ━━━
{transcript_preview if has_transcript else "Altyazı bulunamadı. Başlık ve DNA skorlarından tahmini analiz yap."}

━━━ GÖREVİN ━━━
Bu referans videoyu inceleyerek benim kanalım ({content_type} / {purpose}) için VİRAL bir hook ve senaryo taslağı üret.
KURAL: Çıktı YALNIZCA aşağıdaki JSON formatında olmalıdır. Başka hiçbir metin yazma.

{ADVISORY_TONE_RULE_CREATIVE}

{{
  "kanca_analizi": "Referans videonun kanca stratejisi ve neden etkili/etkisiz olduğu (2 cümle)",
  "benim_kancam": {{
    "ilk_cumle": "İzleyiciyi ilk 3 saniyede yakalayacak açılış cümlesi (kanalıma özel)",
    "psikolojik_tetikleyici": "Hangi psikolojik mekanizmayı tetikliyor? (Merak/Şok/Vaat/Korku)",
    "gorsel_eylem": "Ekran üzerinde ne görünmeli / nasıl bir sahne kurulmalı?"
  }},
  "senaryo_taslaklari": [
    {{
      "versiyon": "A — Agresif Hook",
      "baslik_onerisi": "Bu konsept için önerilen başlık",
      "senaryo": "İlk 60 saniyenin senaryo taslağı (madde madde, konuşma diliyle)"
    }},
    {{
      "versiyon": "B — Merak Hook",
      "baslik_onerisi": "Bu konsept için önerilen başlık",
      "senaryo": "İlk 60 saniyenin senaryo taslağı (madde madde, konuşma diliyle)"
    }},
    {{
      "versiyon": "C — Şok Hook",
      "baslik_onerisi": "Bu konsept için önerilen başlık",
      "senaryo": "İlk 60 saniyenin senaryo taslağı (madde madde, konuşma diliyle)"
    }}
  ],
  "tempo_tavsiyesi": "Videonun ritim/tempo önerisi: kesim sıklığı, cümle uzunluğu (2-3 cümle)"
}}{_lang_rule_hs}"""

    def _hspost():
        import requests as _r
        return _r.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are the world's best YouTube Script Doctor. Produce ONLY valid JSON output."
                            if payload.lang == "en" else
                            "Sen dünyanın en iyi YouTube Senaryo Doktoru'sun. YALNIZCA geçerli JSON çıktısı üret."
                        )
                    },
                    {"role": "user", "content": prompt_hs}
                ],
                "max_tokens": 1400,
                "temperature": 0.65,
            },
            timeout=35,
        )

    try:
        resp_hs = await run_in_threadpool(_hspost)
        if resp_hs.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Groq API error: HTTP {resp_hs.status_code}")

        raw_hs = resp_hs.json()["choices"][0]["message"]["content"].strip()
        _clean_hs = re.sub(r"```(?:json)?", "", raw_hs).replace("```", "").strip()
        _match_hs = re.search(r"\{.*\}", _clean_hs, re.DOTALL)
        if not _match_hs:
            raise HTTPException(status_code=500, detail="AI response did not contain valid JSON.")
        hook_script = json.loads(_match_hs.group(), strict=False)
    except HTTPException:
        raise
    except json.JSONDecodeError as e:
        app_logger.error(f"[generate_hook_script] JSON parse hatası: {e}")
        raise HTTPException(status_code=500, detail=f"AI yanıtı JSON olarak ayrıştırılamadı: {e}")
    except Exception as e:
        app_logger.error(f"[generate_hook_script] Beklenmeyen hata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Hook script üretilemedi: {e}")

    app_logger.info(f"[generate_hook_script] ✅ Tamamlandı: video_id={video_id} has_transcript={has_transcript}")

    return {
        "success":          True,
        "video_id":         video_id,
        "reference_title":  payload.title,
        "my_channel":       my_channel_name,
        "content_type":     content_type,
        "has_transcript":   has_transcript,
        "transcript_length": len(transcript),
        "ref_dna":          ref_dna,
        "hook_script":      hook_script,
    }


@app.get("/health")

async def health():

    return {
        "status": "online",
        "ffmpeg_available": FFMPEG_AVAILABLE,
        "gpu_codec": GPU_CODEC,
        "system_caps": SYSTEM_CAPS
    }


@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="critical", access_log=False)


if __name__ == "__main__":
    init_db()

    # IF you want to move your old data (guest) to your new account (ID: 2)
    # remove the '#' sign at the beginning of the following line once and run:
    # migrate_data(2)

    threading.Thread(target=run_server, daemon=True).start()
    time.sleep(2)

    webview.create_window(
        "YouTube Analiz Pro V4.0 — SaaS Edition",
        "http://127.0.0.1:8000",
        width=1050,
        height=900
    )
    webview.start()
