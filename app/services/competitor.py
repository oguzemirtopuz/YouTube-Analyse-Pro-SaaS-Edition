"""
app/services/competitor.py
───────────────────────────
Rakip analiz servisi — server.pyw'dan ayrıştırıldı (FAZ 2.2 Refactor).

İçerik:
  • extract_core_keywords  : Metin temizleme & anahtar kelime çıkarımı
  • compute_kill_switch    : İki video başlığı arasında konu benzerliği kontrolü
  • CompetitorAnalyzer     : yt-dlp üzerinden rakip video verisi çekme sınıfı
"""

import re
import traceback
import logging
from datetime import datetime

# yt-dlp optional
try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False

_logger = logging.getLogger("yt_analiz.competitor")


# ─── extract_core_keywords ────────────────────────── ──────────────────────────

def extract_core_keywords(text_str):
    if not text_str:
        return set()
    text_str = str(text_str).lower().replace("'", " ").replace('"', ' ').replace('-', ' ')
    words = set(re.findall(r'\b\w+\b', text_str))
    stop_words = {
        # Turkish
        've', 'ile', 'için', 'bir', 'çok', 'nasıl', 'neden', 'gibi', 'ama', 'bunu', 'böyle',
        'olan', 'olarak', 'kadar', 'sonra', 'önce', 'video', 'oyun', 'yeni', 'bölüm',
        'türkçe', 'izle', 'abone', 'ol', 'görün', 'bu', 'ben', 'sen', 'biz', 'siz', 'onlar',
        'ise', 'da', 'de', 'ki', 'mi', 'mu', 'mı', 'mü', 'ne', 'daha',
        # English
        'the', 'and', 'for', 'with', 'that', 'this', 'are', 'was', 'how', 'why',
        'what', 'when', 'who', 'from', 'have', 'has', 'had', 'not', 'but', 'they',
        'you', 'your', 'its', 'our', 'can', 'will', 'just', 'into', 'also', 'about',
        # spanish
        'que', 'con', 'para', 'por', 'una', 'uno', 'los', 'las', 'del', 'sus',
        'como', 'pero', 'est', 'son', 'han', 'hay', 'todo', 'este', 'esta', 'eso',
        'ese', 'ella', 'ellos', 'nos', 'muy', 'mas', 'sin', 'cuando', 'donde',
        'quien', 'porque', 'desde', 'hasta', 'entre', 'sobre', 'solo',
    }
    return {w for w in words if len(w) > 2 and w not in stop_words}


# ─── compute_kill_switch ────────────────────────── ───────────────────────────

def compute_kill_switch(user_title: str, comp_title: str) -> bool:
    user_kw = extract_core_keywords(user_title)
    comp_kw = extract_core_keywords(comp_title)
    if not user_kw or not comp_kw:
        return False
    for uk in user_kw:
        for ck in comp_kw:
            if uk in ck or ck in uk:
                return False
    return True


# ─── CompetitorAnalyzer ─────────────────────────── ────────────────────────────

class CompetitorAnalyzer:

    @staticmethod
    def get_competitor(category: str, tags: str, manual_url: str = "", channel_name: str = "", user_title: str = ""):
        fallback_data = {
            'title': f"{category.split()[0] if category else 'Viral'} Konseptli Video",
            'channel': 'Sektör Lideri (Otomatik)',
            'views': 345000,
            'tags': ['viral', 'trend', 'nasıl yapılır', 'yeni', category.split()[0] if category else 'video'],
            'hashtags': ['viral', 'trend'],
            'is_manual': False,
            'likes': 15000,
            'comments': 1200,
            'upload_date': datetime.now().strftime('%Y%m%d'),
            'is_fake': True
        }
        if not YT_DLP_AVAILABLE:
            return fallback_data
        ydl_opts = {'quiet': True, 'extract_flat': False, 'skip_download': True, 'max_downloads': 1, 'noplaylist': True}
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                if manual_url and ("youtube.com" in manual_url or "youtu.be" in manual_url):
                    info = ydl.extract_info(manual_url, download=False)
                    comp_desc = info.get('description', '')
                    c_hashes = [w.strip('#').lower() for w in str(comp_desc).split() if w.startswith('#')]
                    c_hashes = list(dict.fromkeys([h for h in c_hashes if h]))
                    return {
                        'title': info.get('title', 'Bilinmiyor'),
                        'channel': info.get('uploader', 'Rakip Kanal'),
                        'views': info.get('view_count', fallback_data['views']),
                        'tags': info.get('tags', fallback_data['tags'])[:15],
                        'hashtags': c_hashes[:10],
                        'is_manual': True,
                        'likes': info.get('like_count', 0),
                        'comments': info.get('comment_count', 0),
                        'upload_date': info.get('upload_date', fallback_data['upload_date']),
                        'is_fake': False
                    }
                else:
                    # ── Arama sorgusu: KATEGORİ (her zaman) + başlık keyword'leri ──
                    # Kategori kanalın niş'ini belirler (yapay zeka, oyun, yemek vs.)
                    # Başlık ek spesifiklik verir (minecraft, iskender vs.)
                    cat_keywords = extract_core_keywords(category) if category else set()
                    title_keywords = extract_core_keywords(user_title) if user_title else set()
                    tag_keywords = set()
                    if tags:
                        tag_keywords = extract_core_keywords(tags.replace(',', ' '))

                    # Niş filtresinde kullanılacak: kategori + başlık keyword'leri birlikte
                    all_user_keywords = cat_keywords | title_keywords

                    # Sorgu: önce kategori (niş), sonra başlıktan ek spesifik kelimeler
                    query_parts = []
                    if cat_keywords:
                        query_parts.extend(list(cat_keywords)[:3])
                    # Başlıktan kategori'de olmayan kelimeleri ekle (en fazla 3)
                    title_unique = title_keywords - cat_keywords
                    if title_unique:
                        query_parts.extend(list(title_unique)[:3])
                    # Etiketlerden de ekle (diğerlerinde olmayanları, en fazla 2)
                    remaining_tags = tag_keywords - cat_keywords - title_keywords
                    if remaining_tags:
                        query_parts.extend(list(remaining_tags)[:2])
                    # Hiçbir keyword yoksa ham kategori metnini kullan
                    if not query_parts and category:
                        query_parts = category.split()[:3]

                    search_query = " ".join(query_parts).strip()
                    if not search_query or len(search_query) < 3:
                        search_query = "YouTube trend"

                    _logger.debug(f"Rakip araması: sorgu = '{search_query}' (kategori: {category})")

                    # ytsearch10: daha geniş aday havuzu → niş uyumu filtresi uygula
                    info = ydl.extract_info(f"ytsearch10:{search_query}", download=False)
                    if 'entries' in info and len(info['entries']) > 0:
                        entry = None
                        own_channel_lower = channel_name.lower().strip() if channel_name else ""

                        for candidate in info['entries']:
                            if not candidate:
                                continue

                            # ── Kendi kanalı filtresi (isim + channel_id) ──
                            uploader = (candidate.get('uploader') or candidate.get('channel') or '').lower().strip()
                            candidate_channel_id = (candidate.get('channel_id') or candidate.get('uploader_id') or '').lower().strip()

                            # Kendi kanalını atla: isim karşılaştırması
                            if 'babaclutch' in uploader or (own_channel_lower and (
                                uploader == own_channel_lower or
                                own_channel_lower in uploader or
                                uploader in own_channel_lower
                            )):
                                _logger.debug(f"Rakip araması: kendi kanalı (Self-Comparison) atlandı → {uploader}")
                                continue

                            # ── Niş uyumu filtresi ──
                            # Adayın başlığı ile kullanıcının kategori+başlık keyword'leri
                            # arasında en az 1 ortak core keyword olmalı
                            # (minecraft↔minecraft eşleşir, minecraft↔valorant eşleşmez)
                            if all_user_keywords:
                                candidate_title = candidate.get('title', '')
                                candidate_kw = extract_core_keywords(candidate_title)
                                # Adayın etiketlerini de kontrol et (varsa)
                                candidate_tags = candidate.get('tags') or []
                                if candidate_tags:
                                    candidate_kw |= extract_core_keywords(' '.join(str(t) for t in candidate_tags))
                                # Tam eşleşme veya kısmi eşleşme (kelime içinde geçme)
                                has_niche_match = False
                                for uk in all_user_keywords:
                                    for ck in candidate_kw:
                                        if uk == ck or (len(uk) >= 4 and (uk in ck or ck in uk)):
                                            has_niche_match = True
                                            break
                                    if has_niche_match:
                                        break

                                if not has_niche_match:
                                    _logger.debug(
                                        f"Rakip araması: niş uyumsuzluğu atlandı → "
                                        f"'{candidate_title}' (kullanıcı kw: {all_user_keywords}, aday kw: {candidate_kw})"
                                    )
                                    continue

                            entry = candidate
                            break

                        if entry is None:
                            # Niş filtresi çok sıkıysa, filtresiz ilk uygun adayı al
                            _logger.warning("Rakip araması: niş uyumu bulunamadı, filtresiz ilk aday seçiliyor")
                            for candidate in info['entries']:
                                if not candidate:
                                    continue
                                uploader = (candidate.get('uploader') or candidate.get('channel') or '').lower().strip()
                                if 'babaclutch' in uploader or (own_channel_lower and (
                                    uploader == own_channel_lower or
                                    own_channel_lower in uploader or
                                    uploader in own_channel_lower
                                )):
                                    continue
                                entry = candidate
                                break

                        if entry is None:
                            raise ValueError("Henüz kıyaslanacak başka bir rakip bulunamadı")

                        comp_desc = entry.get('description', '')
                        c_hashes = [w.strip('#').lower() for w in str(comp_desc).split() if w.startswith('#')]
                        c_hashes = list(dict.fromkeys([h for h in c_hashes if h]))
                        return {
                            'title': entry.get('title', fallback_data['title']),
                            'channel': entry.get('uploader', fallback_data['channel']),
                            'views': entry.get('view_count', fallback_data['views']),
                            'tags': entry.get('tags', fallback_data['tags'])[:15],
                            'hashtags': c_hashes[:10],
                            'is_manual': False,
                            'likes': entry.get('like_count', 0),
                            'comments': entry.get('comment_count', 0),
                            'upload_date': entry.get('upload_date', fallback_data['upload_date']),
                            'is_fake': False
                        }
                    else:
                        raise ValueError("Henüz kıyaslanacak başka bir rakip bulunamadı")
        except ValueError as ve:
            # We simply forward the error to the upper layer by throwing a ValueError (without producing a fallback).
            raise ve
        except Exception as e:
            traceback.print_exc()
            raise ValueError(f"Rakip aramasında beklenmeyen bir hata oluştu: {str(e)}")


# ─── check_content_consistency ─────────────────────── ────────────────────────

def check_content_consistency(title: str, tags: str, description: str) -> dict:
    """
    Başlık, etiket ve açıklama arasındaki tutarlılığı kontrol eder.
    Sonuç: {'ok': bool, 'issues': list[str]}
    """
    issues = []
    title_kw = extract_core_keywords(title)

    # label control
    if not tags or not tags.strip():
        issues.append('no_tags')
    else:
        tag_text = tags.replace(',', ' ')
        tag_kw = extract_core_keywords(tag_text)
        if title_kw and tag_kw:
            overlap = sum(1 for tk in title_kw for tagk in tag_kw if tk in tagk or tagk in tk)
            if overlap == 0:
                issues.append('title_tags_mismatch')

    # Description control
    if not description or not description.strip():
        issues.append('no_desc')
    else:
        desc_kw = extract_core_keywords(description)
        if title_kw and desc_kw:
            overlap = sum(1 for tk in title_kw for dk in desc_kw if tk in dk or dk in tk)
            if overlap == 0:
                issues.append('title_desc_mismatch')

    return {'ok': len(issues) == 0, 'issues': issues}
