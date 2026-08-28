"""
app/services/ai_service.py
───────────────────────────
Yapay Zeka servisi — server.pyw'dan ayrıştırıldı (FAZ 2.1 Refactor).

İçerik:
  • get_groq_api_key          : DB'den Groq API anahtarını çeker (async)
  • generate_ai_game_feedback : Groq (Llama-3.3-70B) ile YouTube koç tavsiyesi üretir
  • analyze_image_with_gemini : Gemini 2.0 Flash ile görsel / PDF analizi yapar
"""

import logging
import requests
import asyncio

from app.database.db import get_async_db
from app.services.security import CryptoManager, CryptoDecryptionError

_logger = logging.getLogger("yt_analiz.ai")


# ─── Advisory tone ─────────────────────────── ────────────────────────────
# Single source of truth for the wording rule every user-facing prompt injects.
# The examples use %X rather than a real number so the rule itself can never be
# mistaken for a growth promise by the tone tests.

ADVISORY_TONE_RULE = (
    "ADVISORY TONE (MANDATORY): Every recommendation you write must read as an option the "
    "creator may choose, never as an order and never as a promised result.\n"
    "- Phrase advice as a suggestion: 'bunu yapabilirsin', 'sunu deneyebilirsin', "
    "'dusunebilirsin', 'you could try', 'you may want to', 'podrias probar'.\n"
    "- NEVER use commands or obligations: 'yap', 'ekle', 'sil', 'yapmalisin', 'zorundasin', "
    "'acilen', 'derhal', 'do this', 'you must', 'you should', 'debes'.\n"
    "- NEVER promise a numeric outcome such as 'CTR %X artar', 'izlenmen X kat artar' or "
    "'this will increase views by X%'. You MAY state measured facts from the supplied data "
    "(for example 'retention drops at second 12'), but describe the effect of a change only "
    "as a possibility: 'artirmaya yardimci olabilir', 'may help', 'puede ayudar'.\n"
    "- Stay concrete: keep giving the exact timestamp, colour, wording or scene. "
    "Specific but optional — offer it, do not command it."
)

# For endpoints whose payload is creative material (titles, hooks, thumbnail copy)
# rather than counsel: the asset itself stays punchy, the guidance around it does not.
ADVISORY_TONE_RULE_CREATIVE = (
    "ADVISORY TONE (MANDATORY): Titles, hooks and thumbnail descriptions are creative assets — "
    "keep those punchy and bold. But every sentence that tells the creator what to DO "
    "(analysis, warnings, tempo notes, tactics, summaries) must read as a suggestion "
    "('bunu deneyebilirsin', 'you could try', 'podrias probar'), never as an order "
    "('bunu yap', 'you must', 'derhal') and never as a promised number "
    "('CTR %X artar', 'views will double')."
)


# ─── Groq API key ──────────────────────────── ────────────────────────────

async def get_groq_api_key() -> str:
    """DB'den Groq API anahtarını çeker (async)."""
    try:
        db = await get_async_db()
        try:
            async with db.execute("SELECT value FROM app_settings WHERE key='groq_api_key'") as cursor:
                row = await cursor.fetchone()
            return CryptoManager.decrypt(row[0]) if row and row[0] else ""
        finally:
            await db.close()
    except CryptoDecryptionError:
        raise
    except Exception as e:
        _logger.error(f"Hata [get_groq_api_key]: {str(e)}", exc_info=True)
        return ""


# ─── generate_ai_game_feedback ─────────────────────── ────────────────────────

async def generate_ai_game_feedback(c_type: str, c_aud: str, c_purp: str, tech_score: float,
                               retention_score: float, peaks: int, lang: str,
                               visual_insights: str = "") -> str:
    """
    Kanal amacına ve türüne göre Groq'a
    özel YouTube koç tavsiyesi ürettirir.
    visual_insights: Thumbnail ve sahne analiz verileri (Aşama 3).
    Başarısız olursa boş string döner → caller fallback uygular.
    """
    api_key = await get_groq_api_key()
    if not api_key:
        return ""

    if tech_score < 7.5:
        perf = (f"tempo düşük ({tech_score}/10), sadece {peaks} pik var" if lang == "tr"
                else f"el tempo es bajo ({tech_score}/10), solo {peaks} picos" if lang == "es"
                else f"tempo is low ({tech_score}/10), only {peaks} peaks")
    elif retention_score < 6.0:
        perf = (f"tempo iyi ama izleyici erken çıkıyor (retention {retention_score}/10)" if lang == "tr"
                else f"el tempo es bueno pero los espectadores se van pronto (retención {retention_score}/10)" if lang == "es"
                else f"tempo is good but viewers leave early (retention {retention_score}/10)")
    else:
        perf = (f"hem tempo hem retention iyi ({tech_score}/10, {retention_score}/10)" if lang == "tr"
                else f"tanto el tempo como la retención son buenos ({tech_score}/10, {retention_score}/10)" if lang == "es"
                else f"both tempo and retention are good ({tech_score}/10, {retention_score}/10)")

    lang_instr = {"tr": "Türkçe yaz", "es": "Escribe en Español"}.get(lang, "Write in English")

    # Identify thumbnail truth — AI should never produce false facial information
    thumb_face_fact = ""
    if visual_insights:
        if "No face detected" in visual_insights or "face detected" not in visual_insights.lower():
            thumb_face_fact = (
                "ABSOLUTE THUMBNAIL FACT: The thumbnail analysis confirmed NO HUMAN FACE was detected. "
                "You MUST NOT mention any face, emotion, or expression about the thumbnail. "
                "Do NOT say things like 'mutlu yüz', 'yüz tespiti', 'emotion detected'. "
                "If you mention the thumbnail, only reference its colors, contrast, or text space. "
            )
        else:
            thumb_face_fact = (
                "THUMBNAIL FACE FACT: A face WAS detected in the thumbnail. "
                "You may reference the detected emotion and gaze from the Visual Insights data. "
            )

    visual_block = ""
    if visual_insights:
        visual_block = f"\n\nVisual Insights (FACTUAL DATA - DO NOT CONTRADICT):\n{visual_insights}\n"

    prompt = (
        f"You are a YouTube coach specialized in content strategy. "
        f"The creator makes videos about: '{c_type}'. "
        f"Channel Purpose: '{c_purp if c_purp else 'Entertainment'}'. "
        f"Target audience: '{c_aud if c_aud else 'viewers'}'. "
        f"Video performance: {perf}."
        f"{visual_block}\n\n"
        f"{thumb_face_fact}"
        f"{lang_instr}. "
        f"Write a SHORT, SPECIFIC coaching tip. "
        f"MEMORY & CONTEXT: If the user has high scores (e.g. 8.5+ in tech/retention/seo), start by congratulating them before giving advice. Do not just focus on weaknesses. "
        f"TAG PROTECTION: NEVER label the user's tags as 'irrelevant' or 'alakasız'. If tags are provided, acknowledge them as correct unless they clearly belong to a different game. "
        f"CRITICAL RULE: Use ONLY the provided '{c_type}' and '{c_purp}' data. "
        f"NO HALLUCINATION: NEVER make up information. If you do not know the answer to something, explicitly state 'I do not know' (veya 'Bilmiyorum'). NEVER give wrong information. "
        f"ANTI-GENERIC RULE: NEVER use generic advice like 'surprise them in the first 10 seconds' or 'ilk 10 saniyede şaşırt'. You MUST answer the 'HOW' question. Provide a highly specific, concrete scene or script. "
        f"CRITICAL THUMBNAIL RULE: If the Channel Type is 'Gaming' or 'Oyun', NEVER suggest adding real human faces to the thumbnail. Instead, suggest using glowing text, high-contrast game characters, or epic in-game vehicles. "
        f"IMPORTANT: DO NOT use the example phrase about 'happy face' and 'looking at camera'. It was a placeholder. Describe the actual visual energy of BabaClutch's gaming thumbnail instead. "
        f"Start with an emoji + 'ANALİZ PRO KOÇU: ' "
        f"(ES='ENTRENADOR PRO: ', EN='PRO COACH: '). "
        f"If visual insights are provided, reference them ONLY if they are factually confirmed (e.g., contrast ratio, color match - NOT face if no face was detected). "
        f"Focus on what editing or hook technique works best for THIS content's audience. "
        f"HOOK FORMULA: Always end your advice with an 'Uygulama Örneği' (Application Example). Be extremely concrete but keep it optional. Example: 'Uygulama Örneği: 00:01'de ekran sallantı efektiyle (camera shake) birlikte \"Bunu Beklemiyorduk!\" yazısını belirgin bir fontla ekrana getirebilirsin'. "
        f"\n\n{ADVISORY_TONE_RULE}\n"
    )


    try:
        loop = asyncio.get_running_loop()
        resp = await loop.run_in_executor(None, lambda: requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200,
                "temperature": 0.7
            },
            timeout=10
        ))
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        _logger.error(f"Hata [generate_ai_game_feedback]: {str(e)}", exc_info=True)
    return ""


# ─── analyze_image_with_gemini ─────────────────────── ────────────────────────

async def analyze_image_with_gemini(image_base64: str, mime_type: str) -> str:
    try:
        db = await get_async_db()
        try:
            async with db.execute("SELECT value FROM app_settings WHERE key='gemini_api_key'") as cursor:
                row = await cursor.fetchone()
        finally:
            await db.close()
        gemini_key = CryptoManager.decrypt(row[0]) if row and row[0] else ""
        # print(f"IS THERE A GEMINI KEY: {bool(gemini_key)}, mime: {mime_type}")
        if not gemini_key:
            return ""

        if mime_type == "application/pdf":
            prompt = (
                "This is a YouTube analytics report PDF. "
                "Extract ALL visible data: scores, metrics, retention rates, SEO scores, "
                "peak counts, competitor data, feedback texts, recommendations — everything. "
                "Present it as structured text so a YouTube coach can give advice based on it."
            )
        else:
            prompt = (
                "This is a YouTube analytics screenshot or related image. "
                "Extract ALL visible data EXACTLY as it appears: numbers, percentages, timestamps, "
                "retention graphs, view counts, dates, comparison data — everything you see. "
                "CRITICAL: DO NOT calculate, guess, or invent numbers. If it says '3:28', write exactly '3:28'. "
                "Present it as highly precise structured text."
            )

        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": mime_type, "data": image_base64}}
                ]
            }]
        }
        print(f"GEMINI ISTEK GÖNDERILIYOR...")
        loop = asyncio.get_running_loop()
        resp = await loop.run_in_executor(None, lambda: requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}",
            json=payload,
            timeout=20
        ))
        print(f"GEMINI YANIT: status={resp.status_code}")
        if resp.status_code == 200:
            result = resp.json()
            text = result["candidates"][0]["content"]["parts"][0]["text"]
            return f"User uploaded YouTube analytics data:\n{text}"
        else:
            print(f"GEMINI API HATA: {resp.status_code} - {resp.text}")
            if resp.status_code == 429:
                return "SİSTEM BİLGİSİ: Kullanıcı bir görsel yükledi ancak Gemini API (Google) anahtarının KOTASI DOLDU (Error 429). Lütfen kullanıcıya 'Google Gemini API kotanızın dolduğunu, bu nedenle resmi okuyamadığımı' kibarca bildir."
            return f"SİSTEM BİLGİSİ: Görsel okunurken Gemini API hatası oluştu: {resp.status_code}"
    except CryptoDecryptionError:
        raise
    except Exception as e:
        print(f"GEMINI HATA: {type(e).__name__}: {e}")
        return f"SİSTEM BİLGİSİ: Görsel okuma sistemi çöktü: {str(e)}"
