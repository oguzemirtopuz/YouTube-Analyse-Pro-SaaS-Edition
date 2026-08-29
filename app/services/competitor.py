"""
app/services/competitor.py
───────────────────────────
Rakip analiz servisi — server.pyw'dan ayrıştırıldı (FAZ 2.2 Refactor).

İçerik:
  • extract_core_keywords  : Metin temizleme & anahtar kelime çıkarımı
  • compute_kill_switch    : İki video başlığı arasında konu benzerliği kontrolü
  • CompetitorAnalyzer     : yt-dlp üzerinden rakip video verisi çekme sınıfı
"""

import math
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

_STOP_WORDS = frozenset({
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
    # Placeholder categories. 'Genel' is what a channel gets when its content type
    # was never filled in, and searching for it only adds noise to the query.
    'genel', 'general', 'diğer', 'diger', 'other', 'içerik', 'icerik', 'content',
})


# str.lower() turns the Turkish dotted capital 'İ' into 'i' plus a combining dot,
# which \w does not match: 'İskender' used to tokenize as ['i', 'skender'] and lose
# its first letter. Turkish titles are full of words starting with İ.
_TR_UPPER_I = str.maketrans({'İ': 'i', 'I': 'i'})


def tokenize_keywords(text_str) -> list:
    """
    Content words in the order they appear, de-duplicated.

    Order matters: both the search query and the scoring weights are derived from
    this list, and a search that returns different rivals for the same video on
    every run is impossible to reason about or support.
    """
    if not text_str:
        return []
    text_str = str(text_str).translate(_TR_UPPER_I).lower()
    text_str = text_str.replace("'", " ").replace('"', ' ').replace('-', ' ')
    out, seen = [], set()
    for w in re.findall(r'\b\w+\b', text_str):
        if len(w) > 2 and w not in _STOP_WORDS and w not in seen:
            seen.add(w)
            out.append(w)
    return out


def extract_core_keywords(text_str) -> set:
    return set(tokenize_keywords(text_str))


_FOLD_MAP = str.maketrans({'ı': 'i', 'ş': 's', 'ğ': 'g', 'ü': 'u', 'ö': 'o', 'ç': 'c',
                           'â': 'a', 'î': 'i', 'û': 'u'})


def _fold(token: str) -> str:
    """
    ASCII-folded form, used only for comparing tokens — never for display or search.
    YouTube titles mix 'İSKENDER', 'iskender' and 'Iskender' freely, and two videos
    on the same topic should not be judged unrelated over a diacritic.
    """
    return token.translate(_FOLD_MAP)


# ─── compute_kill_switch ────────────────────────── ───────────────────────────

def compute_kill_switch(user_title: str, comp_title: str) -> bool:
    user_kw = {_fold(k) for k in extract_core_keywords(user_title)}
    comp_kw = {_fold(k) for k in extract_core_keywords(comp_title)}
    if not user_kw or not comp_kw:
        return False
    for uk in user_kw:
        for ck in comp_kw:
            if uk in ck or ck in uk:
                return False
    return True


# ─── Lookup status codes ────────────────────────── ───────────────────────────
# get_competitor() reports what happened instead of raising. By the time it runs
# the video has already been analysed for minutes, so a missing rival must never
# be able to sink the whole analysis.

COMPETITOR_OK = "ok"                            # auto search found a comparable rival
COMPETITOR_MANUAL = "manual"                    # user supplied the URL
COMPETITOR_NO_MATCH = "no_confident_match"      # searched, nothing close enough
COMPETITOR_LOOKUP_FAILED = "lookup_failed"      # network / yt-dlp problem
COMPETITOR_MANUAL_FAILED = "manual_url_failed"  # user's URL could not be read

# Statuses that mean a real rival is attached to the analysis.
COMPETITOR_FOUND_STATUSES = (COMPETITOR_OK, COMPETITOR_MANUAL)


def _lookup_result(status: str, competitor=None, detail: str = "") -> dict:
    return {'status': status, 'competitor': competitor, 'detail': detail}


def _entry_to_competitor(entry: dict, is_manual: bool) -> dict:
    """Map a yt-dlp entry onto the competitor shape the report and UI expect."""
    hashes = [w.strip('#').lower() for w in str(entry.get('description') or '').split() if w.startswith('#')]
    hashes = list(dict.fromkeys([h for h in hashes if h]))
    return {
        'title': entry.get('title') or 'Bilinmiyor',
        'channel': entry.get('uploader') or entry.get('channel') or 'Rakip Kanal',
        'views': entry.get('view_count') or 0,
        'tags': (entry.get('tags') or [])[:15],
        'hashtags': hashes[:10],
        'is_manual': is_manual,
        'likes': entry.get('like_count') or 0,
        'comments': entry.get('comment_count') or 0,
        'upload_date': entry.get('upload_date') or datetime.now().strftime('%Y%m%d'),
        'is_fake': False,
    }


# ─── Candidate scoring ──────────────────────────── ───────────────────────────
# Every candidate is scored and the winner still has to clear a threshold. Taking
# "the first result that shares a word" is what used to produce comparisons against
# unrelated trending videos, and a wrong comparison is worse than none at all.

STRONG_TOKEN_MIN_LEN = 4    # 'ai' identifies nothing; 'minecraft' identifies a topic
SEARCH_RESULT_COUNT = 10
SHORTS_MAX_SEC = 90
MIN_TOTAL_SCORE = 45.0

# Where a keyword came from tells us how much it actually narrows the topic down:
# a word in the video's own title is far more telling than the channel's category.
_SOURCE_WEIGHTS = {'title': 1.0, 'tags': 0.7, 'category': 0.5}
_EXACT_POINTS = 30.0
_PARTIAL_POINTS = 15.0
_TOPIC_CAP = 70.0

_TR_CHARS = frozenset("ıİşŞğĞçÇöÖüÜ")
_TR_HINT_WORDS = frozenset({
    've', 'ile', 'için', 'bir', 'nasıl', 'bu', 'çok', 'ben', 'gün', 'yeni', 'bölüm', 'ilk',
})


def _looks_turkish(text):
    """True / False when there is a clear signal, None when it cannot be told."""
    s = str(text or '')
    if len(s.strip()) < 8:
        return None
    if _TR_CHARS & set(s):
        return True
    words = set(re.findall(r'\b\w+\b', s.lower()))
    if words & _TR_HINT_WORDS:
        return True
    return False if len(words) >= 3 else None


class _MatchContext:
    """Everything the scorer needs to know about the user's own video."""

    def __init__(self, category="", tags="", user_title="", channel_name="",
                 duration_sec=None, is_shorts=False):
        self.user_title = user_title or ""
        self.own_channel = (channel_name or "").lower().strip()
        self.duration_sec = float(duration_sec) if (duration_sec or 0) > 0 else None
        self.is_shorts = bool(is_shorts)

        self.title_tokens = tokenize_keywords(user_title)
        self.tag_tokens = tokenize_keywords((tags or "").replace(',', ' '))
        self.cat_tokens = tokenize_keywords(category)

        # First source wins, so a word that appears in both the title and the
        # category keeps the title's higher weight.
        self.weighted_tokens = {}
        for source, tokens in (('title', self.title_tokens),
                               ('tags', self.tag_tokens),
                               ('category', self.cat_tokens)):
            for tok in tokens:
                self.weighted_tokens.setdefault(tok, _SOURCE_WEIGHTS[source])

        self.wants_turkish = _looks_turkish(f"{user_title} {tags}")

    def search_queries(self) -> list:
        """
        The narrow query first, then a broader one used only if nothing clears the
        threshold. The broad pass costs another round trip, so it is worth spending
        only when the alternative is giving up on the comparison entirely.
        """
        niche = self.cat_tokens[:2]
        specific = [t for t in self.title_tokens if len(t) >= STRONG_TOKEN_MIN_LEN]
        extra_tags = [t for t in self.tag_tokens
                      if t not in self.title_tokens and t not in self.cat_tokens]

        candidates = [
            niche + specific[:3],
            niche + specific[:1] + extra_tags[:2],
            niche or specific[:2],
        ]

        queries = []
        for parts in candidates:
            q = " ".join(dict.fromkeys(parts)).strip()
            if len(q) >= 3 and q not in queries:
                queries.append(q)
        return queries or ["YouTube trend"]


def _score_candidate(entry: dict, ctx: _MatchContext):
    """
    Returns (score, reason). A score of None means the candidate is disqualified;
    `reason` always explains the outcome so the logs stay readable during support.
    """
    title = str(entry.get('title') or '')
    if not title:
        return None, "no title"

    uploader = (entry.get('uploader') or entry.get('channel') or '').lower().strip()
    if ctx.own_channel and uploader and (
            uploader == ctx.own_channel
            or ctx.own_channel in uploader
            or uploader in ctx.own_channel):
        return None, f"own channel ({uploader})"

    cand_tokens = set(tokenize_keywords(title))
    cand_tokens |= set(tokenize_keywords(' '.join(str(t) for t in (entry.get('tags') or []))))
    searchable = {_fold(t) for t in cand_tokens}

    topic, hits = 0.0, []
    for tok, weight in ctx.weighted_tokens.items():
        folded = _fold(tok)
        if folded in searchable:
            topic += _EXACT_POINTS * weight
            hits.append(tok)
        elif len(folded) >= STRONG_TOKEN_MIN_LEN and any(
                folded in c or (len(c) >= STRONG_TOKEN_MIN_LEN and c in folded)
                for c in searchable):
            topic += _PARTIAL_POINTS * weight
            hits.append(tok)
    topic = min(topic, _TOPIC_CAP)

    if not hits:
        return None, "no topic overlap"

    # One short word in common ('100', 'pro') is coincidence, not a shared topic.
    if not any(len(t) >= STRONG_TOKEN_MIN_LEN for t in hits) and len(hits) < 2:
        return None, f"only one short keyword in common ({hits[0]})"

    # The report uses compute_kill_switch to warn "these topics do not match".
    # Applying it here means we never pick a rival we would then warn about.
    if compute_kill_switch(ctx.user_title, title):
        return None, "titles share no topic (kill switch)"

    # ── Format: a 40-second clip is not a fair rival for a 20-minute video ──
    raw_dur = entry.get('duration')
    cand_dur = float(raw_dur) if isinstance(raw_dur, (int, float)) and raw_dur > 0 else None
    fmt = 0.0
    if cand_dur is not None:
        if ctx.is_shorts:
            if cand_dur <= SHORTS_MAX_SEC:
                fmt += 15.0
            elif cand_dur > SHORTS_MAX_SEC * 3:
                return None, f"long-form ({int(cand_dur)}s) against a Shorts analysis"
            else:
                fmt -= 20.0
        elif cand_dur <= SHORTS_MAX_SEC:
            fmt -= 25.0
        if ctx.duration_sec:
            fmt += 15.0 * (min(ctx.duration_sec, cand_dur) / max(ctx.duration_sec, cand_dur))

    # ── Language: an English video is a poor rival for a Turkish one ──
    lang = 0.0
    cand_turkish = _looks_turkish(title)
    if ctx.wants_turkish is not None and cand_turkish is not None:
        lang = 8.0 if ctx.wants_turkish == cand_turkish else -8.0

    # ── Popularity: a tie-break between equally relevant videos, nothing more ──
    pop = min(7.0, math.log10((entry.get('view_count') or 0) + 1))

    total = topic + fmt + lang + pop
    return total, f"topic={topic:.0f} format={fmt:+.0f} lang={lang:+.0f} pop={pop:+.1f} hits={hits}"


def _pick_best(pool: list, ctx: _MatchContext):
    """Highest-scoring candidate that clears MIN_TOTAL_SCORE, or None."""
    scored = []
    for entry in pool:
        score, reason = _score_candidate(entry, ctx)
        title = str(entry.get('title') or '?')
        if score is None:
            _logger.debug(f"Rakip araması: aday elendi → '{title}': {reason}")
        else:
            scored.append((score, title, entry, reason))

    if not scored:
        return None

    # Title is the tie-break so an unchanged result set always yields the same pick.
    scored.sort(key=lambda x: (-x[0], x[1]))
    score, title, entry, reason = scored[0]
    if score < MIN_TOTAL_SCORE:
        _logger.info(
            f"Rakip araması: en iyi aday eşiğin altında ({score:.0f} < {MIN_TOTAL_SCORE:.0f}) "
            f"→ '{title}': {reason}")
        return None

    _logger.info(f"Rakip araması: seçilen aday {score:.0f} puan → '{title}': {reason}")
    return entry


# ─── CompetitorAnalyzer ─────────────────────────── ────────────────────────────

class CompetitorAnalyzer:

    @staticmethod
    def get_competitor(category: str, tags: str, manual_url: str = "", channel_name: str = "",
                       user_title: str = "", duration_sec=None, is_shorts: bool = False) -> dict:
        """
        Look for a video worth comparing against.

        Returns {'status': <code>, 'competitor': dict|None, 'detail': str} and never
        raises. Candidates are scored on topic overlap, format and language, and the
        best one still has to clear MIN_TOTAL_SCORE: an unrelated trending video is
        worse than no comparison at all.
        """
        if not YT_DLP_AVAILABLE:
            return _lookup_result(COMPETITOR_LOOKUP_FAILED, detail="yt-dlp is not installed")

        ydl_opts = {'quiet': True, 'extract_flat': False, 'skip_download': True, 'max_downloads': 1, 'noplaylist': True}

        # ── Kullanıcının verdiği link: bilinçli bir seçim, niş filtresine takılmaz ──
        if manual_url and ("youtube.com" in manual_url or "youtu.be" in manual_url):
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(manual_url, download=False)
                return _lookup_result(COMPETITOR_MANUAL, competitor=_entry_to_competitor(info, is_manual=True))
            except Exception as e:
                _logger.warning(f"Rakip araması: kullanıcının verdiği link okunamadı ({manual_url}): {e}")
                return _lookup_result(COMPETITOR_MANUAL_FAILED, detail=str(e))

        ctx = _MatchContext(category=category, tags=tags, user_title=user_title,
                            channel_name=channel_name, duration_sec=duration_sec,
                            is_shorts=is_shorts)
        queries = ctx.search_queries()
        pool, seen, tried = [], set(), []

        for attempt, query in enumerate(queries, start=1):
            _logger.debug(f"Rakip araması: {attempt}. sorgu = '{query}' (kategori: {category})")
            tried.append(query)
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(f"ytsearch{SEARCH_RESULT_COUNT}:{query}", download=False)
            except Exception as e:
                # Losing the first search means we learned nothing; losing a later,
                # broader one still leaves the candidates we already collected.
                _logger.warning(f"Rakip araması: '{query}' sorgusu başarısız: {e}")
                _logger.debug(traceback.format_exc())
                if attempt == 1:
                    return _lookup_result(COMPETITOR_LOOKUP_FAILED, detail=str(e))
                break

            for candidate in (info or {}).get('entries') or []:
                if not candidate:
                    continue
                key = candidate.get('id') or candidate.get('url') or candidate.get('title')
                if key in seen:
                    continue
                seen.add(key)
                pool.append(candidate)

            best = _pick_best(pool, ctx)
            if best is not None:
                return _lookup_result(COMPETITOR_OK, competitor=_entry_to_competitor(best, is_manual=False))

        # Nothing cleared the threshold. Rather than fall back on an unrelated
        # trending video, leave the comparison out and say so.
        _logger.info(
            f"Rakip araması: {len(pool)} aday incelendi, kıyaslanabilir video yok "
            f"(sorgular: {tried})")
        return _lookup_result(
            COMPETITOR_NO_MATCH,
            detail=f"no candidate above score {MIN_TOTAL_SCORE:.0f} from {len(pool)} results "
                   f"(queries: {', '.join(tried)})")


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
