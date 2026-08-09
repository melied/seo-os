import sqlite3
import sys
import os
import json
import re
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import DB_PATH, BLOGGER_BLOG_ID, GOOGLE_SERVICE_ACCOUNT_JSON
from agents.intent_agent import TaskStatus

# ======================================================
# Markdown → HTML
# ======================================================

def markdown_to_html(text: str) -> str:
    """تحويل Markdown إلى HTML مناسب لـ Blogger"""
    lines = text.split('\n')
    html_lines = []
    in_list = False

    for line in lines:
        # تخطي الـ Schema وملفات JSON
        if line.strip().startswith('```') or line.strip().startswith('{'):
            continue

        # H1
        if line.startswith('# ') and not line.startswith('## '):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append(f'<h1>{line[2:].strip()}</h1>')

        # H2
        elif line.startswith('## ') and not line.startswith('### '):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append(f'<h2>{line[3:].strip()}</h2>')

        # H3
        elif line.startswith('### '):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append(f'<h3>{line[4:].strip()}</h3>')

        # قائمة
        elif line.strip().startswith('- ') or line.strip().startswith('* '):
            if not in_list:
                html_lines.append('<ul>')
                in_list = True
            item = line.strip()[2:]
            item = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', item)
            html_lines.append(f'<li>{item}</li>')

        # فقرة عادية
        elif line.strip():
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            paragraph = line.strip()
            paragraph = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', paragraph)
            paragraph = re.sub(r'\*(.+?)\*', r'<em>\1</em>', paragraph)
            html_lines.append(f'<p>{paragraph}</p>')

        else:
            if in_list:
                html_lines.append('</ul>')
                in_list = False

    if in_list:
        html_lines.append('</ul>')

    return '\n'.join(html_lines)

def build_schema_html(schema_path: str) -> str:
    """بناء Schema script tag من ملف JSON"""
    if not schema_path or not os.path.exists(schema_path):
        return ""

    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = json.load(f)
        schema_json = json.dumps(schema, ensure_ascii=False, indent=2)
        return f'\n<script type="application/ld+json">\n{schema_json}\n</script>'
    except Exception:
        return ""

def read_task_files(task: dict) -> dict:
    """قراءة ملفات الـ Pipeline من Filesystem"""
    keyword = task.get('keyword', '')
    safe_name = re.sub(r'[^\w\s-]', '', keyword).strip()
    safe_name = re.sub(r'[\s]+', '-', safe_name)[:50]
    task_dir = os.path.join('outputs', safe_name)

    files = {}

    # Article
    article_path = task.get('article_path') or os.path.join(task_dir, 'article.md')
    if article_path and os.path.exists(article_path):
        with open(article_path, 'r', encoding='utf-8') as f:
            files['article'] = f.read()
        files['article_path'] = article_path

    # Schema
    schema_path = os.path.join(task_dir, 'schema.json')
    if os.path.exists(schema_path):
        files['schema_path'] = schema_path

    # Outline (للروابط الداخلية)
    outline_path = os.path.join(task_dir, 'outline.json')
    if os.path.exists(outline_path):
        with open(outline_path, 'r', encoding='utf-8') as f:
            files['outline'] = json.load(f)

    return files

def build_blogger_post(task: dict, files: dict) -> dict:
    """
    بناء Blogger Post payload
    يعيد dict جاهز للـ Blogger API
    لا يرسل أي شيء بعد
    """
    article_md = files.get('article', '')
    outline = files.get('outline', {})

    if not article_md:
        return None

    # استخرج Meta Title
    brief_data = task.get('brief_data', {})
    quality_report = task.get('quality_report', {})
    meta_title = brief_data.get('recommended_title', task.get('keyword', ''))

    # H1 من الـ outline
    h1 = outline.get('h1', meta_title)

    # تحويل المقال لـ HTML
    html_content = markdown_to_html(article_md)

    # إضافة Schema
    schema_html = build_schema_html(files.get('schema_path', ''))
    if schema_html:
        html_content += schema_html

    # إضافة روابط داخلية
    link_candidates = outline.get('internal_link_candidates', [])
    if link_candidates:
        links_html = '\n<div class="internal-links">\n<h3>مقالات ذات صلة</h3>\n<ul>\n'
        for link in link_candidates[:3]:
            title = link.get('title', '')
            slug = link.get('slug', '')
            if title and slug:
                year = datetime.now().year
                url = f"https://www.news-theworld.com/{year}/{slug}.html"
                links_html += f'<li><a href="{url}">{title}</a></li>\n'
        links_html += '</ul>\n</div>'
        html_content += links_html

    # Labels من التصنيفات
    keyword = task.get('keyword', '')
    labels = _get_labels(keyword)

    return {
        "title": h1 or meta_title,
        "content": html_content,
        "labels": labels,
        "status": "DRAFT",
        "meta_title": meta_title,
        "keyword": keyword
    }

def _get_labels(keyword: str) -> list:
    """استخرج labels مناسبة من الكلمة المفتاحية"""
    labels = []
    keyword_lower = keyword.lower()

    label_map = {
        'دجاج': 'تربية الدجاج',
        'دواجن': 'تربية الدجاج',
        'ماعز': 'الثروة الحيوانية',
        'غنم': 'الثروة الحيوانية',
        'خروف': 'الثروة الحيوانية',
        'بقر': 'الثروة الحيوانية',
        'ماشية': 'الثروة الحيوانية',
        'علف': 'التغذية والأعلاف',
        'مشروع': 'المشاريع الزراعية',
        'جدوى': 'المشاريع الزراعية',
        'سعر': 'أسعار الثروة الحيوانية',
        'زراعة': 'الزراعة',
        'سمان': 'تربية السمان',
        'ارانب': 'تربية الأرانب'
    }

    for key, label in label_map.items():
        if key in keyword_lower and label not in labels:
            labels.append(label)

    if not labels:
        labels = ['الثروة الحيوانية والفلاحة']

    return labels

def publish_to_blogger(post: dict, as_draft: bool = True) -> dict:
    """
    إرسال المقال إلى Blogger API باستخدام OAuth
    as_draft=True: يحفظ كمسودة (الوضع الافتراضي)
    """
    if not BLOGGER_BLOG_ID:
        return {
            "success": False,
            "error": "BLOGGER_BLOG_ID غير مضبوط"
        }

    try:
        from agents.blogger_auth import get_blogger_service
        service = get_blogger_service()

        body = {
            'title': post['title'],
            'content': post['content'],
            'labels': post.get('labels', [])
        }

        result = service.posts().insert(
            blogId=BLOGGER_BLOG_ID,
            body=body,
            isDraft=as_draft
        ).execute()

        return {
            "success": True,
            "post_id": result.get('id'),
            "post_url": result.get('url', ''),
            "status": result.get('status'),
            "title": result.get('title')
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def save_draft_locally(post: dict, task_id: int) -> str:
    """حفظ الـ Draft محلياً قبل الإرسال لـ Blogger"""
    keyword = post.get('keyword', f'task-{task_id}')
    safe_name = re.sub(r'[^\w\s-]', '', keyword).strip()
    safe_name = re.sub(r'[\s]+', '-', safe_name)[:50]

    task_dir = os.path.join('outputs', safe_name)
    os.makedirs(task_dir, exist_ok=True)

    draft_path = os.path.join(task_dir, 'blogger_draft.html')
    with open(draft_path, 'w', encoding='utf-8') as f:
        f.write(f"<!-- Title: {post['title']} -->\n")
        f.write(f"<!-- Labels: {', '.join(post.get('labels', []))} -->\n")
        f.write(f"<!-- Status: DRAFT -->\n\n")
        f.write(post['content'])

    return draft_path

def update_task_status(task_id: int, post_id: str = None,
                       post_url: str = None, status: str = TaskStatus.PUBLISHED):
    """تحديث حالة الـ Task بعد الإرسال"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE content_tasks
        SET status = ?, updated_at = datetime('now')
        WHERE id = ?
    """, (status, task_id))
    conn.commit()
    conn.close()

def run_draft(task_id: int, send_to_blogger: bool = False) -> dict:
    """
    تشغيل Blogger Draft لمهمة محددة
    send_to_blogger=False: يحفظ محلياً فقط (الوضع الافتراضي والآمن)
    send_to_blogger=True: يرسل لـ Blogger كمسودة
    """
    from agents.human_approval import get_task

    print(f"\n{'=' * 55}")
    print(f"  Blogger Draft — Task {task_id}")
    print(f"{'=' * 55}")

    # 1. تحقق من الحالة
    task = get_task(task_id)
    if not task:
        return {"success": False, "error": f"Task {task_id} غير موجود"}

    if task['status'] != TaskStatus.APPROVED:
        return {
            "success": False,
            "error": f"Task {task_id} ليس في حالة APPROVED (الحالة الحالية: {task['status']})"
        }

    print(f"  الكلمة المفتاحية : {task['keyword']}")
    print(f"  الحالة           : {task['status']} ✅")

    # 2. قراءة الملفات
    files = read_task_files(task)
    if not files.get('article'):
        return {"success": False, "error": "ملف المقال غير موجود"}

    print(f"  المقال           : {len(files['article'].split())} كلمة ✅")

    # 3. بناء الـ Post
    post = build_blogger_post(task, files)
    if not post:
        return {"success": False, "error": "فشل في بناء الـ Post"}

    print(f"  العنوان          : {post['title'][:50]}...")
    print(f"  Labels           : {', '.join(post['labels'])}")

    # 4. حفظ محلياً دائماً
    draft_path = save_draft_locally(post, task_id)
    print(f"  Draft محفوظ      : {draft_path} ✅")

    # 5. إرسال لـ Blogger (اختياري)
    if send_to_blogger:
        print(f"\n  جاري إرسال المسودة لـ Blogger...")
        result = publish_to_blogger(post, as_draft=True)

        if result['success']:
            print(f"  ✅ تم إنشاء المسودة على Blogger")
            print(f"     Post ID  : {result['post_id']}")
            print(f"     Post URL : {result.get('post_url', 'N/A')}")
            update_task_status(task_id, result['post_id'], result.get('post_url'))
            return {
                "success": True,
                "draft_path": draft_path,
                "blogger_post_id": result['post_id'],
                "blogger_url": result.get('post_url'),
                "status": "DRAFT_ON_BLOGGER"
            }
        else:
            print(f"  ❌ فشل الإرسال: {result['error']}")
            return {
                "success": False,
                "draft_path": draft_path,
                "error": result['error']
            }
    else:
        print(f"\n  ℹ️  Draft محفوظ محلياً فقط")
        print(f"  لإرسال لـ Blogger: استخدم send_to_blogger=True")
        return {
            "success": True,
            "draft_path": draft_path,
            "status": "DRAFT_LOCAL"
        }

def run():
    """تشغيل Blogger Draft Workflow"""
    from agents.human_approval import get_approved_articles

    print(f"\n{'=' * 55}")
    print(f"  Blogger Draft Workflow")
    print(f"{'=' * 55}")

    rows = get_approved_articles()

    if not rows:
        print(f"  لا توجد مقالات معتمدة جاهزة للنشر")
        print(f"{'=' * 55}")
        return

    print(f"\n  المقالات المعتمدة ({len(rows)}):\n")
    for row in rows:
        task_id, keyword, article_path, quality_report, created_at = row
        print(f"  ID: {task_id} | {keyword}")

    print(f"\n  أدخل Task ID (أو 0 للخروج):")
    try:
        task_id = int(input("  > ").strip())
    except ValueError:
        print("  ❌ رقم غير صحيح")
        return

    if task_id == 0:
        return

    print(f"\n  هل تريد إرسال المسودة لـ Blogger الآن؟")
    print(f"  [L] حفظ محلياً فقط (آمن)")
    print(f"  [B] إرسال لـ Blogger كمسودة")
    choice = input("  > ").strip().upper()

    send = choice == 'B'
    result = run_draft(task_id, send_to_blogger=send)

    print(f"\n{'=' * 55}")
    if result['success']:
        print(f"  ✅ النتيجة: {result.get('status')}")
        print(f"  Draft: {result.get('draft_path')}")
        if result.get('blogger_post_id'):
            print(f"  Blogger Post ID: {result['blogger_post_id']}")
    else:
        print(f"  ❌ فشل: {result.get('error')}")
    print(f"{'=' * 55}")

if __name__ == "__main__":
    run()