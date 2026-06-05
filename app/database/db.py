"""
app/database/db.py
──────────────────
Veritabanı katmanı — server.pyw'dan ayrıştırıldı (FAZ 1 Refactor).

İçerik:
  • db_path        : SQLite dosya yolu (EXE / geliştirme modu uyumlu)
  • get_db()       : Senkron bağlantı (sqlite3)
  • get_async_db() : Asenkron bağlantı (aiosqlite, WAL modu)
  • init_db()      : Tüm tabloları oluşturur + migration'ları uygular
  • migrate_data() : Eski misafir verilerini hedef kullanıcıya taşır
"""

import os
import sys
import asyncio
import sqlite3
import aiosqlite
import logging

# ─── Crossroads: EXE vs development ───────────────────── ──────────────────────
if getattr(sys, 'frozen', False):
    _APP_DIR = os.path.dirname(sys.executable)
else:
    # This file is located at app/database/db.py; project root 2 levels up
    _APP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

db_path = os.path.join(_APP_DIR, 'channels.db')

# Instead of sharing the app_logger in server.pyw, use the module's own logger.
# The root logger will already be configured when server.pyw starts.
_logger = logging.getLogger("yt_analiz.database")


# ─── Connection functions ───────────────────────── ──────────────────────────

def get_db():
    """Senkron SQLite bağlantısı döndürür.
    
    STRES TESTİ FIX: WAL (Write-Ahead Logging) modu etkinleştirildi.
    Senkron (sync) ve asenkron (async) bağlantılar aynı dosyaya eş zamanlı
    yazarken 'database is locked' race condition'ını önler.
    timeout=5 → lock beklerken 5 saniye dener, sonra OperationalError fırlatır.
    """
    conn = sqlite3.connect(str(db_path), check_same_thread=False, timeout=5)
    conn.row_factory = sqlite3.Row
    # WAL mode: reading never blocks writing
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")  # WAL ile güvenli, daha hızlı
    return conn


async def get_async_db():
    """Asenkron SQLite bağlantısı döndürür (WAL modunda). Endpoint'ler için."""
    db = await aiosqlite.connect(str(db_path))
    await db.execute("PRAGMA journal_mode=WAL;")
    db.row_factory = aiosqlite.Row
    return db


# ─── init_db ──────────────────────────────── ─────────────────────────────────

def init_db():
    """Senkron init_db — asyncio.run ile aiosqlite kullanır."""
    async def _init():
        db = await get_async_db()
        try:
            await db.execute('''CREATE TABLE IF NOT EXISTS users
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

            await db.execute('''CREATE TABLE IF NOT EXISTS email_verifications
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        code TEXT NOT NULL,
                        expires_at TIMESTAMP NOT NULL,
                        verified INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

            await db.execute('''CREATE TABLE IF NOT EXISTS channels
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        content_type TEXT,
                        target_audience TEXT,
                        purpose TEXT,
                        user_id INTEGER DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

            await db.execute('''CREATE TABLE IF NOT EXISTS analyses
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                        channel_id INTEGER,
                        video_name TEXT,
                        overall_score REAL,
                        retention_score REAL,
                        tech_score REAL,
                        seo_score REAL,
                        thumb_score REAL,
                        peaks INTEGER,
                        viral_score REAL,
                        coach_feedback TEXT,
                        competitor_data TEXT,
                        analysis_duration_sec REAL DEFAULT 0,
                        video_description TEXT,
                        video_tags TEXT,
                        user_id INTEGER DEFAULT 1,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(channel_id) REFERENCES channels(id))''')

            await db.execute('''CREATE TABLE IF NOT EXISTS content_ideas
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER DEFAULT 1,
                        keyword TEXT NOT NULL,
                        generated_ideas_json TEXT,
                        search_results_json TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

            await db.execute('''CREATE TABLE IF NOT EXISTS app_settings
                        (key TEXT PRIMARY KEY, value TEXT)''')

            await db.execute('''CREATE TABLE IF NOT EXISTS chat_sessions
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER DEFAULT 1,
                        title TEXT NOT NULL DEFAULT 'Yeni Sohbet',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

            await db.execute('''CREATE TABLE IF NOT EXISTS chat_messages
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id INTEGER NOT NULL,
                        sender TEXT NOT NULL,
                        text TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE)''')

            await db.execute('''CREATE TABLE IF NOT EXISTS user_sessions
                        (token TEXT PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(user_id) REFERENCES users(id))''')

            migrations = [
                "ALTER TABLE analyses ADD COLUMN coach_feedback TEXT",
                "ALTER TABLE analyses ADD COLUMN competitor_data TEXT",
                "ALTER TABLE analyses ADD COLUMN analysis_duration_sec REAL DEFAULT 0",
                "ALTER TABLE analyses ADD COLUMN video_description TEXT",
                "ALTER TABLE analyses ADD COLUMN video_tags TEXT",
                "ALTER TABLE channels ADD COLUMN user_id INTEGER DEFAULT 1",
                "ALTER TABLE analyses ADD COLUMN user_id INTEGER DEFAULT 1",
                "ALTER TABLE users ADD COLUMN email TEXT",
                "ALTER TABLE users ADD COLUMN is_verified INTEGER DEFAULT 0",
                "ALTER TABLE users ADD COLUMN profile_pic TEXT",
                "ALTER TABLE users ADD COLUMN google_id TEXT",
                "ALTER TABLE users ADD COLUMN access_token TEXT",
                "ALTER TABLE users ADD COLUMN auth_provider TEXT DEFAULT 'local'",
                "ALTER TABLE chat_sessions ADD COLUMN user_id INTEGER DEFAULT 1",
                "ALTER TABLE channels ADD COLUMN channel_rules TEXT",
                "ALTER TABLE analyses ADD COLUMN is_favorite INTEGER DEFAULT 0",
            ]
            for sql in migrations:
                try:
                    await db.execute(sql)
                except Exception as e:
                    _logger.debug(f"Migration zaten uygulanmış veya hata: {sql[:50]} → {e}")

            await db.execute("INSERT OR IGNORE INTO users (id, username, password_hash) VALUES (1, 'misafir', '')")
            await db.commit()
        finally:
            await db.close()
        _logger.info("✅ Veritabanı başlatıldı ve migration'lar uygulandı.")

    asyncio.run(_init())


# ─── migrate_data ────────────────────────────── ───────────────────────────────

def migrate_data(target_user_id):
    """Misafir (user_id=1) verilerini hedef kullanıcıya taşır."""
    try:
        async def _migrate():
            db = await get_async_db()
            try:
                await db.execute("UPDATE channels SET user_id = 1 WHERE user_id IS NULL")
                await db.execute("UPDATE analyses SET user_id = 1 WHERE user_id IS NULL")
                await db.execute("UPDATE channels SET user_id = ? WHERE user_id = 1", (target_user_id,))
                await db.execute("UPDATE analyses SET user_id = ? WHERE user_id = 1", (target_user_id,))
                await db.execute("UPDATE content_ideas SET user_id = ? WHERE user_id = 1", (target_user_id,))
                await db.commit()
            finally:
                await db.close()
        asyncio.run(_migrate())
        print(f"✅ AKTARMA BAŞARILI: Tüm veriler ID: {target_user_id} hesabına taşındı.")
    except Exception as e:
        _logger.error(f"❌ AKTARMA HATASI: {e}", exc_info=True)
