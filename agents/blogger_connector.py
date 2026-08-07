import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.oauth2 import service_account
from googleapiclient.discovery import build
from config.settings import GOOGLE_SERVICE_ACCOUNT_JSON, BLOGGER_BLOG_ID, DB_PATH

SCOPES = ['https://www.googleapis.com/auth/blogger.readonly']

def get_service():
    creds = service_account.Credentials.from_service_account_file(
        GOOGLE_SERVICE_ACCOUNT_JSON, scopes=SCOPES
    )
    return build('blogger', 'v3', credentials=creds)

def fetch_all_posts():
    service = get_service()
    all_posts = []
    page_token = None

    print("جاري جلب المقالات من Blogger...")

    while True:
        params = {
            'blogId': BLOGGER_BLOG_ID,
            'maxResults': 20,
            'status': 'LIVE',
            'fetchBodies': True,
            'fetchImages': False
        }
        if page_token:
            params['pageToken'] = page_token

        result = service.posts().list(**params).execute()
        posts = result.get('items', [])
        all_posts.extend(posts)

        print(f"   تم جلب {len(all_posts)} مقال...")

        page_token = result.get('nextPageToken')
        if not page_token:
            break

    return all_posts

def save_posts_to_db(posts):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    saved = 0
    updated = 0

    for post in posts:
        post_id = post.get('id')
        title = post.get('title', '')
        url = post.get('url', '')
        content = post.get('content', '')
        published = post.get('published', '')
        labels = ', '.join(post.get('labels', []))

        slug = url.rstrip('/').split('/')[-1].replace('.html', '')

        cursor.execute("SELECT id FROM articles WHERE blogger_post_id = ?", (post_id,))
        existing = cursor.fetchone()

        if existing:
            cursor.execute("""
                UPDATE articles SET title=?, slug=?, content=?, published_at=?, status=?
                WHERE blogger_post_id=?
            """, (title, slug, content, published, 'published', post_id))
            updated += 1
        else:
            cursor.execute("""
                INSERT INTO articles (title, slug, content, published_at, status, blogger_post_id, keyword)
                VALUES (?, ?, ?, ?, 'published', ?, ?)
            """, (title, slug, content, published, post_id, labels))
            saved += 1

    conn.commit()
    conn.close()
    return saved, updated

def run():
    posts = fetch_all_posts()
    saved, updated = save_posts_to_db(posts)
    print(f"\n✅ اكتمل جلب المقالات:")
    print(f"   - إجمالي المقالات: {len(posts)}")
    print(f"   - محفوظة جديدة: {saved}")
    print(f"   - محدّثة: {updated}")

if __name__ == "__main__":
    run()