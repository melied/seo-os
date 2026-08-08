import sqlite3
import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import DB_PATH
from agents.intent_agent import TaskStatus

def get_pending_articles() -> list:
    """جلب المقالات التي اجتازت Quality Gate وتنتظر المراجعة البشرية"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, keyword, article_path, quality_report, created_at
        FROM content_tasks
        WHERE status = ?
        ORDER BY created_at DESC
    """, (TaskStatus.READY_FOR_REVIEW,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_task(task_id: int) -> dict:
    """جلب تفاصيل مهمة محددة"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, keyword, search_intent, content_type,
               article_path, quality_report, brief_data,
               outline_data, status, created_at
        FROM content_tasks WHERE id = ?
    """, (task_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        'id': row[0],
        'keyword': row[1],
        'search_intent': row[2],
        'content_type': row[3],
        'article_path': row[4],
        'quality_report': json.loads(row[5]) if row[5] else {},
        'brief_data': json.loads(row[6]) if row[6] else {},
        'outline_data': json.loads(row[7]) if row[7] else {},
        'status': row[8],
        'created_at': row[9]
    }

def read_article_file(task: dict) -> str:
    """قراءة ملف المقال من Filesystem"""
    article_path = task.get('article_path')

    # إذا لم يكن في DB، نبحث في outputs
    if not article_path:
        keyword = task.get('keyword', '')
        import re
        safe_name = re.sub(r'[^\w\s-]', '', keyword).strip()
        safe_name = re.sub(r'[\s]+', '-', safe_name)[:50]
        article_path = os.path.join('outputs', safe_name, 'article.md')

    if article_path and os.path.exists(article_path):
        with open(article_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""

def approve_article(task_id: int, reviewer_notes: str = "") -> dict:
    """
    الموافقة على المقال — يغير الحالة إلى APPROVED
    لا ينشر على Blogger — ينتظر خطوة منفصلة
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    approval_data = {
        "approved_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "reviewer_notes": reviewer_notes,
        "approved_by": "human",
        "action": "APPROVED"
    }

    cursor.execute("""
        UPDATE content_tasks
        SET status = ?, quality_report = json_patch(
            COALESCE(quality_report, '{}'),
            ?
        ), updated_at = datetime('now')
        WHERE id = ? AND status = ?
    """, (
        TaskStatus.APPROVED,
        json.dumps({"approval": approval_data}, ensure_ascii=False),
        task_id,
        TaskStatus.READY_FOR_REVIEW
    ))

    affected = cursor.rowcount
    conn.commit()
    conn.close()

    if affected == 0:
        return {
            "success": False,
            "message": f"Task {task_id} غير موجود أو ليس في حالة READY_FOR_REVIEW"
        }

    return {
        "success": True,
        "task_id": task_id,
        "status": TaskStatus.APPROVED,
        "message": "✅ المقال تمت الموافقة عليه — جاهز لـ Blogger Draft",
        "approval_data": approval_data
    }

def reject_article(task_id: int, reason: str = "") -> dict:
    """
    رفض المقال — يعيده إلى FAILED مع سبب الرفض
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    rejection_data = {
        "rejected_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "reason": reason,
        "rejected_by": "human",
        "action": "REJECTED"
    }

    cursor.execute("""
        UPDATE content_tasks
        SET status = ?, updated_at = datetime('now')
        WHERE id = ? AND status = ?
    """, (
        TaskStatus.FAILED,
        task_id,
        TaskStatus.READY_FOR_REVIEW
    ))

    affected = cursor.rowcount
    conn.commit()
    conn.close()

    if affected == 0:
        return {
            "success": False,
            "message": f"Task {task_id} غير موجود أو ليس في حالة READY_FOR_REVIEW"
        }

    return {
        "success": True,
        "task_id": task_id,
        "status": TaskStatus.FAILED,
        "message": "❌ المقال تم رفضه",
        "rejection_data": rejection_data
    }

def print_pending_list(rows: list):
    print("\n" + "=" * 55)
    print("  Human Approval — Pending Articles")
    print("=" * 55)

    if not rows:
        print("  لا توجد مقالات تنتظر المراجعة")
        print("=" * 55)
        return

    for row in rows:
        task_id, keyword, article_path, quality_report, created_at = row
        qr = json.loads(quality_report) if quality_report else {}
        score = qr.get('score', 0)
        print(f"\n  ID: {task_id}")
        print(f"  الكلمة المفتاحية : {keyword}")
        print(f"  Quality Score    : {score}/100")
        print(f"  تاريخ الإنشاء    : {created_at}")
        print(f"  الملف            : {article_path or 'N/A'}")

    print("\n" + "=" * 55)

def interactive_review(task_id: int):
    """مراجعة تفاعلية لمقال محدد"""
    task = get_task(task_id)
    if not task:
        print(f"  ❌ Task {task_id} غير موجود")
        return

    print("\n" + "=" * 55)
    print(f"  مراجعة المقال — Task {task_id}")
    print("=" * 55)
    print(f"  الكلمة المفتاحية : {task['keyword']}")
    print(f"  Intent           : {task['search_intent']}")
    print(f"  نوع المحتوى      : {task['content_type']}")
    print(f"  الحالة           : {task['status']}")

    qr = task['quality_report']
    if qr:
        print(f"  Quality Score    : {qr.get('score', 0)}/100")

    # عرض المقال
    article = read_article_file(task)
    if article:
        print(f"\n  --- بداية المقال ---")
        # عرض أول 500 حرف فقط
        preview = article[:800].strip()
        print(preview)
        if len(article) > 800:
            print(f"\n  ... ({len(article.split())} كلمة إجمالاً)")
        print(f"  --- نهاية المعاينة ---")
    else:
        print(f"  ⚠️  ملف المقال غير موجود")

    print(f"\n  الخيارات:")
    print(f"  [A] Approve — الموافقة على المقال")
    print(f"  [R] Reject  — رفض المقال")
    print(f"  [S] Skip    — تخطي")

    choice = input("\n  اختر: ").strip().upper()

    if choice == 'A':
        notes = input("  ملاحظات (اختياري): ").strip()
        result = approve_article(task_id, notes)
        print(f"\n  {result['message']}")
        if result['success']:
            print(f"  Task ID: {task_id} → {TaskStatus.APPROVED}")
            print(f"  الخطوة التالية: Blogger Draft")

    elif choice == 'R':
        reason = input("  سبب الرفض: ").strip()
        result = reject_article(task_id, reason)
        print(f"\n  {result['message']}")

    elif choice == 'S':
        print("  تم التخطي")
    else:
        print("  اختيار غير صحيح")

def run():
    """تشغيل Human Approval Workflow"""
    print("\n" + "=" * 55)
    print("  Human Approval Workflow")
    print("=" * 55)

    rows = get_pending_articles()
    print_pending_list(rows)

    if not rows:
        return

    print("\n  أدخل Task ID للمراجعة (أو 0 للخروج):")
    try:
        task_id = int(input("  > ").strip())
    except ValueError:
        print("  ❌ رقم غير صحيح")
        return

    if task_id == 0:
        return

    interactive_review(task_id)

def get_approved_articles() -> list:
    """جلب المقالات المعتمدة الجاهزة لـ Blogger"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, keyword, article_path, quality_report, created_at
        FROM content_tasks
        WHERE status = ?
        ORDER BY created_at DESC
    """, (TaskStatus.APPROVED,))
    rows = cursor.fetchall()
    conn.close()
    return rows

if __name__ == "__main__":
    run()