import sqlite3
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import DB_PATH
from agents.intent_agent import TaskStatus, SearchIntent

def get_existing_articles_for_keyword(keyword: str) -> list:
    """البحث عن مقالات موجودة قريبة من الكلمة المفتاحية"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    words = [w for w in keyword.split() if len(w) > 3]
    results = []

    for word in words:
        cursor.execute("""
            SELECT title, slug, keyword, status
            FROM articles
            WHERE (title LIKE ? OR keyword LIKE ?)
            AND status = 'published'
            LIMIT 5
        """, (f'%{word}%', f'%{word}%'))
        results.extend(cursor.fetchall())

    conn.close()

    seen = []
    unique = []
    for r in results:
        if r[1] not in seen:
            seen.append(r[1])
            unique.append({
                'title': r[0],
                'slug': r[1],
                'keyword': r[2],
                'status': r[3]
            })

    return unique[:5]

def check_content_gap(keyword: str, existing: list) -> dict:
    """تحديد الفجوة بين الكلمة المفتاحية والمحتوى الموجود"""
    keyword_lower = keyword.lower()

    # هل يوجد مقال مباشر؟
    direct_match = any(
        keyword_lower in a['title'].lower() or
        a['title'].lower() in keyword_lower
        for a in existing
    )

    # هل يوجد مقال قريب؟
    partial_match = len(existing) > 0 and not direct_match

    if direct_match:
        gap_type = "no_gap"
        recommendation = "improve_existing"
        gap_description = "يوجد مقال مباشر — يُنصح بتحسين المقال الموجود بدلاً من إنشاء جديد"
    elif partial_match:
        gap_type = "partial_gap"
        recommendation = "create_new_targeted"
        gap_description = f"يوجد {len(existing)} مقال قريب — يمكن إنشاء مقال جديد أكثر تخصصاً"
    else:
        gap_type = "full_gap"
        recommendation = "create_new"
        gap_description = "لا يوجد محتوى مغطٍّ لهذا الموضوع — فرصة لإنشاء مقال جديد"

    return {
        "gap_type": gap_type,
        "recommendation": recommendation,
        "gap_description": gap_description,
        "existing_count": len(existing),
        "direct_match": direct_match
    }

def get_internal_link_candidates(keyword: str, existing: list) -> list:
    """تحديد مقالات مناسبة للربط الداخلي بناءً على الصلة الموضوعية"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    keyword_lower = keyword.lower()
    candidates = []

    # كلمات الصلة الموضوعية
    topic_map = {
        'دجاج': ['دواجن', 'كتكوت', 'بروي', 'بياض', 'علف دجاج', 'فروج'],
        'دواجن': ['دجاج', 'كتكوت', 'بروي', 'سمان'],
        'ماعز': ['معزة', 'مورسيانو', 'صانن', 'حليب ماعز'],
        'غنم': ['خروف', 'كبش', 'نعجة', 'اضحية'],
        'علف': ['تغذية', 'اعلاف', 'كمية علف'],
        'مشروع': ['جدوى', 'تكلفة', 'ربح', 'استثمار'],
        'سعر': ['تكلفة', 'اسعار', 'سوق']
    }

    related_terms = []
    for topic, terms in topic_map.items():
        if topic in keyword_lower:
            related_terms.extend(terms)

    # أضف الكلمات الموجودة في existing
    for article in existing:
        if article['slug'] not in [c.get('slug') for c in candidates]:
            candidates.append({
                'title': article['title'],
                'slug': article['slug'],
                'relevance': 'direct'
            })

    # ابحث بالمصطلحات المرتبطة
    for term in related_terms[:3]:
        cursor.execute("""
            SELECT title, slug FROM articles
            WHERE title LIKE ? AND status = 'published'
            LIMIT 2
        """, (f'%{term}%',))
        rows = cursor.fetchall()
        for title, slug in rows:
            if slug not in [c.get('slug') for c in candidates]:
                candidates.append({
                    'title': title,
                    'slug': slug,
                    'relevance': 'topical'
                })

    conn.close()
    return candidates[:4]

def build_recommended_sections(intent_data: dict) -> list:
    """بناء الأقسام المقترحة بناءً على Intent والموضوعات الفرعية"""
    intent = intent_data['search_intent']
    content_type = intent_data['content_type']
    subtopics = intent_data['important_subtopics']
    keyword = intent_data['primary_keyword']
    is_local = intent_data['is_local']

    sections = []

    # المقدمة دائماً أولاً
    sections.append({
        "type": "introduction",
        "purpose": f"تعريف بالموضوع وذكر الكلمة المفتاحية في أول 50 كلمة",
        "word_count": "100-150"
    })

    # أقسام من الموضوعات الفرعية
    for subtopic in subtopics:
        sections.append({
            "type": "h2",
            "heading": subtopic,
            "purpose": f"تغطية موضوع: {subtopic}",
            "word_count": "150-250"
        })

    # قسم محلي إذا كان الموضوع محلياً
    if is_local and content_type in ['price_guide', 'feasibility_study', 'informational_article']:
        local_section = {
            "type": "h2",
            "heading": f"الوضع في الجزائر",
            "purpose": "بيانات وأرقام محلية حقيقية",
            "word_count": "150-200"
        }
        # أضفه قبل الأسئلة الشائعة
        sections.append(local_section)

    # أسئلة شائعة فقط إذا كان هناك مبرر
    if intent == SearchIntent.INFORMATIONAL and len(intent_data['questions']) >= 3:
        sections.append({
            "type": "faq",
            "purpose": "الإجابة على الأسئلة الأكثر بحثاً",
            "questions": intent_data['questions'][:5],
            "word_count": "50-100 لكل سؤال"
        })

    # الخاتمة دائماً أخيراً
    sections.append({
        "type": "conclusion",
        "purpose": "تلخيص النقاط الرئيسية وتوجيه القارئ للخطوة التالية",
        "word_count": "80-120"
    })

    return sections

def generate_brief(intent_data: dict) -> dict:
    """توليد Content Brief كامل من Intent Analysis"""
    keyword = intent_data['primary_keyword']

    # فحص المحتوى الموجود
    existing = get_existing_articles_for_keyword(keyword)
    content_gap = check_content_gap(keyword, existing)

    # مرشحو الروابط الداخلية
    link_candidates = get_internal_link_candidates(keyword, existing)

    # الأقسام المقترحة
    sections = build_recommended_sections(intent_data)

    # متطلبات الـ Freshness
    freshness_requirements = []
    if intent_data['freshness_required']:
        from datetime import datetime
        year = datetime.now().year
        freshness_requirements = [
            f"اذكر السنة {year} في العنوان",
            "أضف تاريخ آخر تحديث",
            "تحقق من دقة الأسعار والأرقام",
            "أشر إلى مصدر البيانات"
        ]

    # حساب الطول المستهدف
    target_length = _get_target_length(intent_data['content_type'])

    brief = {
        "keyword": keyword,
        "intent": intent_data['search_intent'],
        "content_type": intent_data['content_type'],
        "audience": _get_audience(intent_data),
        "recommended_title": _get_recommended_title(intent_data),
        "sections": sections,
        "questions_to_answer": intent_data['questions'],
        "entities": _get_entities(keyword),
        "internal_link_targets": link_candidates,
        "freshness_requirements": freshness_requirements,
        "target_word_count": target_length,
        "content_gap": content_gap,
        "existing_articles": existing,
        "seo_notes": _get_seo_notes(intent_data),
        "status": TaskStatus.BRIEF_READY
    }

    return brief

def _get_audience(intent_data: dict) -> str:
    keyword = intent_data['primary_keyword'].lower()
    is_local = intent_data['is_local']
    location = "في الجزائر" if is_local else "في المغرب العربي"

    if 'مبتدئ' in keyword or 'كيف' in keyword:
        return f"المبتدئون الراغبون في بدء مشروع {location}"
    elif 'مشروع' in keyword or 'جدوى' in keyword:
        return f"أصحاب المشاريع الصغيرة والمستثمرون {location}"
    elif 'سعر' in keyword or 'تكلفة' in keyword:
        return f"المربون وأصحاب المزارع {location}"
    else:
        return f"مربو الماشية والمزارعون {location}"

def _get_recommended_title(intent_data: dict) -> str:
    keyword = intent_data['primary_keyword']
    content_type = intent_data['content_type']
    from datetime import datetime
    year = datetime.now().year

    if content_type == 'feasibility_study':
        base = keyword.replace('دراسة جدوى', '').strip()
        return f"دراسة جدوى {base}: التكاليف والأرباح الحقيقية {year}"
    elif content_type == 'price_guide':
        return f"{keyword}: آخر الأسعار ومقارنة السوق {year}"
    elif content_type == 'how_to_guide':
        return f"كيف تبدأ {keyword}: دليل شامل خطوة بخطوة"
    else:
        return f"{keyword}: دليل شامل {year}"

def _get_target_length(content_type: str) -> str:
    lengths = {
        'feasibility_study':    '1500-2000',
        'price_guide':          '800-1200',
        'how_to_guide':         '1200-1800',
        'comparison':           '1000-1500',
        'informational_article': '1000-1500',
        'commercial_guide':     '1200-1800',
        'general_article':      '800-1200'
    }
    return lengths.get(content_type, '1000-1500')

def _get_entities(keyword: str) -> list:
    keyword_lower = keyword.lower()
    entities = []

    entity_map = {
        'دجاج': ['وزارة الفلاحة الجزائرية', 'أسواق الدواجن', 'سلالات الدجاج'],
        'ماعز': ['ماعز المورسيانو', 'ماعز الصانن', 'أسواق الماشية'],
        'غنم': ['خروف الرملي', 'خروف الأوراسي', 'أسواق الأغنام'],
        'علف': ['أعلاف مركبة', 'ذرة صفراء', 'صوجا'],
        'مشروع': ['دعم الدولة', 'قروض الفلاحة', 'ANSEJ', 'CNAC']
    }

    for topic, ents in entity_map.items():
        if topic in keyword_lower:
            entities.extend(ents)

    return entities[:5]

def _get_seo_notes(intent_data: dict) -> list:
    notes = [
        f"الكلمة المفتاحية في الـ H1 وأول 50 كلمة",
        f"Meta Title بين 55-60 حرف",
        f"Meta Description بين 140-155 حرف",
        f"Slug بالإنجليزية 3-5 كلمات"
    ]

    if intent_data['freshness_required']:
        from datetime import datetime
        notes.append(f"أضف سنة {datetime.now().year} في العنوان")

    if intent_data['is_local']:
        notes.append("اذكر 'الجزائر' في Meta Title أو Description")

    if intent_data['content_type'] == 'price_guide':
        notes.append("أضف Schema من نوع Article (لا FAQPage إلا إذا وجد FAQ حقيقي)")

    return notes

def save_brief_to_db(task_id: int, brief: dict):
    """حفظ الـ Brief في قاعدة البيانات"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE content_tasks
        SET brief_data = ?, status = ?, updated_at = datetime('now')
        WHERE id = ?
    """, (
        json.dumps(brief, ensure_ascii=False),
        TaskStatus.BRIEF_READY,
        task_id
    ))

    conn.commit()
    conn.close()

def print_brief_report(brief: dict):
    print("\n" + "=" * 55)
    print("     Content Brief Report")
    print("=" * 55)
    print(f"  الكلمة المفتاحية  : {brief['keyword']}")
    print(f"  Intent            : {brief['intent']}")
    print(f"  نوع المحتوى       : {brief['content_type']}")
    print(f"  الجمهور           : {brief['audience']}")
    print(f"  العنوان المقترح   : {brief['recommended_title']}")
    print(f"  الطول المستهدف    : {brief['target_word_count']} كلمة")

    print(f"\n  Content Gap:")
    print(f"    النوع           : {brief['content_gap']['gap_type']}")
    print(f"    التوصية         : {brief['content_gap']['recommendation']}")
    print(f"    الوصف           : {brief['content_gap']['gap_description']}")

    print(f"\n  الأقسام المقترحة ({len(brief['sections'])}):")
    for i, s in enumerate(brief['sections'], 1):
        heading = s.get('heading', s.get('type', ''))
        print(f"    {i}. {heading} ({s['type']})")

    if brief['internal_link_targets']:
        print(f"\n  مرشحو الروابط الداخلية ({len(brief['internal_link_targets'])}):")
        for link in brief['internal_link_targets']:
            print(f"    - {link['title'][:50]}... [{link['relevance']}]")

    if brief['entities']:
        print(f"\n  الكيانات المهمة:")
        for e in brief['entities']:
            print(f"    - {e}")

    if brief['seo_notes']:
        print(f"\n  ملاحظات SEO:")
        for note in brief['seo_notes']:
            print(f"    ✓ {note}")

    print(f"\n  الحالة            : {brief['status']}")
    print("=" * 55)

def run(keyword: str = None, task_id: int = None, intent_data: dict = None):
    """
    توليد Content Brief
    يمكن استدعاؤه مباشرة أو من pipeline
    """
    if not intent_data:
        from agents.intent_agent import analyze
        if not keyword:
            keyword = input("أدخل الكلمة المفتاحية: ").strip()
        intent_data, task_id = analyze(keyword)

    print(f"\n📋 جاري توليد Content Brief...")
    brief = generate_brief(intent_data)

    if task_id:
        save_brief_to_db(task_id, brief)

    print_brief_report(brief)
    return brief, task_id

if __name__ == "__main__":
    if len(sys.argv) > 1:
        kw = ' '.join(sys.argv[1:])
        run(keyword=kw)
    else:
        run()