import sqlite3
import os

DB_PATH = os.path.join("data", "seo_os.db")

def create_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            slug TEXT,
            keyword TEXT,
            status TEXT DEFAULT 'draft',
            content TEXT,
            meta_title TEXT,
            meta_description TEXT,
            schema TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            published_at TEXT,
            blogger_post_id TEXT
        );

        CREATE TABLE IF NOT EXISTS keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT,
            monthly_searches INTEGER,
            difficulty TEXT,
            intent TEXT,
            status TEXT DEFAULT 'pending',
            article_id INTEGER
        );

        CREATE TABLE IF NOT EXISTS gsc_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page TEXT,
            query TEXT,
            clicks INTEGER,
            impressions INTEGER,
            ctr REAL,
            position REAL,
            date_range TEXT,
            fetched_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS internal_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_article_id INTEGER,
            target_article_id INTEGER,
            anchor_text TEXT
        );
    """)

    conn.commit()
    conn.close()
    print("✅ قاعدة البيانات جاهزة: data/seo_os.db")

if __name__ == "__main__":
    create_database()