"""
app/services/analysis_engine.py
─────────────────────────────────
Analiz motoru — server.pyw'dan ayrıştırıldı (FAZ 2.2 Refactor).

İçerik:
  • INDUSTRY_STANDARDS    : Sektörel karşılaştırma eşikleri
  • AnalysisEngine        : Video analiz sınıfı (görsel tempo, ses, sahne,
                            thumbnail, viral segment, DB kayıt)
"""

import os
import gc
import json
import uuid
import logging
import subprocess
import traceback
import numpy as np
import cv2
import librosa
from typing import Dict, List, Optional

from app.database.db import get_async_db
from app.services.ai_service import generate_ai_game_feedback

# DeepFace optional
try:
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
except ImportError:
    DEEPFACE_AVAILABLE = False

# ColorThief optional
try:
    from colorthief import ColorThief
    COLORTHIEF_AVAILABLE = True
except ImportError:
    COLORTHIEF_AVAILABLE = False

_logger = logging.getLogger("yt_analiz.analysis_engine")


# ─── run_cmd helper (duplicate of the same function in server.pyw) ────────────
def _run_cmd(cmd_list, timeout=None):
    kwargs = {'stdout': subprocess.DEVNULL, 'stderr': subprocess.DEVNULL}
    if os.name == 'nt':
        kwargs['creationflags'] = 0x08000000
    return subprocess.run(cmd_list, check=True, timeout=timeout, **kwargs)


# ─── get_dynamic_timeout helper ───────────────────── ─────────────────────
import re as _re

def _get_dynamic_timeout(video_path: str, min_timeout: int = 120) -> Optional[int]:
    try:
        probe_cmd = ["ffmpeg", "-i", video_path, "-hide_banner"]
        probe_kwargs = {'capture_output': True, 'text': True, 'timeout': 10}
        if os.name == 'nt':
            probe_kwargs['creationflags'] = 0x08000000
        result = subprocess.run(probe_cmd, **probe_kwargs)
        match = _re.search(r'Duration:\s*(\d+):(\d+):(\d+)', result.stderr)
        if match:
            h, m, s = int(match.group(1)), int(match.group(2)), int(match.group(3))
            duration_sec = h * 3600 + m * 60 + s
            return max(min_timeout, duration_sec * 2)
    except Exception as e:
        _logger.error(f"Kritik Analiz Hatası: {str(e)}", exc_info=True)
        raise  # Hatanın yukarı sızmasına izin ver
    return None


# ─── INDUSTRY_STANDARDS ─────────────────────────── ───────────────────────────

INDUSTRY_STANDARDS = {
    'gaming': {'tempo': 8.8, 'seo': 7.5, 'retention': 4.5},
    'eğitim': {'tempo': 4.5, 'seo': 9.5, 'retention': 7.0},
    'vlog': {'tempo': 7.5, 'seo': 6.5, 'retention': 5.5},
    'finance': {'tempo': 5.0, 'seo': 8.5, 'retention': 6.5},
    'shorts': {'tempo': 9.5, 'seo': 5.0, 'retention': 8.5},
    'default': {'tempo': 7.0, 'seo': 8.0, 'retention': 6.0}
}


# ─── AnalysisEngine ───────────────────────────── ──────────────────────────────

class AnalysisEngine:

    @staticmethod
    def get_industry_standard(c_type: str):
        c_type = c_type.lower()
        for key, std in INDUSTRY_STANDARDS.items():
            if key in c_type:
                return std
        return INDUSTRY_STANDARDS['default']

    @staticmethod
    async def generate_dynamic_feedback(c_type, c_aud, c_purp, tech_score, retention_score, peaks,
                                        lang="tr", thumb_insights: dict = None,
                                        visual_insights_str: str = ""):

        c_type_raw = c_type.lower()
        c_aud_raw = c_aud.lower() if c_aud else "izleyici"
        if len(c_aud_raw) > 40:
            c_aud_raw = c_aud_raw[:37] + "..."
        feedback = ""
        is_en = (lang == "en")
        is_es = (lang == "es")

        # --- Hardcoded keyword routing removed for neutrality ---
        ai_feedback = await generate_ai_game_feedback(
            c_type, c_aud, c_purp, tech_score, retention_score, peaks, lang,
            visual_insights=visual_insights_str
        )
        if ai_feedback:
            feedback = ai_feedback
        else:
            prefix = "📢 " + ("CHANNEL ANALYSIS" if is_en else "ANÁLISIS DE CANAL" if is_es else "KANAL ANALİZİ") + f" ({c_type_raw.upper()}): "
            if tech_score < 5.0:
                feedback = (f"{prefix}" +
                            (f"There's stagnation. Tighten the editing a bit so the '{c_aud_raw}' audience doesn't get bored." if is_en else
                            f"Hay estancamiento. Ajusta un poco el montaje para que la audiencia '{c_aud_raw}' no se aburra." if is_es else
                            f"Durağanlık var. '{c_aud_raw}' kitlesini sıkmamak için kurguyu biraz sıkılaştır."))
            elif retention_score < 5.0:
                feedback = (f"{prefix}" +
                            (f"People are clicking on your video but '{c_aud_raw}' is leaving immediately. Speed up the intro." if is_en else
                            f"La gente hace clic en tu video pero '{c_aud_raw}' se va inmediatamente. Acelera la introducción." if is_es else
                            f"İnsanlar videona tıklıyor ama '{c_aud_raw}' hemen çıkıyor. Girişi hızlandır."))
            else:
                feedback = (f"{prefix}" +
                            (f"You've found a good balance suitable for your channel type." if is_en else
                            f"Has encontrado un buen equilibrio adecuado para el tipo de tu canal." if is_es else
                            f"Kanalının türüne uygun bir denge yakalamışsın."))

        # ── Visual intelligence annotation (Stage 3) ──
        if thumb_insights and thumb_insights.get("visual_summary"):
            vs = thumb_insights["visual_summary"]
            feedback += f" 📸 [{vs}]"

        return feedback

    @staticmethod
    def analyze_visual_tempo(video_path: str, pro_mode: bool) -> List[float]:
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps == 0 or np.isnan(fps):
            fps = 30
        frame_skip = int(fps / 5) if pro_mode else int(fps)
        tempo_map, current_sec_diffs, prev_frame, frame_count = [], [], None, 0
        gc_counter = 0
        try:
            while True:
                ret = cap.grab()
                if not ret:
                    break
                if frame_count % frame_skip == 0:
                    ret, frame = cap.retrieve()
                    if not ret:
                        continue
                    small_frame = cv2.resize(frame, (320, int((320 / frame.shape[1]) * frame.shape[0])))
                    gray = cv2.GaussianBlur(cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY), (21, 21), 0)
                    if prev_frame is not None:
                        thresh = cv2.threshold(cv2.absdiff(gray, prev_frame), 25, 255, cv2.THRESH_BINARY)[1]
                        current_sec_diffs.append((np.sum(thresh) / thresh.size) / 255 * 100)
                        del thresh
                    prev_frame = gray
                    del frame, small_frame
                    # Every time at least 1 value is collected (or as many fps in pro mode) add it to the tempo map
                    threshold_count = int(fps) if pro_mode else 1
                    if len(current_sec_diffs) >= threshold_count:
                        tempo_map.append(round(float(np.mean(current_sec_diffs)), 2))
                        current_sec_diffs = []
                    gc_counter += 1
                    if gc_counter % 100 == 0:
                        gc.collect()
                frame_count += 1
        except Exception as e:
            _logger.warning(f"Hata [analyze_visual_tempo]: {e}")
        finally:
            cap.release()
            gc.collect()
        return tempo_map

    @staticmethod
    def analyze_audio_per_sec(video_path: str, pro_mode: bool) -> List[float]:
        temp_audio = f"temp_coach_{uuid.uuid4().hex[:5]}.wav"
        audio_map = []
        sr_val = 22050 if pro_mode else 11025
        try:
            _run_cmd(["ffmpeg", "-y", "-hwaccel", "auto", "-i", video_path, "-vn", "-acodec", "pcm_s16le", "-ar", str(sr_val), "-ac", "1", temp_audio], timeout=_get_dynamic_timeout(video_path))

            # --- CHUNK-BASED: Process audio piece by piece, without pressing RAM ---
            frame_length = 2048
            hop_length = sr_val  # Original: 1 RMS value every second
            block_length = 256

            all_rms = []
            stream = librosa.stream(
                temp_audio,
                block_length=block_length,
                frame_length=frame_length,
                hop_length=hop_length
            )
            for y_block in stream:
                rms_block = librosa.feature.rms(
                    y=y_block,
                    frame_length=frame_length,
                    hop_length=hop_length,
                    center=False
                )[0]
                all_rms.append(rms_block)

            if all_rms:
                rms = np.concatenate(all_rms)
                audio_map = [round(float(v) * 100, 2) for v in rms]
                del all_rms, rms
                gc.collect()
        except Exception as e:
            _logger.warning(f"Hata [analyze_audio_per_sec]: {e}")
        finally:
            if os.path.exists(temp_audio):
                try:
                    os.remove(temp_audio)
                except Exception as e:
                    _logger.debug(f"Geçici ses dosyası silinemedi: {e}")
        return audio_map

    @staticmethod
    def analyze_scene_changes(video_path: str, ch_type: str = "default") -> Dict:
        """
        Sahne değişimlerini ve hareket yoğunluğunu tespit eder.
        ch_type'a göre adaptif eşik kullanır.
        """
        ch_lower = ch_type.lower()
        gaming_keys = ['gaming', 'oyun', 'fps', 'valorant', 'fortnite', 'gta',
                       'cs2', 'apex', 'warzone', 'pubg']
        education_keys = ['eğitim', 'ders', 'tutorial', 'podcast', 'bilgi', 'belgesel']
        vlog_keys = ['vlog', 'günlük', 'daily']

        if any(k in ch_lower for k in gaming_keys):
            scene_threshold = 40.0
        elif any(k in ch_lower for k in education_keys):
            scene_threshold = 25.0
        elif any(k in ch_lower for k in vlog_keys):
            scene_threshold = 32.0
        else:
            scene_threshold = 30.0

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps == 0 or np.isnan(fps):
            fps = 30
        frame_skip = max(1, int(fps / 3))
        cut_times = []
        motion_values = []
        prev_hist = None
        prev_gray = None
        frame_count = 0
        gc_counter = 0

        try:
            while True:
                ret = cap.grab()
                if not ret:
                    break
                if frame_count % frame_skip == 0:
                    ret, frame = cap.retrieve()
                    if not ret:
                        continue
                    small = cv2.resize(frame, (160, 90))
                    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
                    hist = cv2.calcHist([gray], [0], None, [64], [0, 256])
                    cv2.normalize(hist, hist)

                    if prev_hist is not None:
                        diff = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CHISQR)
                        current_time = frame_count / fps
                        if diff > scene_threshold:
                            cut_times.append(round(current_time, 1))

                    if prev_gray is not None:
                        motion = float(np.mean(cv2.absdiff(gray, prev_gray)))
                        motion_values.append(motion)

                    prev_hist = hist
                    prev_gray = gray
                    del frame, small
                    gc_counter += 1
                    if gc_counter % 150 == 0:
                        gc.collect()
                frame_count += 1
        except Exception as e:
            _logger.warning(f"Hata [analyze_scene_changes]: {e}")
        finally:
            cap.release()
            gc.collect()

        total_duration = frame_count / fps if fps > 0 else 1.0
        cut_frequency = round(len(cut_times) / max(1.0, total_duration / 60.0), 1)
        avg_motion = round(float(np.mean(motion_values)), 2) if motion_values else 0.0
        # Downsample motion_values ​​for response size
        step = max(1, len(motion_values) // 200)
        sampled_motion = [round(v, 2) for v in motion_values[::step]] if motion_values else []

        return {
            "cut_times": cut_times[:100],
            "cut_count": len(cut_times),
            "cut_frequency": cut_frequency,
            "avg_motion_intensity": avg_motion,
            "motion_values": sampled_motion,
            "scene_threshold_used": scene_threshold,
            "total_duration": round(total_duration, 1)
        }

    @staticmethod
    def analyze_thumbnail(path: str) -> Dict:
        """
        Gelişmiş thumbnail analizi (Aşama 3):
        - DeepFace ile yüz/duygu/bakış yönü tespiti
        - Michelson kontrast oranı
        - Metin yerleşim alanı (Rule of Thirds)
        - Canlı renk paleti uyumu (YouTube vibrant colors)
        """
        result = {
            "score": 0.0, "face_detected": False, "face_count": 0,
            "faces": [], "contrast_ratio": 0.0, "text_space_score": 0.0,
            "vibrant_color_match": 0.0, "visual_summary": ""
        }
        try:
            if not os.path.exists(path) or os.path.getsize(path) == 0:
                return result
            img = cv2.imread(path)
            if img is None:
                return result

            h, w = img.shape[:2]
            summary_parts = []
            face_bonus = 0.0

            # ── 1. DEEPFACE: Face + Emotion + Gaze Direction ──
            if DEEPFACE_AVAILABLE:
                try:
                    analyses = None
                    # NOT: opencv backend kaldırıldı — Haar Cascade çok fazla yanlış pozitif üretiyor
                    for backend in ['retinaface', 'mtcnn']:
                        try:
                            analyses = DeepFace.analyze(
                                img_path=path,
                                actions=['emotion'],
                                detector_backend=backend,
                                enforce_detection=True,
                                silent=True
                            )
                            break
                        except ValueError:
                            continue
                        except Exception:
                            continue

                    if not analyses:
                        raise ValueError("No face detected by any backend")

                    if not isinstance(analyses, list):
                        analyses = [analyses]

                    valid_faces = []
                    for face_data in analyses:
                        region = face_data.get("region", {})
                        fw = region.get("w", 0)
                        fh = region.get("h", 0)
                        # Minimum yüz boyutu: thumbnail'in en az %8'i olmalı
                        if fw < w * 0.08 or fh < h * 0.08:
                            continue
                        # En-boy oranı kontrolü: gerçek yüzler 0.5-2.0 aralığında
                        aspect_ratio = fw / fh if fh > 0 else 0
                        if aspect_ratio < 0.5 or aspect_ratio > 2.0:
                            continue

                        dominant = face_data.get("dominant_emotion", "neutral")
                        emotions = face_data.get("emotion", {})
                        # Güven eşiği: dominant duygunun güveni %45'in altındaysa yüzü reddet
                        dominant_confidence = emotions.get(dominant, 0)
                        if dominant_confidence < 45.0:
                            continue

                        face_cx = region.get("x", 0) + fw / 2
                        face_cy = region.get("y", 0) + fh / 2
                        center_dist_x = abs(face_cx - w / 2) / (w / 2) if w > 0 else 1
                        center_dist_y = abs(face_cy - h / 2) / (h / 2) if h > 0 else 1
                        looking_at_camera = center_dist_x < 0.4 and center_dist_y < 0.5

                        valid_faces.append({
                            "dominant_emotion": dominant,
                            "emotion_scores": {k: round(v, 1) for k, v in emotions.items()},
                            "region": {"x": region.get("x", 0), "y": region.get("y", 0),
                                       "w": fw, "h": fh},
                            "looking_at_camera": looking_at_camera
                        })

                    if valid_faces:
                        result["face_detected"] = True
                        result["face_count"] = len(valid_faces)
                        result["faces"] = valid_faces
                        primary = valid_faces[0]
                        emo = primary["dominant_emotion"]

                        high_ctr = {"surprise": 2.5, "happy": 2.0, "fear": 2.2, "angry": 1.5}
                        face_bonus = high_ctr.get(emo, 0.8)
                        if primary["looking_at_camera"]:
                            face_bonus += 0.5

                        emo_tr = {"surprise": "şaşkın", "happy": "mutlu", "fear": "korkmuş",
                                  "angry": "kızgın", "sad": "üzgün", "neutral": "nötr",
                                  "disgust": "tiksinti"}
                        # Hardcoded face texts were completely scrubbed upon user request
                        # summary_parts.append(f"Thumbnail has a face {emo_tr.get(emo, emo)}")
                        # if primary["looking_at_camera"]:
                        # summary_parts.append("looking at camera")
                except Exception as e:
                    print(f"DeepFace analiz hatası: {e}")
            else:
                pass

            # ── 2. CONTRAST RATIO (Michelson Contrast) ──
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l_ch, a_ch, b_ch = cv2.split(lab)
            l_min = float(np.percentile(l_ch, 5))
            l_max = float(np.percentile(l_ch, 95))

            if (l_max + l_min) > 0:
                michelson = (l_max - l_min) / (l_max + l_min)
            else:
                michelson = 0.0
            result["contrast_ratio"] = round(michelson, 3)

            if 0.4 <= michelson <= 0.8:
                contrast_10 = 10.0
            elif michelson > 0.8:
                contrast_10 = max(6.0, 10.0 - (michelson - 0.8) * 15)
            else:
                contrast_10 = max(2.0, michelson / 0.4 * 10.0)

            if michelson >= 0.5:
                summary_parts.append("kontrast çok iyi")
            elif michelson >= 0.3:
                summary_parts.append("kontrast orta düzeyde")
            else:
                summary_parts.append("kontrast düşük")

            # ── 3. TEXT SETTLEMENT AREA ──
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            regions_var = [
                float(np.std(gray[:h // 4, :])),
                float(np.std(gray[3 * h // 4:, :])),
                float(np.std(gray[:, :w // 3])),
                float(np.std(gray[:, 2 * w // 3:])),
            ]
            min_var = min(regions_var)
            if min_var < 25:
                text_space_10 = 10.0
            elif min_var < 40:
                text_space_10 = 7.5
            elif min_var < 55:
                text_space_10 = 5.0
            else:
                text_space_10 = max(2.0, 10.0 - (min_var - 30) * 0.15)
            result["text_space_score"] = round(text_space_10, 1)

            # ── 4. VIBRANT COLOR PALETTE HARMONY ──
            vibrant_palette_bgr = [
                (0, 0, 255), (0, 215, 255), (212, 188, 0), (53, 107, 255),
                (20, 255, 57), (182, 89, 155), (0, 69, 255), (0, 165, 255),
            ]
            vibrant_10 = 5.0
            try:
                if COLORTHIEF_AVAILABLE:
                    ct = ColorThief(path)
                    palette = ct.get_palette(color_count=5, quality=5)
                    best_dist = 999.0
                    for dom_rgb in palette:
                        dom_bgr = np.array(
                            [[[dom_rgb[2], dom_rgb[1], dom_rgb[0]]]], dtype=np.uint8)
                        dom_lab = cv2.cvtColor(dom_bgr, cv2.COLOR_BGR2LAB)[0][0].astype(float)
                        for vib_bgr in vibrant_palette_bgr:
                            vib_arr = np.array(
                                [[[vib_bgr[0], vib_bgr[1], vib_bgr[2]]]], dtype=np.uint8)
                            vib_lab = cv2.cvtColor(
                                vib_arr, cv2.COLOR_BGR2LAB)[0][0].astype(float)
                            dist = float(np.sqrt(np.sum((dom_lab - vib_lab) ** 2)))
                            if dist < best_dist:
                                best_dist = dist
                    if best_dist < 20:
                        vibrant_10 = 10.0
                    elif best_dist < 40:
                        vibrant_10 = 8.0
                    elif best_dist < 60:
                        vibrant_10 = 6.0
                    elif best_dist < 80:
                        vibrant_10 = 4.0
                    else:
                        vibrant_10 = 2.0
                else:
                    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
                    mean_sat = float(np.mean(hsv[:, :, 1]))
                    vibrant_10 = min(10.0, mean_sat / 12.8)
            except Exception:
                vibrant_10 = 5.0
            result["vibrant_color_match"] = round(vibrant_10, 1)
            if vibrant_10 >= 7:
                summary_parts.append("canlı renk paleti güçlü")

            # ── 5. BRIGHTNESS + SATURATION ──
            mean_l = float(np.mean(l_ch))
            if 40 <= mean_l <= 80:
                brightness_10 = 10.0
            elif mean_l < 40:
                brightness_10 = max(3.0, (mean_l / 40.0) * 10.0)
            else:
                brightness_10 = max(3.0, (1 - (mean_l - 80) / 175) * 10.0)
            sat_std = (float(np.std(a_ch)) + float(np.std(b_ch))) / 2
            saturation_10 = min(10.0, sat_std * 0.4)

            # ── 6. TOTAL SCORE ──
            face_10 = min(10.0, face_bonus * 3.3)
            if result["face_detected"]:
                total = (brightness_10 * 0.10 + saturation_10 * 0.10 +
                         contrast_10 * 0.20 + text_space_10 * 0.15 +
                         vibrant_10 * 0.15 + face_10 * 0.30)
            else:
                total = (brightness_10 * 0.15 + saturation_10 * 0.15 +
                         contrast_10 * 0.25 + text_space_10 * 0.20 +
                         vibrant_10 * 0.25)
            result["score"] = round(max(0.0, min(10.0, total)), 1)
            if not result["face_detected"]:
                result["visual_summary"] = "(Yüz bulunamadı; ya direkt yok ya da çok küçük)"
            else:
                result["visual_summary"] = (
                    " ve ".join(summary_parts) if summary_parts
                    else "Thumbnail analizi tamamlandı"
                )
        except Exception as e:
            print(f"Thumbnail analiz hatası: {e}")
            traceback.print_exc()
        return result

    @staticmethod
    async def save_analysis(channel_id: int, result: Dict, user_id: int = 1) -> int:
        db = await get_async_db()
        try:
            comp_dict = result.get("competitor_data", {})
            if isinstance(comp_dict, dict):
                comp_dict["face_detected"] = result.get("thumb_data", {}).get("face_detected", False)
                comp_dict["_thumb_data"] = result.get("thumb_data", {})
                comp_dict["_viral_segments"] = result.get("viral_segments", [])

            comp_str = json.dumps(comp_dict)
            peak_count = int(result.get("peaks", 0))
            duration_sec = result.get("analysis_duration_sec", 0)

            await db.execute('''INSERT INTO analyses (
                                channel_id, video_name, overall_score, retention_score,
                                tech_score, seo_score, thumb_score, peaks, viral_score,
                                coach_feedback, competitor_data, analysis_duration_sec, user_id
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (channel_id, result.get("title", "Bilinmeyen Video"),
                       result.get("overall_score", 0), result.get("retention_score", 0),
                       result.get("tech_score", 0), result.get("seo_score", 0),
                       result.get("thumb_score", 0),
                       peak_count,
                       result.get("viral_score", 0), result.get("dynamic_feedback", ""),
                       comp_str, duration_sec, user_id))

            async with db.execute("SELECT last_insert_rowid()") as cursor:
                row = await cursor.fetchone()
                analysis_id = row[0]
            await db.commit()
            return analysis_id
        finally:
            await db.close()

    @staticmethod
    def analyze_video_tech(video_path: str, pro_mode: bool) -> Dict:
        temp_audio = f"temp_audio_{uuid.uuid4().hex[:8]}.wav"
        sr_val = 22050 if pro_mode else 11025
        try:
            _run_cmd(["ffmpeg", "-y", "-hwaccel", "auto", "-i", video_path, "-vn", "-acodec", "pcm_s16le", "-ar", str(sr_val), "-ac", "1", temp_audio], timeout=_get_dynamic_timeout(video_path))

            # --- CHUNK-BASED: Analyzing the entire audio piece by piece without loading it into RAM ---
            frame_length = 2048
            hop_length = 512
            block_length = 256  # ~6 seconds/block

            all_rms_blocks = []
            total_samples = 0

            stream = librosa.stream(
                temp_audio,
                block_length=block_length,
                frame_length=frame_length,
                hop_length=hop_length
            )
            for y_block in stream:
                total_samples += len(y_block)
                rms_block = librosa.feature.rms(
                    y=y_block,
                    frame_length=frame_length,
                    hop_length=hop_length,
                    center=False
                )[0]
                all_rms_blocks.append(rms_block)

            if not all_rms_blocks:
                _logger.error("Ses analizi hatası: Videoda ses bloğu bulunamadı (sessiz veya bozuk video).")
                raise ValueError("Videonun ses kanalı okunamadı veya video tamamen sessiz. Lütfen ses içeren geçerli bir MP4 yükleyin.")

            rms = np.concatenate(all_rms_blocks)
            del all_rms_blocks
            gc.collect()

            duration = total_samples / sr_val
            rms_list = [round(float(v), 4) for v in rms]
            peak_times = [round(i * (duration / len(rms)), 1) for i in range(1, len(rms)) if rms[i] - rms[i - 1] > 0.18]
            gaps = [peak_times[i + 1] - peak_times[i] for i in range(len(peak_times) - 1)] if len(peak_times) > 1 else []
            max_gap = max(gaps) if gaps else (duration - (peak_times[0] if peak_times else 0))
            viral_score = min(10.0, len(peak_times) ** 1.6 / 12) if len(peak_times) > 5 else 0.0
            tech_score = 9.5 if len(peak_times) > 18 else (7.5 if len(peak_times) > 10 else 5.0)

            return {
                "tech_score": tech_score, "peaks": len(peak_times), "peak_times": peak_times,
                "max_gap": round(max_gap, 1), "viral_score": round(viral_score, 1),
                "duration": round(duration, 1), "rms_data": rms_list
            }
        except Exception as e:
            _logger.error(f"Ses analizi hatası: {e}")
            raise ValueError(f"Videonun ses kanalı okunamadı veya dosya bozuk. Lütfen ses içeren geçerli bir MP4 yükleyin. (Detay: {str(e)[:80]})")
        finally:
            if os.path.exists(temp_audio):
                try:
                    os.remove(temp_audio)
                except Exception as e:
                    _logger.warning(f"Hata [analyze_video_tech temp clean]: {e}")

    @staticmethod
    def find_viral_segments(tech: Dict, visual_tempo: list = None,
                            scene_changes: Dict = None) -> list:
        """
        Multimodal viral segment tespiti:
        - Ses (RMS) patlamaları: %40
        - Sahne değişim yoğunluğu: %30
        - Hareket yoğunluğu: %30
        """
        if tech["peaks"] < 3:
            return []
        duration = tech["duration"]
        rms_data = tech.get("rms_data", [])
        if not rms_data:
            return []

        rms_array = np.array(rms_data)
        rms_max = float(np.max(rms_array)) if len(rms_array) > 0 else 1.0
        time_per_frame = duration / len(rms_data)

        # Scene change and motion data
        cut_times = scene_changes.get("cut_times", []) if scene_changes else []
        motion_vals = visual_tempo if visual_tempo else []
        motion_max = max(motion_vals) if motion_vals else 1.0
        if motion_max == 0:
            motion_max = 1.0

        segments = []
        for peak_time in tech["peak_times"][:3]:
            peak_idx = min(int(peak_time / time_per_frame), len(rms_data) - 1)
            local_peak_val = float(rms_data[peak_idx])
            threshold = local_peak_val * 0.35

            start_idx = peak_idx
            while start_idx > 0 and rms_data[start_idx] >= threshold:
                start_idx -= 1

            start_sec = start_idx * time_per_frame

            end_idx = peak_idx
            while end_idx < len(rms_data) - 1 and rms_data[end_idx] >= threshold:
                end_idx += 1

            end_sec = end_idx * time_per_frame + 2.0

            actual_duration = end_sec - start_sec
            if actual_duration < 6.0:
                end_sec = min(duration, start_sec + 6.0)
            elif actual_duration > 45.0:
                end_sec = start_sec + 45.0

            end_sec = min(duration, end_sec)
            start_sec = round(start_sec, 1)
            end_sec = round(end_sec, 1)

            # ── Multimodal Excitement Coefficient ──
            # 1. Audio score (normalized)
            rms_norm = (local_peak_val / rms_max) if rms_max > 0 else 0.0

            # 2. Scene change intensity (number of cuts in this window)
            cuts_in_window = sum(
                1 for ct in cut_times if start_sec <= ct <= end_sec
            )
            seg_dur = max(1.0, end_sec - start_sec)
            cut_density = cuts_in_window / (seg_dur / 10.0)  # cuts per 10sec
            cut_density_norm = min(1.0, cut_density / 5.0)

            # 3. Motion intensity (average motion in this window)
            motion_norm = 0.0
            if motion_vals:
                m_start = int(start_sec)
                m_end = min(int(end_sec) + 1, len(motion_vals))
                if m_start < len(motion_vals):
                    window_motion = motion_vals[m_start:m_end]
                    if window_motion:
                        motion_norm = (sum(window_motion) / len(window_motion)) / motion_max

            excitement = (rms_norm * 0.4) + (cut_density_norm * 0.3) + (motion_norm * 0.3)
            excitement_score = round(min(10.0, excitement * 10), 1)

            segments.append({
                "start_sec": start_sec, "end_sec": end_sec,
                "suggested_duration": round(end_sec - start_sec, 1),
                "score": round((local_peak_val / rms_max) * 100, 1),
                "excitement_score": excitement_score,
                "audio_intensity": round(rms_norm * 10, 1),
                "cut_density": round(cut_density_norm * 10, 1),
                "motion_intensity": round(motion_norm * 10, 1)
            })
        return segments

    @staticmethod
    async def get_channel_averages(channel_id: int) -> Dict:
        db = await get_async_db()
        try:
            async with db.execute('''SELECT AVG(overall_score), AVG(retention_score), AVG(tech_score), AVG(seo_score), AVG(thumb_score) FROM analyses WHERE channel_id = ?''', (channel_id,)) as cursor:
                row = await cursor.fetchone()
        finally:
            await db.close()

        def safe_round(val):
            return round(float(val), 1) if val is not None else 0.0

        return {
            "avg_overall": safe_round(row[0] if row else None),
            "avg_retention": safe_round(row[1] if row else None),
            "avg_tech": safe_round(row[2] if row else None),
            "avg_seo": safe_round(row[3] if row else None),
            "avg_thumb": safe_round(row[4] if row else None)
        }
