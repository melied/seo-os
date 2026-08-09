import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import BLOGGER_OAUTH_CLIENT, BLOGGER_TOKEN

SCOPES = ['https://www.googleapis.com/auth/blogger']

def get_blogger_credentials():
    """
    الحصول على OAuth credentials لـ Blogger
    المرة الأولى: يفتح المتصفح للمصادقة
    بعدها: يستخدم الـ token المحفوظ
    """
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request

    creds = None

    # تحقق من وجود token محفوظ
    if os.path.exists(BLOGGER_TOKEN):
        creds = Credentials.from_authorized_user_file(BLOGGER_TOKEN, SCOPES)

    # إذا لا يوجد token أو منتهي الصلاحية
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                BLOGGER_OAUTH_CLIENT, SCOPES
            )
            creds = flow.run_local_server(port=0)

        # حفظ الـ token للمرة القادمة
        with open(BLOGGER_TOKEN, 'w') as f:
            f.write(creds.to_json())
        print(f"  ✅ Token محفوظ: {BLOGGER_TOKEN}")

    return creds

def get_blogger_service():
    """الحصول على Blogger API service"""
    from googleapiclient.discovery import build
    creds = get_blogger_credentials()
    return build('blogger', 'v3', credentials=creds)

def test_auth():
    print("\n=== اختبار Blogger OAuth ===")
    try:
        service = get_blogger_service()
        blog = service.blogs().get(blogId='5054239674590804140').execute()
        print(f"  ✅ تم الاتصال بـ Blogger")
        print(f"  اسم المدونة: {blog.get('name')}")
        print(f"  المقالات   : {blog.get('posts', {}).get('totalItems', 0)}")
        return True
    except Exception as e:
        print(f"  ❌ خطأ: {e}")
        return False

if __name__ == "__main__":
    test_auth()