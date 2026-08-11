import sqlite3
import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import DB_PATH
from agents.intent_agent import TaskStatus
from agents.validators import (
    run_all_validations,
    print_validation_report
)

CRITICAL_CHECKS = [
    "full_article",
    "has_introduction",
    "no_placeholders",
    "valid_h1_count",
    "min_h2_count",
    "no_duplicate_headings",
    "valid_schema"
]

WARNING_CHECKS = [
    "has_conclusion",
    "keyword_density",
    "keyword_present"
]

def run_quality_gate(
    article_text: str,
    keyword: str = "",
    schema=None,
    outline=None,
    meta_title: str = "",
    meta_description: str = "",
    slug: str = ""
) -> dict:

    if not article_text or article_text.strip() == "":
        return {
            "status": TaskStatus.AI_UNAVAILABLE,
            "passed": False,
            "critical_issues": ["لا يوجد محتوى — AI غير متاح أو فشل في توليد المقال"],
            "warnings": [],
            "checks": {},
            "score": 0,
            "quality_gate": "FAILED"
        }

    validation = run_all_validations(article_text, keyword, schema)
    article_v = validation['article']
    schema_v = validation['schema']

    critical_issues = []
    warnings = list(article_v.get('warnings', []))
    checks = {}

    from agents.validators import is_full_article
    checks['full_article'] = is_full_article(article_text, min_words=200)
    if not checks['full_article']:
        critical_issues.append("❌ النص ليس مقالاً كاملاً — أقل من 200 كلمة")

    from agents.validators import has_introduction
    checks['has_introduction'] = has_introduction(article_text)
    if not checks['has_introduction']:
        critical_issues.append("❌ المقدمة مفقودة")

    checks['no_placeholders'] = article_v['placeholder_check']['passed']
    if not checks['no_placeholders']:
        for issue in article_v['placeholder_check']['issues']:
            critical_issues.append(f"❌ {issue}")

    h1_count = article_v['headings']['h1']
    checks['valid_h1_count'] = h1_count == 1
    if h1_count == 0:
        critical_issues.append("❌ لا يوجد H1 في المقال")
    elif h1_count > 1:
        critical_issues.append(f"❌ يوجد {h1_count} عناوين H1 — يجب أن يكون واحداً")

    h2_count = article_v['headings']['h2']
    checks['min_h2_count'] = h2_count >= 2
    if not checks['min_h2_count']:
        critical_issues.append("❌ عدد الأقسام الرئيسية أقل من 2")

    from agents.validators import find_duplicate_headings
    duplicates = find_duplicate_headings(article_text)
    checks['no_duplicate_headings'] = len(duplicates) == 0
    if duplicates:
        critical_issues.append(f"❌ عناوين مكررة: {', '.join(duplicates)}")

    checks['valid_schema'] = schema_v['passed'] if schema else True
    if schema and not schema_v['passed']:
        for issue in schema_v['issues']:
            critical_issues.append(issue)

    checks['has_meta_title'] = bool(meta_title and len(meta_title) >= 10)
    if not checks['has_meta_title']:
        critical_issues.append("❌ Meta Title مفقود أو قصير جداً")

    checks['has_meta_description'] = bool(meta_description and len(meta_description) >= 50)
    if not checks['has_meta_description']:
        warnings.append("⚠️  Meta Description مفقود أو قصير")

    checks['has_slug'] = bool(slug and len(slug) >= 3)
    if not checks['has_slug']:
        warnings.append("⚠️  Slug مفقود")

    from agents.validators import has_conclusion
    checks['has_conclusion'] = has_conclusion(article_text)
    if not checks['has_conclusion']:
        warnings.append("⚠️  الخاتمة غير واضحة")

    if keyword:
        checks['keyword_present'] = keyword.lower() in article_text.lower()
        if not checks['keyword_present']:
            warnings.append(f"⚠️  الكلمة المفتاحية '{keyword}' غير موجودة في المقال")

    total_critical = len(CRITICAL_CHECKS) + 2
    passed_critical = sum(1 for k in CRITICAL_CHECKS if checks.get(k, False))
    passed_critical += (1 if checks.get('has_meta_title') else 0)
    passed_critical += (1 if checks.get('valid_schema') else 0)
    score = int((passed_critical / total_critical) * 100) if total_critical > 0 else 0

    if len(critical_issues) == 0:
        status = TaskStatus.READY_FOR_REVIEW
        passed = True
    else:
        status = TaskStatus.FAILED
        passed = False

    return {
        "status": status,
        "passed": passed,
        "critical_issues": critical_issues,
        "warnings": warnings,
        "checks": checks,
        "score": score,
        "quality_gate": "PASSED" if passed else "FAILED",
        "word_count": article_v['word_count'],
        "headings": article_v['headings']
    }

def save_quality_report(task_id: int, report: dict):
    """حفظ تقرير الـ Quality Gate في قاعدة البيانات — يدعم V1 وV2"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # V1 يستخدم 'status' — V2 يستخدم 'gate_status'
    status = report.get('gate_status') or report.get('status') or TaskStatus.FAILED

    cursor.execute("""
        UPDATE content_tasks
        SET quality_report = ?, status = ?, updated_at = datetime('now')
        WHERE id = ?
    """, (
        json.dumps(report, ensure_ascii=False),
        status,
        task_id
    ))
    conn.commit()
    conn.close()

def print_quality_report(report: dict):
    gate = report['quality_gate']
    icon = "✅" if gate == "PASSED" else "❌"
    status = report['status']

    print(f"\n{'=' * 55}")
    print(f"     Quality Gate Report — {icon} {gate}")
    print(f"{'=' * 55}")
    print(f"  الحالة     : {status}")
    print(f"  النقاط     : {report['score']}/100")
    print(f"  الكلمات    : {report.get('word_count', 0)}")

    headings = report.get('headings', {})
    if headings:
        print(f"  العناوين   : H1={headings.get('h1',0)} | H2={headings.get('h2',0)} | H3={headings.get('h3',0)}")

    print(f"\n  الفحوصات:")
    for check, result in report['checks'].items():
        icon_c = "✅" if result else "❌"
        print(f"    {icon_c} {check}")

    if report['critical_issues']:
        print(f"\n  ❌ مشاكل حرجة ({len(report['critical_issues'])}):")
        for issue in report['critical_issues']:
            print(f"     {issue}")

    if report['warnings']:
        print(f"\n  ⚠️  تحذيرات ({len(report['warnings'])}):")
        for w in report['warnings']:
            print(f"     {w}")

    print(f"\n{'=' * 55}")
    if gate == "PASSED":
        print("  ✅ المقال جاهز للمراجعة البشرية")
        print("  ⏳ في انتظار الموافقة قبل النشر")
    else:
        print("  ❌ المقال لا يمكن تمريره — يجب إصلاح المشاكل الحرجة")
    print(f"{'=' * 55}")

def run(article_text: str = None, keyword: str = "",
        schema=None, meta_title: str = "",
        meta_description: str = "", slug: str = "",
        task_id: int = None) -> dict:

    if not article_text:
        print("❌ لا يوجد نص للتحقق منه")
        return {"status": TaskStatus.FAILED, "passed": False}

    print(f"\n🔍 جاري تشغيل Quality Gate...")
    report = run_quality_gate(
        article_text, keyword, schema,
        meta_title=meta_title,
        meta_description=meta_description,
        slug=slug
    )

    if task_id:
        save_quality_report(task_id, report)

    print_quality_report(report)
    return report


if __name__ == "__main__":
    from tests.test_validators import FULL_ARTICLE

    schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": "تربية الدجاج في الجزائر: دليل شامل 2026",
        "description": "دليل شامل لتربية الدجاج في الجزائر",
        "author": {"@type": "Organization", "name": "الثروة الحيوانية"},
        "datePublished": datetime.now().strftime('%Y-%m-%d'),
        "dateModified": datetime.now().strftime('%Y-%m-%d'),
        "url": "https://www.news-theworld.com/2026/chicken-farming.html"
    }

    run(
        article_text=FULL_ARTICLE,
        keyword="تربية الدجاج في الجزائر",
        schema=schema,
        meta_title="تربية الدجاج في الجزائر: دليل شامل 2026",
        meta_description="كل ما تحتاجه لبدء مشروع تربية الدجاج في الجزائر من الصفر.",
        slug="chicken-farming-algeria-2026"
    )