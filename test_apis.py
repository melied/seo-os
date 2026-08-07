import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from config.settings import GOOGLE_SERVICE_ACCOUNT_JSON, GSC_SITE_URL, BLOGGER_BLOG_ID

SCOPES = [
    'https://www.googleapis.com/auth/webmasters.readonly',
    'https://www.googleapis.com/auth/blogger.readonly'
]

def get_credentials():
    creds = service_account.Credentials.from_service_account_file(
        GOOGLE_SERVICE_ACCOUNT_JSON,
        scopes=SCOPES
    )
    return creds

def test_search_console(creds):
    print("=== اختبار Search Console ===")
    try:
        service = build('webmasters', 'v3', credentials=creds)
        result = service.searchanalytics().query(
            siteUrl=GSC_SITE_URL,
            body={
                'startDate': '2025-06-01',
                'endDate': '2025-07-31',
                'dimensions': ['query'],
                'rowLimit': 5
            }
        ).execute()

        rows = result.get('rows', [])
        if rows:
            print(f"✅ Search Console يعمل — أول 5 كلمات:")
            for row in rows:
                print(f"   - {row['keys'][0]} | clicks: {row['clicks']} | impressions: {row['impressions']}")
        else:
            print("⚠️  الاتصال نجح لكن لا توجد بيانات في هذا النطاق الزمني")
    except Exception as e:
        print(f"❌ خطأ في Search Console: {e}")

def test_blogger(creds):
    print("\n=== اختبار Blogger ===")
    try:
        service = build('blogger', 'v3', credentials=creds)

        # أولاً نجلب معلومات المدونة
        blog = service.blogs().getByUrl(
            url='https://www.news-theworld.com/'
        ).execute()

        blog_id = blog.get('id')
        blog_name = blog.get('name')
        posts_count = blog.get('posts', {}).get('totalItems', 0)

        print(f"✅ Blogger يعمل:")
        print(f"   - اسم المدونة: {blog_name}")
        print(f"   - Blog ID: {blog_id}")
        print(f"   - إجمالي المقالات: {posts_count}")
        print(f"\n📌 احفظ هذا الـ Blog ID في config/.env")
        print(f"   BLOGGER_BLOG_ID={blog_id}")

    except Exception as e:
        print(f"❌ خطأ في Blogger: {e}")

if __name__ == "__main__":
    print("جاري الاتصال بـ Google APIs...\n")
    creds = get_credentials()
    test_search_console(creds)
    test_blogger(creds)