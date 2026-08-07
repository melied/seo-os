import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import DB_PATH

def run():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("=" * 50)
    print("       تقرير الموقع — SEO Operating System")
    print("=" * 50)

    # إجمالي المقالات
    cursor.execute("SELECT COUNT(*) FROM articles WHERE status = 'published'")
    total_articles = cursor.fetchone()[0]
    print(f"\n📄 إجمالي المقالات: {total_articles}")

    # التصنيفات
    cursor.execute("""
        SELECT keyword, COUNT(*) as count
        FROM articles
        WHERE keyword IS NOT NULL AND keyword != ''
        GROUP BY keyword
        ORDER BY count DESC
        LIMIT 10
    """)
    categories = cursor.fetchall()
    if categories:
        print(f"\n📂 التصنيفات:")
        for cat, count in categories:
            print(f"   - {cat}: {count} مقال")

    # إجمالي بيانات GSC
    cursor.execute("SELECT COUNT(*) FROM gsc_data")
    total_gsc = cursor.fetchone()[0]
    print(f"\n🔍 بيانات Search Console: {total_gsc} صف")

    # إجمالي الكلمات المفتاحية الفريدة
    cursor.execute("SELECT COUNT(DISTINCT query) FROM gsc_data")
    total_queries = cursor.fetchone()[0]
    print(f"   - كلمات مفتاحية فريدة: {total_queries}")

    # إجمالي الصفحات
    cursor.execute("SELECT COUNT(DISTINCT page) FROM gsc_data")
    total_pages = cursor.fetchone()[0]
    print(f"   - صفحات مفهرسة: {total_pages}")

    # إجمالي الـ clicks والـ impressions
    cursor.execute("SELECT SUM(clicks), SUM(impressions) FROM gsc_data")
    row = cursor.fetchone()
    total_clicks = int(row[0] or 0)
    total_impressions = int(row[1] or 0)
    avg_ctr = round((total_clicks / total_impressions * 100), 2) if total_impressions > 0 else 0
    print(f"   - إجمالي الـ Clicks: {total_clicks:,}")
    print(f"   - إجمالي الـ Impressions: {total_impressions:,}")
    print(f"   - متوسط الـ CTR: {avg_ctr}%")

    # أفضل 5 صفحات بالـ clicks
    cursor.execute("""
        SELECT page, SUM(clicks) as total_clicks, SUM(impressions) as total_impressions
        FROM gsc_data
        GROUP BY page
        ORDER BY total_clicks DESC
        LIMIT 5
    """)
    top_pages = cursor.fetchall()
    print(f"\n🏆 أفضل 5 صفحات (Clicks):")
    for page, clicks, impressions in top_pages:
        slug = page.rstrip('/').split('/')[-1].replace('.html', '')
        print(f"   - {slug}")
        print(f"     clicks: {clicks:,} | impressions: {impressions:,}")

    # أفضل 5 كلمات بالـ impressions
    cursor.execute("""
        SELECT query, SUM(clicks) as total_clicks, SUM(impressions) as total_impressions,
               ROUND(AVG(position), 1) as avg_position
        FROM gsc_data
        GROUP BY query
        ORDER BY total_impressions DESC
        LIMIT 5
    """)
    top_queries = cursor.fetchall()
    print(f"\n🔑 أعلى 5 كلمات بالـ Impressions:")
    for query, clicks, impressions, position in top_queries:
        print(f"   - {query}")
        print(f"     clicks: {clicks} | impressions: {impressions:,} | موضع: {position}")

    # فرص سريعة — كلمات في موضع 4-20
    cursor.execute("""
        SELECT query, SUM(clicks) as total_clicks, SUM(impressions) as total_impressions,
               ROUND(AVG(position), 1) as avg_position
        FROM gsc_data
        GROUP BY query
        HAVING avg_position BETWEEN 4 AND 20
           AND total_impressions > 100
        ORDER BY total_impressions DESC
        LIMIT 10
    """)
    opportunities = cursor.fetchall()
    print(f"\n💡 فرص سريعة (موضع 4-20، impressions > 100):")
    for query, clicks, impressions, position in opportunities:
        print(f"   - {query}")
        print(f"     موضع: {position} | impressions: {impressions:,} | clicks: {clicks}")

    # صفحات بـ impressions عالية وclicks منخفضة
    cursor.execute("""
        SELECT query, SUM(clicks) as total_clicks, SUM(impressions) as total_impressions,
               ROUND(AVG(ctr)*100, 2) as avg_ctr
        FROM gsc_data
        GROUP BY query
        HAVING total_impressions > 200 AND avg_ctr < 2.0
        ORDER BY total_impressions DESC
        LIMIT 5
    """)
    low_ctr = cursor.fetchall()
    print(f"\n⚠️  كلمات بـ CTR منخفض (تحتاج تحسين Title/Meta):")
    for query, clicks, impressions, ctr in low_ctr:
        print(f"   - {query}")
        print(f"     CTR: {ctr}% | impressions: {impressions:,} | clicks: {clicks}")

    print("\n" + "=" * 50)
    print("✅ انتهى التقرير")
    print("=" * 50)

    conn.close()

if __name__ == "__main__":
    run()