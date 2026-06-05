<div align="center">

  <img src="https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11"/>
  <img src="https://img.shields.io/badge/FastAPI-0.110-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/Chrome_Extension-Manifest_V3-4285F4?style=for-the-badge&logo=googlechrome&logoColor=white" alt="Chrome Extension"/>
  <img src="https://img.shields.io/badge/AI_Powered-Groq_%7C_Gemini-FF6B35?style=for-the-badge&logo=openai&logoColor=white" alt="AI Powered"/>
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="MIT License"/>

  <br/><br/>

  <h1>🚀 YouTube Analyse Pro</h1>
  <h3>The Ultimate AI-Powered YouTube Growth Ecosystem</h3>

  <p><em>Mathematically dissect videos · Reverse-engineer viral structures · Dominate the algorithm</em></p>

  <br/>

  [![Live Demo](https://img.shields.io/badge/🚀_Live_Demo-Visit_SaaS_Platform-00FF66?style=for-the-badge&logo=google-chrome&logoColor=white)](https://your-saas-url-here.com)
  &nbsp;
  [![Download](https://img.shields.io/badge/⬇️_Download-Latest_Release-0066FF?style=for-the-badge&logo=github&logoColor=white)](https://github.com/oguzemirtopuz/YouTube-Analyse-Pro-SaaS-Edition/releases)

  <br/>

  > **⚠️ Live Demo Notice:** Replace the Live Demo badge URL with your actual deployment address before publishing.

</div>

---

## 🎯 The Problem

Content creators and digital marketers often struggle to understand *why* a video goes viral, relying on guesswork rather than data-driven insights. Traditional analytics tools provide basic surface-level metrics (views, likes, comments) but fail to dissect the core psychological triggers, audio pacing, and visual momentum that actually retain audience attention and trigger the YouTube algorithm.

## 💡 The Solution & Value Proposition

**YouTube Analyse Pro** is an advanced **YouTube Growth Ecosystem** built to mathematically dissect videos, clone viral structures, and dominate competitor channels. Powered by state-of-the-art AI and computer vision, it analyzes scene cuts, audio tempo, and transcript psychology to reverse-engineer viral success — giving creators actionable, predictive intelligence and guerrilla marketing tactics to skyrocket channel growth and audience retention.

---

## ✨ Latest Release — v6.1.0 RIVAL DNA HIJACKER & SCRIPT DOCTOR

> [!IMPORTANT]
> **v6.1.0 - Rival DNA Hijacker & Script Doctor Update 🕵️✍️**
>
> **A. Rival DNA Hijacker (NEW):**
> * **`POST /api/extension/guerilla_strategy`:** Analyzes rival channel DNA scores to generate a user-specific "Guerilla Strategy" report. Contains the competitor's strongest weapon, weakness, and a 3-step action plan.
> * **`GuerillaStrategyRequest` Model:** Contains `rival_video_id`, `rival_channel`, `dna_data`, `target_channel_id` (multi-channel support), and `lang` (i18n) fields.
> * **Dynamic Profiling:** User's `content_type` and `purpose` are dynamically fetched from the database and injected into the Groq prompt.
>
> **B. Script Doctor (NEW):**
> * **`POST /api/extension/generate_hook_script`:** References competitor/reference video DNA data and transcript to generate a viral hook + 3 different script drafts (Aggressive/Curiosity/Shock) tailored to the user's channel.
> * **`HookScriptRequest` Model:** Contains `video_id`, `video_url`, `dna_data`, `target_channel_id`, and `lang` fields.
> * **Transcript Fallback:** Performs estimated analysis from title and DNA scores if subtitles are missing—never returns empty.
>
> **C. Technical Fixes & Architecture:**
> * **Dynamic Architecture:** Removed hardcoded channel name references in `clone_video`, `clone_debate`, and all related Groq prompts. Everything is dynamically fetched from the database's `content_type` and `purpose` fields.
> * **Multi-Channel Support:** Added `target_channel_id` to `CloneVideoRequest` model. All extension endpoints (`clone_video`, `clone_debate`, `guerilla_strategy`, `generate_hook_script`) now correctly target the user's selected channel.
> * **`is_favorite` Migration:** Added SQLite migration to `init_db` in `app/database/db.py` to add `is_favorite INTEGER DEFAULT 0` column to the `analyses` table.
> * **Anti-Hallucination Shield:** Dynamically resolved system prompt for chat endpoint (`/api/chat`) based on user's dynamic `content_type`.
---

## 🌟 Ecosystem Architecture

The project is split into two perfectly synced engines:

```
YouTube Analyse Pro
├── 🖥️  Desktop App (FastAPI + PyWebView)
│   ├── Computer Vision Analysis (OpenCV)
│   ├── Audio Intelligence (Librosa + FFmpeg)
│   ├── AI Coach (Groq Llama-3 + Gemini Vision)
│   ├── PDF Report Generator (ReportLab)
│   └── Multi-User Auth (SQLite + AES Encryption)
│
└── 🧩  Chrome Extension (Manifest V3)
    ├── Viral Cloning Engine
    ├── A/B Test Simulator (Multi-Agent AI Debate)
    ├── BabaClutch Chaos Metric (Local NLP)
    ├── Channel Battles (Competitor Analysis)
    └── Rabbit Hole (Niche Trend Finder)
```

### 🖥️ 1. The Core — Desktop Application

A heavy-duty backend built with **Python 3.11, FastAPI, and PyWebView**, powered by OpenCV and Librosa for deep, frame-by-frame video analysis.

| Feature | Description |
|---|---|
| 🎬 **Computer Vision** | Detects scene cuts, fast-paced edits, and brightness variations using OpenCV |
| 🎵 **Audio Intelligence** | Analyzes audio tempo, dead air (silences), and decibel peaks via Librosa |
| 📊 **Retention Score** | Calculates a highly accurate score based on hook momentum, frame density, and pacing |
| 🤖 **AI Coach** | Analyzes thumbnails, reads transcripts, and delivers actionable brutal feedback |
| 🔐 **Security** | AES-encrypted API key storage (Groq/Gemini) with SQLite for analysis history |
| 📄 **PDF Reports** | Professional multi-language (EN/TR/ES) export with visual charts and comparison tables |
| 👥 **Multi-User SaaS** | Full user auth, per-channel analytics, Google OAuth2, and email verification |

### 🧩 2. The Weapon — Chrome Extension

A sleek, neon-themed **Chrome Extension** that injects directly into the YouTube interface and syncs with the Desktop App.

* **Viral Cloning Engine:** With one click (`Clone This Video`), the extension extracts a viral video's transcript, structure, and psychological triggers, generating 3 unique content hooks tailored to your own niche.
* **DNA Extraction & Master Prompt:** Automatically breaks down a video's transcript into 4 core metrics (Hook, Tempo, CTA, Emotion) using a weighted algorithm. It awards "Synergy Bonuses" for elite pacing and instantly generates a copy-pasteable "Master Prompt" to feed into LLMs for script generation. 🧬
* **A/B Test Simulator (AI Debate):** Two distinct AI Personas (The Critic vs. The Wizard) argue in real-time to find the ultimate viral hook for your next video, judged by a Master AI Referee. ⚔️
* **BabaClutch Chaos Metric:** A 100% local, custom Python NLP algorithm that calculates the "Rage Density" and "Tempo Variance" of competitor transcripts to measure their psychological chaos level. 🌪️
* **Channel Battles (Competitor Analysis):** Visit any competitor's channel page and click `Analyze Channel`. The extension bypasses YouTube's pagination, instantly pulls their real view counts using a hybrid `yt-dlp` engine, and pits their stats against your channel's Quality Score. The AI generates aggressive, guerrilla marketing tactics to steal their audience.
* **Rabbit Hole (Niche Finder):** Stuck on what to film next? Search a broad keyword (e.g., "Crypto"), and the Rabbit Hole module will deep-dive into YouTube to find hidden "Outlier" videos with abnormally high View Velocities.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.11 · FastAPI · Uvicorn · SQLite · Cryptography (Fernet AES) |
| **AI / NLP** | Groq API (Llama-3.3-70b-versatile) · Google Gemini 2.0 Flash (Vision) |
| **Audio / Video** | OpenCV · Librosa · FFmpeg · yt-dlp |
| **Frontend (Desktop)** | PyWebView · Chart.js · Glassmorphism CSS |
| **Frontend (Extension)** | HTML5 · Vanilla CSS · JavaScript (Manifest V3) |
| **Auth** | Google OAuth2 · Email Verification · bcrypt hashing |
| **Reporting** | ReportLab (multi-language PDF) · SMTP email delivery |

---

## 🚀 Installation & Quick Start

### Prerequisites
- Windows 10/11 (64-bit)
- Internet connection for the first-run dependency installation

### Option A — 1-Click Installer (Recommended)

```batch
# Simply double-click:
install.bat
```

> The installer automatically: detects/installs Python 3.11, creates an isolated virtual environment, installs all pip dependencies, installs FFmpeg via yt-dlp, and launches the server.

```batch
# After installation, launch the app anytime with:
START.bat
```

### Option B — Manual Setup

```bash
# 1. Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch the server
python server.pyw
```

### Chrome Extension Setup

1. Open Google Chrome → navigate to `chrome://extensions/`
2. Enable **Developer mode** (top-right toggle)
3. Click **Load unpacked** → select the `chrome_extension/` folder
4. Pin the 🚀 icon to your browser toolbar
5. **Ensure the Desktop App is running** — the extension communicates with it via `localhost:8000`

### Configuration

Once the app is running, open the **Settings** panel to configure:
- 🔑 **Groq API Key** — for all AI Coach features ([get free key](https://console.groq.com))
- 🔑 **Gemini API Key** — for thumbnail vision analysis ([get free key](https://aistudio.google.com))
- 📧 **SMTP Settings** — for automated PDF report email delivery
- 🔐 **Google OAuth2** — for social login support

---

*(For a full list of past version notes, refer to the [Changelog](CHANGELOG.md) in the codebase.)*

---

## 🌌 Connected Projects & Sister Ecosystems

If you like **YouTube Analyse Pro**, check out my other advanced AI projects:

* **[JARVIS-Cognitive-OS (v16.1.0 ARCHITECT UPDATE)](https://github.com/oguzemirtopuz/JARVIS-Cognitive-OS)** 🤖
  * **Armored Sandbox:** AST Sandbox made 100% secure, blocking deep Python vulnerabilities.
  * **Zero Leak (Memory):** Fixed ChromaDB RAM hanging bug; TF-IDF matrix cleared asynchronously.
  * **1-Click Installation:** PowerShell-based automatic FFmpeg downloader and PATH integrator.

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to open an issue or submit a pull request.

---

## 🛡️ License

This project is licensed under the **MIT License**. See the [`LICENSE`](LICENSE) file for details.

---

<div align="center">
  <sub>Built with ❤️ by <a href="https://github.com/oguzemirtopuz">Oğuz Emir Topuz</a> · Star ⭐ the repo if this helped you!</sub>
</div>
