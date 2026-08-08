import sqlite3
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import DB_PATH

# أنواع الـ Intent
class SearchIntent:
    INFORMATIONAL  = "informational"
    COMMERCIAL     = "commercial"
    TRANSACTIONAL  = "transactional"
    NAVIGATIONAL   = "navigational"
    MIXED          = "mixed"

# حالات المهمة
class TaskStatus:
    PLANNED          = "PLANNED"
    RESEARCHING      = "RESEARCHING"
    BRIEF_READY      = "BRIEF_READY"
    OUTLINE_READY    = "OUTLINE_READY"
    WRITING          = "WRITING"
    SEO_OPTIMIZATION = "SEO_OPTIMIZATION"
    QUALITY_CHECK    = "QUALITY_CHECK"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    APPROVED         = "APPROVED"
    PUBLISHED        = "PUBLISHED"
    AI_UNAVAILABLE   = "AI_UNAVAILABLE"
    FAILED           = "FAILED"

# مؤشرات الـ Intent (بدون AI)
INFORMATIONAL_SIGNALS = [
    'كيف', 'ما هو', 'ما هي', 'لماذا', 'متى', 'أين',
    'طريقة', 'شرح', 'دليل', 'تعلم', 'مبتدئ',
    'فوائد', 'أنواع', 'مراحل', 'خطوات', 'نصائح',
    'تربية', 'زراعة', 'تغذية', 'رعاية', 'علاج'
]

COMMERCIAL_SIGNALS = [
    'سعر', 'اسعار', 'تكلفة', 'ميزانية', 'مقارنة',
    'افضل', 'مراجعة', 'تقييم', 'يستحق', 'جدوى',
    'مشروع', 'ربح', 'دراسة', 'استثمار'
]

TRANSACTIONAL_SIGNALS = [
    'شراء', 'بيع', 'للبيع', 'اشتري', 'طلب',
    'توصيل', 'متجر', 'سوق', 'اين اجد'
]

FRESHNESS_SIGNALS = [
    '2024', '2025', '2026', '2027',
    'الان', 'اليوم', 'الجديد', 'محدث', 'اخر'
]

LOCAL_SIGNALS = [
    'الجزائر', 'جزائر', 'المغرب', 'تونس', 'ليبيا',
    'السعودية', 'مصر', 'الخليج', 'العراق'
]

def detect_intent(keyword: str) -> dict:
    """
    تحليل الـ Search Intent من الكلمة المفتاحية بدون AI
    """
    keyword_lower = keyword.lower()
    words = keyword_lower.split()

    scores = {
        SearchIntent.INFORMATIONAL:  0,
        SearchIntent.COMMERCIAL:     0,
        SearchIntent.TRANSACTIONAL:  0,
        SearchIntent.NAVIGATIONAL:   0
    }

    for signal in INFORMATIONAL_SIGNALS:
        if signal in keyword_lower:
            scores[SearchIntent.INFORMATIONAL] += 2

    for signal in COMMERCIAL_SIGNALS:
        if signal in keyword_lower:
            scores[SearchIntent.COMMERCIAL] += 2

    for signal in TRANSACTIONAL_SIGNALS:
        if signal in keyword_lower:
            scores[SearchIntent.TRANSACTIONAL] += 2

    # تحديد الـ Intent الأساسي
    max_score = max(scores.values())

    if max_score == 0:
        primary_intent = SearchIntent.INFORMATIONAL
    else:
        # عدد الـ intents التي لها نفس الـ score الأعلى
        top_intents = [k for k, v in scores.items() if v == max_score]
        if len(top_intents) > 1:
            primary_intent = SearchIntent.MIXED
        else:
            primary_intent = top_intents[0]

    # تحديد نوع المحتوى المناسب
    content_type = _get_content_type(primary_intent, keyword_lower)

    # تحديد هدف المستخدم
    user_goal = _get_user_goal(primary_intent, keyword_lower)

    # الموضوعات الفرعية المقترحة
    subtopics = _get_subtopics(keyword_lower, primary_intent)

    # أسئلة مقترحة
    questions = _get_questions(keyword_lower, primary_intent)

    # هل تحتاج freshness؟
    freshness_required = any(s in keyword_lower for s in FRESHNESS_SIGNALS)

    # هل هي محلية؟
    is_local = any(s in keyword_lower for s in LOCAL_SIGNALS)

    # الزاوية التجارية
    commercial_angle = ""
    if primary_intent in [SearchIntent.COMMERCIAL, SearchIntent.MIXED]:
        commercial_angle = _get_commercial_angle(keyword_lower)

    return {
        "primary_keyword":    keyword,
        "search_intent":      primary_intent,
        "intent_scores":      scores,
        "user_goal":          user_goal,
        "content_type":       content_type,
        "important_subtopics": subtopics,
        "questions":          questions,
        "commercial_angle":   commercial_angle,
        "freshness_required": freshness_required,
        "is_local":           is_local,
        "status":             TaskStatus.RESEARCHING
    }

def _get_content_type(intent: str, keyword: str) -> str:
    if 'دراسة جدوى' in keyword or 'مشروع' in keyword:
        return "feasibility_study"
    elif 'سعر' in keyword or 'اسعار' in keyword or 'تكلفة' in keyword:
        return "price_guide"
    elif 'دليل' in keyword or 'كيف' in keyword or 'طريقة' in keyword:
        return "how_to_guide"
    elif 'مقارنة' in keyword or 'افضل' in keyword:
        return "comparison"
    elif intent == SearchIntent.INFORMATIONAL:
        return "informational_article"
    elif intent == SearchIntent.COMMERCIAL:
        return "commercial_guide"
    else:
        return "general_article"

def _get_user_goal(intent: str, keyword: str) -> str:
    if 'تربية' in keyword:
        return "يريد تعلم كيفية تربية الحيوانات أو إنشاء مشروع تربية"
    elif 'سعر' in keyword or 'تكلفة' in keyword:
        return "يريد معرفة الأسعار والتكاليف قبل اتخاذ قرار"
    elif 'مشروع' in keyword or 'جدوى' in keyword:
        return "يريد تقييم جدوى مشروع زراعي أو حيواني"
    elif 'علاج' in keyword or 'مرض' in keyword:
        return "يبحث عن حل لمشكلة صحية عند الحيوانات"
    elif intent == SearchIntent.INFORMATIONAL:
        return "يريد فهم موضوع معين والحصول على معلومات"
    elif intent == SearchIntent.COMMERCIAL:
        return "يريد مقارنة الخيارات واتخاذ قرار شراء أو استثمار"
    else:
        return "يبحث عن معلومات عامة"

def _get_subtopics(keyword: str, intent: str) -> list:
    subtopics = []

    if 'دجاج' in keyword or 'دواجن' in keyword:
        subtopics = [
            "أنواع وسلالات الدجاج",
            "تجهيز المكان والحظيرة",
            "التغذية والأعلاف",
            "الرعاية الصحية والتطعيم",
            "التكاليف والأرباح",
            "الأخطاء الشائعة"
        ]
    elif 'ماعز' in keyword:
        subtopics = [
            "أنواع الماعز",
            "التغذية والرعاية",
            "الإنتاج (حليب أو لحم)",
            "الأمراض والعلاج",
            "التكاليف والأسعار"
        ]
    elif 'غنم' in keyword or 'خروف' in keyword:
        subtopics = [
            "اختيار السلالة المناسبة",
            "التغذية والرعاية",
            "التكاثر والتوليد",
            "الأمراض الشائعة",
            "التكاليف والأسعار"
        ]
    elif 'علف' in keyword or 'تغذية' in keyword:
        subtopics = [
            "أنواع الأعلاف",
            "الكميات المطلوبة",
            "الأسعار في السوق",
            "كيفية تقليل تكاليف العلف"
        ]

    if intent == SearchIntent.COMMERCIAL and not subtopics:
        subtopics = [
            "متطلبات البداية",
            "التكاليف الأولية",
            "العائد المتوقع",
            "المخاطر والتحديات"
        ]

    return subtopics

def _get_questions(keyword: str, intent: str) -> list:
    questions = []

    if 'تربية' in keyword and 'دجاج' in keyword:
        questions = [
            "كم يكلف إنشاء مشروع تربية الدجاج في الجزائر؟",
            "ما هي أفضل سلالة للتربية في الجزائر؟",
            "كيف أجهز الحظيرة المناسبة؟",
            "ما هي الأمراض الشائعة وكيف أتجنبها؟",
            "هل تربية الدجاج مربحة في الجزائر؟"
        ]
    elif 'سعر' in keyword or 'تكلفة' in keyword:
        questions = [
            f"كم يبلغ سعر {keyword.replace('سعر', '').replace('تكلفة', '').strip()} حالياً؟",
            "هل الأسعار مستقرة أم في ارتفاع؟",
            "أين أجد أفضل سعر؟"
        ]
    else:
        questions = [
            f"ما هي أهمية {keyword}؟",
            f"كيف أبدأ في {keyword}؟",
            f"ما هي تكلفة {keyword} في الجزائر؟"
        ]

    return questions

def _get_commercial_angle(keyword: str) -> str:
    if 'مشروع' in keyword or 'جدوى' in keyword:
        return "دراسة جدوى اقتصادية مع أرقام حقيقية من السوق الجزائري"
    elif 'سعر' in keyword or 'تكلفة' in keyword:
        return "مقارنة الأسعار وتحديد أفضل قيمة مقابل التكلفة"
    else:
        return "تقييم الجدوى الاقتصادية"

def save_intent_to_db(intent_data: dict) -> int:
    """حفظ نتيجة تحليل الـ Intent في قاعدة البيانات"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS content_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL,
            search_intent TEXT,
            content_type TEXT,
            user_goal TEXT,
            subtopics TEXT,
            questions TEXT,
            commercial_angle TEXT,
            freshness_required INTEGER DEFAULT 0,
            is_local INTEGER DEFAULT 0,
            status TEXT DEFAULT 'PLANNED',
            intent_data TEXT,
            brief_data TEXT,
            outline_data TEXT,
            article_path TEXT,
            quality_report TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cursor.execute("""
        INSERT INTO content_tasks
        (keyword, search_intent, content_type, user_goal, subtopics,
         questions, commercial_angle, freshness_required, is_local, status, intent_data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        intent_data['primary_keyword'],
        intent_data['search_intent'],
        intent_data['content_type'],
        intent_data['user_goal'],
        json.dumps(intent_data['important_subtopics'], ensure_ascii=False),
        json.dumps(intent_data['questions'], ensure_ascii=False),
        intent_data['commercial_angle'],
        1 if intent_data['freshness_required'] else 0,
        1 if intent_data['is_local'] else 0,
        TaskStatus.RESEARCHING,
        json.dumps(intent_data, ensure_ascii=False)
    ))

    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return task_id

def analyze(keyword: str, save: bool = True) -> tuple:
    """
    تحليل الـ Intent للكلمة المفتاحية
    يعيد: (intent_data, task_id)
    """
    intent_data = detect_intent(keyword)
    task_id = None

    if save:
        task_id = save_intent_to_db(intent_data)

    return intent_data, task_id

def print_intent_report(intent_data: dict, task_id: int = None):
    print("\n" + "=" * 55)
    print("     Intent Analysis Report")
    print("=" * 55)
    print(f"  الكلمة المفتاحية : {intent_data['primary_keyword']}")
    print(f"  Search Intent    : {intent_data['search_intent']}")
    print(f"  نوع المحتوى      : {intent_data['content_type']}")
    print(f"  هدف المستخدم     : {intent_data['user_goal']}")
    print(f"  Freshness        : {'مطلوبة ✅' if intent_data['freshness_required'] else 'غير مطلوبة'}")
    print(f"  محلي             : {'نعم ✅' if intent_data['is_local'] else 'لا'}")

    if intent_data['important_subtopics']:
        print(f"\n  الموضوعات الفرعية:")
        for s in intent_data['important_subtopics']:
            print(f"    - {s}")

    if intent_data['questions']:
        print(f"\n  الأسئلة المقترحة:")
        for q in intent_data['questions']:
            print(f"    ؟ {q}")

    if intent_data['commercial_angle']:
        print(f"\n  الزاوية التجارية : {intent_data['commercial_angle']}")

    if task_id:
        print(f"\n  Task ID          : {task_id}")

    print("=" * 55)

def run(keyword: str = None):
    if not keyword:
        keyword = input("أدخل الكلمة المفتاحية: ").strip()
    if not keyword:
        print("❌ الكلمة المفتاحية فارغة")
        return None, None

    print(f"\n🔍 جاري تحليل Intent لـ: {keyword}")
    intent_data, task_id = analyze(keyword)
    print_intent_report(intent_data, task_id)
    return intent_data, task_id

if __name__ == "__main__":
    if len(sys.argv) > 1:
        kw = ' '.join(sys.argv[1:])
        run(keyword=kw)
    else:
        run()