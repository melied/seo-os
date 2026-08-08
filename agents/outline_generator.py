import sqlite3
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import DB_PATH
from agents.intent_agent import TaskStatus

def build_outline_from_brief(brief: dict) -> dict:
    """
    توليد Outline من Content Brief بدون AI
    Outline ≠ Article — هو هيكل فقط
    """
    keyword = brief['keyword']
    intent = brief['intent']
    sections = brief['sections']
    questions = brief.get('questions_to_answer', [])
    recommended_title = brief['recommended_title']

    # توليد H1 من العنوان المقترح (لا من keyword مباشرة)
    h1 = _generate_h1(brief)

    # بناء الأقسام
    outline_sections = []

    for section in sections:
        section_type = section.get('type')

        if section_type == 'introduction':
            outline_sections.append({
                "type": "introduction",
                "h2": None,
                "writing_notes": _get_intro_notes(keyword, intent),
                "word_count": section.get('word_count', '100-150'),
                "must_include": [keyword, "سبب أهمية الموضوع", "ما سيجده القارئ"]
            })

        elif section_type == 'h2':
            heading = section.get('heading', '')
            outline_sections.append({
                "type": "h2",
                "h2": heading,
                "h3_suggestions": _get_h3_suggestions(heading, keyword),
                "writing_notes": _get_section_notes(heading, intent),
                "word_count": section.get('word_count', '150-250'),
                "must_include": _get_must_include(heading)
            })

        elif section_type == 'faq':
            faq_questions = section.get('questions', questions[:5])
            if faq_questions:
                outline_sections.append({
                    "type": "faq",
                    "h2": "أسئلة شائعة",
                    "questions": faq_questions,
                    "writing_notes": "أجب بشكل مباشر وموجز. لا تكرر السؤال في الإجابة.",
                    "word_count": "50-80 لكل سؤال"
                })

        elif section_type == 'conclusion':
            outline_sections.append({
                "type": "conclusion",
                "h2": "خاتمة",
                "writing_notes": _get_conclusion_notes(intent),
                "word_count": section.get('word_count', '80-120'),
                "must_include": ["تلخيص النقاط الرئيسية", "توجيه للخطوة التالية"]
            })

    # internal links
    link_candidates = brief.get('internal_link_targets', [])

    outline = {
        "keyword": keyword,
        "intent": intent,
        "h1": h1,
        "meta_title_suggestion": _generate_meta_title(brief),
        "sections": outline_sections,
        "internal_link_candidates": link_candidates,
        "seo_notes": brief.get('seo_notes', []),
        "target_word_count": brief.get('target_word_count', '1000-1500'),
        "status": TaskStatus.OUTLINE_READY,
        "validation": _validate_outline(outline_sections, keyword)
    }

    return outline

def _generate_h1(brief: dict) -> str:
    """توليد H1 من Brief — لا من keyword مباشرة"""
    keyword = brief['keyword']
    content_type = brief['content_type']
    from datetime import datetime
    year = datetime.now().year

    # إزالة السنة من keyword إن وجدت لتجنب التكرار
    clean_keyword = keyword
    for y in ['2024', '2025', '2026', '2027']:
        clean_keyword = clean_keyword.replace(y, '').strip()

    if content_type == 'feasibility_study':
        return f"دراسة جدوى {clean_keyword}: الأرقام الحقيقية لعام {year}"
    elif content_type == 'price_guide':
        return f"{clean_keyword}: آخر الأسعار وكيف تختار الأفضل"
    elif content_type == 'how_to_guide':
        return f"كيف تبدأ {clean_keyword} من الصفر: دليل عملي"
    elif 'تربية' in keyword:
        animal = _extract_animal(keyword)
        return f"تربية {animal}: الدليل الشامل للمبتدئين والمحترفين {year}"
    else:
        return brief['recommended_title']

def _generate_meta_title(brief: dict) -> str:
    """توليد Meta Title مختصر بدون تكرار"""
    from datetime import datetime
    year = datetime.now().year
    keyword = brief['keyword']
    content_type = brief['content_type']

    # إزالة السنة من keyword
    clean = keyword
    for y in ['2024', '2025', '2026', '2027']:
        clean = clean.replace(y, '').strip()

    if content_type == 'price_guide':
        title = f"سعر {clean} {year} | دليل المشتري"
    elif content_type == 'feasibility_study':
        title = f"جدوى {clean} {year}: التكاليف والأرباح"
    else:
        title = f"{clean} {year}: دليل شامل"

    # تقليص إذا تجاوز 60 حرف
    if len(title) > 60:
        title = f"{clean} {year}"

    return title

def _extract_animal(keyword: str) -> str:
    animals = {
        'دجاج': 'الدجاج', 'دواجن': 'الدواجن', 'فروج': 'الفروج',
        'ماعز': 'الماعز', 'غنم': 'الغنم', 'خروف': 'الخروف',
        'بقر': 'الأبقار', 'ابل': 'الإبل', 'سمان': 'السمان',
        'ارانب': 'الأرانب'
    }
    for key, value in animals.items():
        if key in keyword.lower():
            return value
    return keyword

def _get_intro_notes(keyword: str, intent: str) -> str:
    if intent == 'informational':
        return f"ابدأ بسؤال يعكس مشكلة القارئ أو إحصائية مثيرة. اذكر '{keyword}' في أول جملتين. أخبر القارئ بما سيستفيده من المقال."
    elif intent == 'commercial':
        return f"ابدأ بالسياق الاقتصادي. اذكر '{keyword}' مع رقم أو إحصائية. وضّح لماذا هذه المعلومة مهمة الآن."
    else:
        return f"مقدمة واضحة تذكر '{keyword}' وتحدد هدف المقال."

def _get_section_notes(heading: str, intent: str) -> str:
    notes_map = {
        'أنواع': "اذكر 3-5 أنواع مع وصف مختصر لكل منها. استخدم جدولاً إذا كانت المقارنة مناسبة.",
        'تجهيز': "اشرح الخطوات العملية. استخدم قائمة مرقمة.",
        'تغذية': "اذكر الكميات والأنواع. استخدم جدولاً للكميات إذا أمكن.",
        'تكلفة': "قدّم أرقاماً حقيقية من السوق. فصّل بين التكاليف الثابتة والمتغيرة.",
        'الأخطاء': "اذكر 4-6 أخطاء شائعة مع كيفية تجنبها.",
        'الوضع في الجزائر': "أرقام وبيانات محلية فقط. أشر للمصدر إن أمكن.",
        'رعاية': "اشرح الرعاية اليومية والوقاية من الأمراض.",
        'مقارنة': "استخدم جدولاً للمقارنة.",
        'سعر': "أرقام محدثة. اذكر العوامل المؤثرة في السعر."
    }

    for key, note in notes_map.items():
        if key in heading:
            return note

    return f"اكتب محتوى عملياً ومفيداً عن: {heading}. استخدم قوائم أو جداول عند الحاجة."

def _get_h3_suggestions(heading: str, keyword: str) -> list:
    h3_map = {
        'أنواع وسلالات': ["السلالات المحلية", "السلالات المستوردة", "أيها أفضل للجزائر؟"],
        'تجهيز': ["المساحة المطلوبة", "التهوية والإضاءة", "معدات التربية الأساسية"],
        'التغذية والأعلاف': ["العلف في مرحلة النمو", "العلف في مرحلة الإنتاج", "الكميات اليومية"],
        'الرعاية الصحية': ["جدول التطعيم", "الأمراض الشائعة", "علامات الحيوان الصحي"],
        'التكاليف والأرباح': ["التكاليف الأولية", "التكاليف الشهرية", "العائد المتوقع"],
        'الأخطاء': []
    }

    for key, h3s in h3_map.items():
        if key in heading:
            return h3s

    return []

def _get_must_include(heading: str) -> list:
    must_map = {
        'أنواع': ["أسماء السلالات", "خصائص كل نوع"],
        'تجهيز': ["المساحة بالمتر", "قائمة المعدات"],
        'تكلفة': ["أرقام محددة", "مصدر الأرقام"],
        'الوضع في الجزائر': ["أرقام محلية", "مقارنة بالسنة السابقة"],
        'رعاية': ["جدول أو قائمة", "نصائح عملية"]
    }

    for key, must in must_map.items():
        if key in heading:
            return must

    return ["معلومات دقيقة", "أمثلة عملية"]

def _get_conclusion_notes(intent: str) -> str:
    if intent == 'informational':
        return "لخّص 3 نقاط رئيسية. اطرح سؤالاً للقارئ. اقترح مقالاً ذا صلة."
    elif intent == 'commercial':
        return "لخّص أهم العوامل في القرار. أضف توصية واضحة. اقترح الخطوة التالية."
    else:
        return "خاتمة مختصرة تلخص المحتوى وتوجّه القارئ."

def _validate_outline(sections: list, keyword: str) -> dict:
    """التحقق من صحة الـ Outline قبل تمريره للـ Writing"""
    issues = []
    warnings = []

    types = [s['type'] for s in sections]

    if 'introduction' not in types:
        issues.append("❌ المقدمة مفقودة")

    if 'conclusion' not in types:
        issues.append("❌ الخاتمة مفقودة")

    h2_sections = [s for s in sections if s['type'] == 'h2']
    if len(h2_sections) < 2:
        issues.append("❌ عدد الأقسام الرئيسية أقل من 2")

    if len(h2_sections) > 8:
        warnings.append("⚠️  عدد الأقسام كبير — قد يكون المقال طويلاً جداً")

    faq_sections = [s for s in sections if s['type'] == 'faq']
    if len(faq_sections) > 1:
        warnings.append("⚠️  أكثر من قسم FAQ — احتفظ بقسم واحد فقط")

    return {
        "is_valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "section_count": len(sections),
        "h2_count": len(h2_sections)
    }

def save_outline_to_db(task_id: int, outline: dict):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE content_tasks
        SET outline_data = ?, status = ?, updated_at = datetime('now')
        WHERE id = ?
    """, (
        json.dumps(outline, ensure_ascii=False),
        TaskStatus.OUTLINE_READY,
        task_id
    ))
    conn.commit()
    conn.close()

def print_outline_report(outline: dict):
    print("\n" + "=" * 55)
    print("     Outline Report")
    print("=" * 55)
    print(f"  الكلمة المفتاحية : {outline['keyword']}")
    print(f"  H1               : {outline['h1']}")
    print(f"  Meta Title       : {outline['meta_title_suggestion']}")
    print(f"  الطول المستهدف   : {outline['target_word_count']} كلمة")

    print(f"\n  الهيكل ({len(outline['sections'])} قسم):")
    for i, s in enumerate(outline['sections'], 1):
        prefix = {
            'introduction': '📝',
            'h2': '📌',
            'faq': '❓',
            'conclusion': '✅'
        }.get(s['type'], '•')
        label = s.get('h2') or s['type']
        print(f"    {prefix} {i}. {label}")
        if s.get('h3_suggestions'):
            for h3 in s['h3_suggestions']:
                print(f"         └─ {h3}")

    validation = outline['validation']
    print(f"\n  Validation:")
    print(f"    {'✅ Outline صالح' if validation['is_valid'] else '❌ Outline يحتوي مشاكل'}")
    for issue in validation['issues']:
        print(f"    {issue}")
    for warning in validation['warnings']:
        print(f"    {warning}")

    if outline['internal_link_candidates']:
        print(f"\n  روابط داخلية مقترحة ({len(outline['internal_link_candidates'])}):")
        for link in outline['internal_link_candidates']:
            print(f"    - {link['title'][:50]}...")

    print(f"\n  الحالة : {outline['status']}")
    print("=" * 55)

def run(keyword: str = None, task_id: int = None,
        brief: dict = None, intent_data: dict = None):

    if not brief:
        from agents.intent_agent import analyze
        from agents.content_brief import generate_brief

        if not keyword:
            keyword = input("أدخل الكلمة المفتاحية: ").strip()

        if not intent_data:
            intent_data, task_id = analyze(keyword)

        brief = generate_brief(intent_data)

    print(f"\n📐 جاري توليد Outline...")
    outline = build_outline_from_brief(brief)

    if task_id:
        save_outline_to_db(task_id, outline)

    print_outline_report(outline)
    return outline, task_id

if __name__ == "__main__":
    if len(sys.argv) > 1:
        kw = ' '.join(sys.argv[1:])
        run(keyword=kw)
    else:
        run()