import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import DB_PATH

# كلمات النيش الزراعي — ما يجب أن يظهر
NICHE_KEYWORDS = [
    'دجاج', 'دجاجة', 'دواجن', 'فروج', 'بروي',
    'ماعز', 'معزة', 'غنم', 'خروف', 'كبش', 'نعجة',
    'بقر', 'عجل', 'بقرة', 'ماشية', 'ابقار',
    'ابل', 'جمل', 'ناقة',
    'سمان', 'ارانب', 'ارنب',
    'علف', 'اعلاف', 'تغذية',
    'تربية', 'مشروع', 'جدوى', 'مزرعة',
    'حليب', 'بيض', 'لحم',
    'فلاحة', 'زراعة', 'زراعي',
    'سعر', 'اسعار', 'سوق',
    'مورسيانو', 'صانن', 'بلدي',
    'اضحية', 'اضاحي', 'عيد',
    'مساحة', 'حظيرة', 'قفص',
    'تطعيم', 'امراض', 'علاج',
    'هيدروبونيك', 'مائي', 'عضوي'
]

# كلمات خارج النيش — ما يجب استثناؤه
EXCLUDED_KEYWORDS = [
    'حج', 'حجاج', 'حجة', 'عمرة',
    'صلاة', 'زكاة', 'قرآن',
    'سياسة', 'انتخاب', 'رئيس',
    'كرة', 'رياضة', 'فيفا',
    'فيلم', 'مسلسل', 'نجم',
    'هاتف', 'جوال', 'تقنية'
]

def is_niche_keyword(keyword):
    """تحقق إن كانت الكلمة ضمن النيش الزراعي"""
    keyword_lower = keyword.lower()

    for excluded in EXCLUDED_KEYWORDS:
        if excluded in keyword_lower:
            return False

    for niche in NICHE_KEYWORDS:
        if niche in keyword_lower:
            return True

    return False

def calculate_opportunity_score(impressions, clicks, position, ctr):
    impression_score = min(impressions / 1000, 10)

    if 1 <= position <= 3:
        position_score = 3
    elif 4 <= position <= 10:
        position_score = 10
    elif 11 <= position <= 20:
        position_score = 7
    else:
        position_score = 2

    if ctr < 0.02 and impressions > 500:
        ctr_score = 8
    elif ctr < 0.05:
        ctr_score = 5
    else:
        ctr_score = 2

    total = (impression_score * 0.4) + (position_score * 0.4) + (ctr_score * 0.2)
    return round(total, 2)

def classify_opportunity(position, impressions, clicks, ctr):
    if position <= 10 and ctr < 0.02 and impressions > 200:
        return "تحسين Title/Meta"
    elif 4 <= position <= 15 and impressions > 100:
        return "تحسين مقال موجود"
    elif position > 15 and impressions > 100:
        return "تعزيز بروابط داخلية"
    elif impressions > 500 and clicks < 5:
        return "مقال جديد مستهدف"
    else:
        return "مراقبة"

def get_existing_articles():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT title, slug FROM articles WHERE status = 'published'")
    articles = cursor.fetchall()
    conn.close()
    return [(title.lower(), slug) for title, slug in articles]

def analyze_opportunities():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            query,
            SUM(clicks) as total_clicks,
            SUM(impressions) as total_impressions,
            ROUND(AVG(ctr), 4) as avg_ctr,
            ROUND(AVG(position), 1) as avg_position,
            COUNT(DISTINCT page) as pages_count
        FROM gsc_data
        GROUP BY query
        HAVING total_impressions >= 50
        ORDER BY total_impressions DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    opportunities = []
    articles = get_existing_articles()
    filtered_out = 0

    for row in rows:
        query, clicks, impressions, ctr, position, pages_count = row

        # تخطي الكلمات خارج النيش
        if not is_niche_keyword(query):
            filtered_out += 1
            continue

        score = calculate_opportunity_score(impressions, clicks, position, ctr)
        opp_type = classify_opportunity(position, impressions, clicks, ctr)

        has_article = any(
            query.lower() in title or any(word in title for word in query.lower().split())
            for title, slug in articles
        )

        opportunities.append({
            'query': query,
            'clicks': int(clicks),
            'impressions': int(impressions),
            'ctr': round(ctr * 100, 2),
            'position': position,
            'pages': pages_count,
            'score': score,
            'type': opp_type,
            'has_article': has_article
        })

    opportunities.sort(key=lambda x: x['score'], reverse=True)
    print(f"   تم تصفية {filtered_out} كلمة خارج النيش الزراعي")
    return opportunities

def save_opportunities_to_db(opportunities):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT,
            clicks INTEGER,
            impressions INTEGER,
            ctr REAL,
            position REAL,
            score REAL,
            type TEXT,
            has_article INTEGER,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cursor.execute("DELETE FROM opportunities")

    for opp in opportunities:
        cursor.execute("""
            INSERT INTO opportunities
            (query, clicks, impressions, ctr, position, score, type, has_article)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            opp['query'],
            opp['clicks'],
            opp['impressions'],
            opp['ctr'],
            opp['position'],
            opp['score'],
            opp['type'],
            1 if opp['has_article'] else 0
        ))

    conn.commit()
    conn.close()

def print_report(opportunities):
    print("=" * 60)
    print("     تقرير فرص المحتوى — Research Engine")
    print("=" * 60)

    title_fixes = [o for o in opportunities if o['type'] == "تحسين Title/Meta"][:5]
    if title_fixes:
        print(f"\n🎯 تحسين Title/Meta (نتائج سريعة):")
        for o in title_fixes:
            print(f"   [{o['score']}] {o['query']}")
            print(f"        موضع: {o['position']} | impressions: {o['impressions']:,} | CTR: {o['ctr']}%")

    improve = [o for o in opportunities if o['type'] == "تحسين مقال موجود"][:5]
    if improve:
        print(f"\n📈 تحسين مقالات موجودة:")
        for o in improve:
            print(f"   [{o['score']}] {o['query']}")
            print(f"        موضع: {o['position']} | impressions: {o['impressions']:,} | clicks: {o['clicks']}")

    new_articles = [o for o in opportunities if o['type'] == "مقال جديد مستهدف" and not o['has_article']][:5]
    if new_articles:
        print(f"\n📝 مقالات جديدة مقترحة:")
        for o in new_articles:
            print(f"   [{o['score']}] {o['query']}")
            print(f"        موضع: {o['position']} | impressions: {o['impressions']:,} | clicks: {o['clicks']}")

    links = [o for o in opportunities if o['type'] == "تعزيز بروابط داخلية"][:5]
    if links:
        print(f"\n🔗 تعزيز بروابط داخلية:")
        for o in links:
            print(f"   [{o['score']}] {o['query']}")
            print(f"        موضع: {o['position']} | impressions: {o['impressions']:,}")

    print(f"\n📊 الإجماليات:")
    print(f"   - إجمالي الفرص ضمن النيش: {len(opportunities)}")
    print(f"   - فرص التحسين السريع: {len(title_fixes)}")
    print(f"   - مقالات تحتاج تحسين: {len(improve)}")
    print(f"   - مقالات جديدة مقترحة: {len(new_articles)}")

    print("\n" + "=" * 60)
    print("✅ تم حفظ جميع الفرص في قاعدة البيانات")
    print("=" * 60)

def run():
    print("جاري تحليل بيانات Search Console...")
    opportunities = analyze_opportunities()
    save_opportunities_to_db(opportunities)
    print_report(opportunities)

if __name__ == "__main__":
    run()