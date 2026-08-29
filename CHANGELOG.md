# Changelog

All notable changes to **YouTube Analyse Pro SaaS Edition** will be documented in this file.

## [v6.4.0] - Optional Rival Comparison

A finished video analysis is no longer thrown away because YouTube search could not supply a fair rival. Comparison appears only when a candidate is actually comparable.

### 🛡️ Analysis always completes
- **Rival lookup is optional:** `/analyze` no longer fails with "no rival found". Scores, coach text, and the PDF are saved either way; `competitor_data` is `null` plus a `competitor_status` (`ok`, `manual`, `no_confident_match`, `lookup_failed`, `manual_url_failed`).
- **Screen & PDF:** When there is no confident match, the VS card and the head-to-head PDF block are replaced with a short note (TR/EN/ES). The creator's SEO check-up, thumbnail emotion table, and viral segments still render.
- **History:** Reopening a saved analysis no longer treats the stored data bag as a rival when none was found.

### 🎯 Comparable rivals only
- Candidates are **scored** (topic overlap, format/duration, language, popularity as a tie-break) instead of taking the first shared keyword.
- A **minimum score** must be cleared; an off-niche trending video is never forced into VS.
- Search queries are **deterministic** (niche first, then distinctive title words). A broader second search runs only if the first pass finds nothing above the threshold.
- Shorts analyses prefer short rivals; long-form analyses prefer similar length. A paste-in URL still bypasses the niche gate (the creator chose it).

### ✅ Tests
- `tests/test_optional_competitor.py` covers lookup statuses, scoring, persistence, PDF skip of head-to-head only, and the history UI contract.

## [v6.3.0] - Advisory Tone

Every recommendation shown to the creator — analysis screen, PDF report, AI coach, chat, Chrome extension badges, and prefilled coach questions — is now phrased as a suggestion, never as an order and never as a promised result.

### 🗣️ Product copy
- **PDF & UI strings (`translations.xlsx`):** Imperative labels (`EMRİ` / `ORDER`), obligation mood (`-malısın`, `You should`), urgency (`acil`, `derhal`), and numeric promises (`CTR %40 artar`) rewritten as options (`bunu deneyebilirsin`, `you could try`, `podrías probar`).
- **On-screen action list (`static/App.js`):** Rule-based feedback lines no longer command a specific edit; they offer it.
- **Offline coach fallback (`analysis_engine.py`):** When Groq is unavailable, the static sentences stay in the same advisory mood (TR/EN/ES).
- **Chrome extension DNA badges:** `Yüksek izlenme garantisi` / `High view guarantee` → potential wording; `GELİŞTİRİLMELİ` / `NEEDS IMPROVEMENT (Fix shortcomings)` → `GELİŞTİRİLEBİLİR` / `ROOM TO IMPROVE`.
- **Quick questions:** `Thumbnail nasıl olmalı?` → `Thumbnail nasıl olabilir?` (and matching EN/ES).

### 🤖 AI prompts
- **Shared tone rule** in `ai_service.py` (`ADVISORY_TONE_RULE` / `ADVISORY_TONE_RULE_CREATIVE`) injected into coach, chat, clone, debate, guerilla, script doctor, and success-formula prompts.
- Creative assets (titles, hooks, thumbnails) stay punchy; surrounding guidance is still a suggestion, not a command.

### ✅ Tests
- Advisory-tone pytest suite under `tests/` (PDF/UI copy, prompts, extension, report email).
- `pytest.ini` limits collection to `tests/` so manual probe scripts such as `test_prophet.py` are not treated as tests.

## [v6.2.0] - Content Ideas & UX Refinement

### 📺 Content Ideas (Always-On Prophet Picks)
- **Persistent Visibility:** The "Prophet's Pick" feature has been rebranded as "İçerik Fikirleri" (Content Ideas) and is now dynamically loaded in every extension state, including directly on YouTube video pages above the current video card.
- **DNA Integration:** Added the 🧬 DNA analysis button directly to the Content Ideas cards, completing the 5-minute clone-and-record workflow.
- **Skeleton Loading:** Implemented a modern CSS shimmer skeleton loader while the Groq AI fetches custom trending niche queries in the background.

### 🧩 UX & Architecture Upgrades
- **Full-Screen Extension:** Migrated from a constrained Chrome popup (650px) to a responsive, full-screen new tab experience (`100vh`) for better readability and a premium feel.
- **Competitor Niche Matching:** Refined the competitor finding algorithm in `competitor.py` to strongly pair the user's category with title keywords (e.g., "AI" + "clone"), significantly reducing irrelevant cross-niche matches.
- **SEO Check-up Context:** Added explicit multi-language explanations (TR/EN/ES) when the system flags irrelevant tags/hashtags, helping creators understand *why* removing them improves algorithm performance.

## [v6.1.0] - Rival DNA Hijacker & Script Doctor
- **`POST /api/extension/guerilla_strategy`:** Analyzes rival channel DNA scores to generate a user-specific "Guerilla Strategy" report. Contains the competitor's strongest weapon, weakness, and a 3-step action plan.
- **`GuerillaStrategyRequest` Model:** Contains `rival_video_id`, `rival_channel`, `dna_data`, `target_channel_id` (multi-channel support), and `lang` (i18n) fields.
- **Dynamic Profiling:** User's `content_type` and `purpose` are dynamically fetched from the database and injected into the Groq prompt.

### ✍️ Script Doctor (NEW)
- **`POST /api/extension/generate_hook_script`:** References competitor/reference video DNA data and transcript to generate a viral hook + 3 different script drafts (Aggressive/Curiosity/Shock) tailored to the user's channel.
- **`HookScriptRequest` Model:** Contains `video_id`, `video_url`, `dna_data`, `target_channel_id`, and `lang` fields.
- **Transcript Fallback:** Performs estimated analysis from title and DNA scores if subtitles are missing—never returns empty.

### 🔧 Technical Fixes & Architecture
- **Dynamic Architecture:** Removed hardcoded channel name references in `clone_video`, `clone_debate`, and all related Groq prompts. Everything is dynamically fetched from the database's `content_type` and `purpose` fields.
- **Multi-Channel Support:** Added `target_channel_id` to `CloneVideoRequest` model. All extension endpoints (`clone_video`, `clone_debate`, `guerilla_strategy`, `generate_hook_script`) now correctly target the user's selected channel.
- **`is_favorite` Migration:** Added SQLite migration to `init_db` in `app/database/db.py` to add `is_favorite INTEGER DEFAULT 0` column to the `analyses` table.
- **Anti-Hallucination Shield:** Dynamically resolved system prompt for chat endpoint (`/api/chat`) based on user's dynamic `content_type`.

## [v6.0.1] - Smart Pick & i18n Update (UX Overhaul)

### 🌐 Internationalization & UI Overhaul
- **Full i18n Support:** Added comprehensive Multi-Language support (EN/TR) to the Chrome Extension with dynamic toggling and localized tooltips.
- **Button Guide Localization:** The entire "Information Modal" (Button Guide) has been separated from static HTML and properly mapped to the i18n engine.
- **Icon & Branding Update:** Refreshed desktop shortcut and UI icons for a seamless neon aesthetic. Overrode aggressive Windows icon caches.
- **Syntax & Bug Squashing:** Completely resolved the string interpolation and quote escaping issues (`tier_mega_viral` syntax error) that froze the extension UI.

### 🔮 Smart Suggestion Engine (Prophet's Pick Evolved)
- **Smart Pick Popup:** "Prophet's Pick" has been upgraded to a non-intrusive "Smart Pick" toast/popup with dynamically translated CTA buttons (Clone, Debate, DNA).
- **Clickable Cards:** Made the entire Smart Pick card area clickable, opening the YouTube video in a new background tab without interfering with the action buttons.

### 🧬 Next-Gen DNA Scoring Engine
- **Weighted Success Formula:** DNA scoring respects the true science of virality: Hook (40%) and Tempo (40%) as core drivers, CTA (10%) and Emotion (10%) as support.
- **Synergy Bonus:** If a video scores >75 in both Hook and Tempo, the system grants a +20 Synergy Bonus.
- **Diminishing Returns (DR) Protection:** CTA and Emotion automatically receive a minimum of 50 credits to prevent unfair drag down on phenomenal hooks.
- **Dynamic Badges:** 4 new UI tiers for DNA scores: 👑 LEGENDARY, 🔥 VIRAL POTENTIAL, ✅ STRONG, ⚠️ NEEDS IMPROVEMENT.
- **Metadata Fallback:** Robust fallback mechanism to analyze Video Title, Tags, and Description if the transcript is missing, dynamically flagging the UI with an "Estimated Analysis".
- **Master Prompt Export:** Instantly generate a copy-pasteable "Master Prompt" matching the structural DNA of the analyzed viral video.

## [v2.0.0] - Enterprise Architecture & 1-Click Install

### 🏗️ Refactored (The Great Refactor)
- **Modular Service Layer:** Surgically decomposed the monolithic `server.pyw` (4,100+ lines) into clean, standalone modules under the `app/` package, adhering to SOLID principles and single-responsibility guidelines.
- **`app/database/db.py`:** Centralized async SQLite engine using Write-Ahead Logging (WAL) and automatic migration management.
- **`app/services/security.py`:** Encapsulated AES-128 Fernet encryption for API keys and PBKDF2 cryptography for secure user sessions.
- **`app/services/email_service.py`:** Extracted dynamic multilingual report and verification code email distribution logic.
- **`app/services/ai_service.py`:** Decoupled external API orchestrations for Groq (Llama-3.3-70B) and Google Gemini 2.0 Flash models.
- **`app/services/competitor.py`:** Modularized yt-dlp integrated competitor research and dynamic metrics computing algorithms.
- **`app/services/analysis_engine.py`:** Separated the core multimedia engines combining OpenCV, librosa audio tracking, and DeepFace vision models.

### 🚀 Added
- **`install.bat` (1-Click Installer):** Formulated an advanced Windows setup script that handles Python diagnostics, establishes an isolated `venv`, installs dependencies from `requirements.txt`, automatically downloads and configures FFmpeg binaries, and spawns a desktop launching shortcut.

---

### 👑 v5.5.0 — Elite Calibration Update
- **[Algorithm] Synergy & DR Protection:** Switched DNA scoring to a weighted model (40/40/10/10) with a +20 Synergy Bonus for high Hook/Tempo and a 50-credit minimum DR protection against weak CTAs.
- **[UI/UX] Dynamic DNA Badges:** Introduced 4 new gradient-styled badge tiers (Legendary, Viral Potential, Strong, Needs Improvement) based on the calculated DNA score.
- **[UI/UX] Info Guide Revamp:** Completely redesigned the Chrome Extension's Info panel with detailed explanations of the DNA scoring methodology, tier systems, and UI button mappings.
- **[Feature] Metadata Fallback:** Added a robust fallback mechanism that analyzes Video Title, Tags, and Description if the transcript is missing, dynamically flagging the UI with an "Estimated Analysis" amber warning.
- **[Prompt Engineering] Master Prompt Generator:** DNA results now automatically construct an advanced LLM script-writing prompt based on the exact anatomical triggers of the analyzed video.

---

### 🔮 v4.5.1 — Prophet's Pick Hotfix
- **[Prophet's Pick] AI Validation Filter:** Added a concurrent Groq AI validation layer for the top 10 highest-velocity videos to filter out generic/irrelevant trending videos before rendering.
- **[UI/UX] Clickable Cards:** Made the entire Prophet's Pick card area clickable, opening YouTube in a new background tab without interfering with Clone/Debate action buttons.
- **[Prompt Engineering] Strict Niche Enforcement:** Updated the AI prompt generating search queries to explicitly ban generic terms and enforce content-specific targeting.

---

### 🔮 v4.5.0 — Prophet's Pick Edition
- **[Prophet's Pick] Dynamic AI Queries:** Generates search queries via Groq tailored to the user's registered `content_type` and `purpose`.
- **[UI/UX] Matrix Glow Cards:** Injects a dynamic 3-card grid with neon Matrix glow when the user is not on a video tab.
- **[Educational UX] Context-Aware Info Modal:** The `ℹ️` button now teaches users whether they are in "Discovery", "Strategy", or "Intelligence" mode.
- **[Self-Filtering] Dynamic Channel Blacklist:** Automatically prevents the user's own videos from appearing in AI-generated trending suggestions.

---

### 🧠 v4.4.0 — Prophet Edition (Predictive Intelligence)
- **[AI] 5-Tier Spectrum:** 🔴 DEAD → 🔵 MEGA VIRAL analysis with dynamic AI persona.
- **[Algorithm] Velocity & Penetration:** View velocity and subscriber penetration ratio metrics.
- **[Features] Matrix Vision & Debate AI:** Neon outlier radar + multi-agent debate (Critic vs. Wizard vs. Referee).
- **[NLP] Chaos Metric:** 100% local algorithm to measure competitor rage and tempo.
- **[Fixes] Zero-Hallucination Armor:** Fixed "Happy Face" hallucination and Turkish/English 'B' suffix parsing bug.

---

### 🎯 v4.3.0 — The Precision Update
- **[Rabbit Hole] Dynamic Compatibility:** SQLite-integrated dynamic context fetching for niche compatibility.
- **[Extension] Robust JSON Parser:** Strips markdown and renders UI cards securely.
- **[Analytics] Chaos Metric UI:** Added human-readable explanation for the 10-point mathematical calculation.

---

### 🌪️ v4.2.0 — The Chaos & Debate Update
- **[AI Debate] A/B Test Simulator:** AI Persona debate engine with Referee evaluation.
- **[DB] SQLite WAL Mode:** Write-Ahead Logging for concurrent read performance.
- **[Crypto] Fail-Fast:** CryptoManager throws HTTP 500 on corrupted keys.
- **[Scraping] yt-dlp Backoff:** Exponential backoff against HTTP 429 bans.

---

### 🔒 v4.1.0 — Security & Logic Hardening
- **[Security] Google OAuth XSS Shield:** Serialized OAuth callbacks with `json.dumps`.
- **[Logic] Groq API Decryption Fix:** Added `CryptoManager.decrypt` to all AI endpoints.
- **[Math] Shorts Scoring Fix:** Realigned Shorts scoring weights to sum correctly to `1.00`.
- **[Stability] Transcript NameError Shield:** Pre-initialized `last_api_error` to prevent NameErrors.

---

### 🌟 v4.0.0 — SaaS Edition
- **SaaS Architecture:** Multi-user support, authentication, and secure localized credential storage.
- **Advanced Computer Vision:** Multi-threaded scene transition mapping and OpenCV threshold computing.

---

*(Earlier version histories can be found within the repository commit history.)*
