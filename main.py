import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def print_header():
    print("\n" + "=" * 60)
    print("  SEO Operating System")
    print("  news-theworld.com")
    print("=" * 60)

def print_menu():
    print("\nCONTENT\n")
    print("  [1]  Sync Website Data")
    print("  [2]  Site SEO Report")
    print("  [3]  Find Content Opportunities")
    print("  [4]  Analyze Keyword")
    print("  [5]  Generate Content Brief")
    print("  [6]  Generate Outline")
    print("  [7]  Generate Full Article")
    print("  [8]  Run Full SEO Pipeline")
    print("\nREVIEW & PUBLISH\n")
    print("  [9]  Human Approval")
    print("  [10] Blogger Draft")
    print("\nMONITORING\n")
    print("  [11] GSC Performance")
    print("  [12] Find Declining Pages")
    print("  [13] Find Rising Pages")
    print("  [14] Internal Linking Opportunities")
    print("\nSYSTEM\n")
    print("  [15] System Status")
    print("  [16] AI Provider Status")
    print("  [17] Database Status")
    print("\n  [0]  Exit")
    print()

# ======================================================
# CONTENT
# ======================================================

def cmd_sync_data():
    from agents.blogger_connector import run as blogger_run
    from agents.gsc_connector import run as gsc_run
    from agents.sitemap_parser import run as sitemap_run
    print("\n📡 Syncing Website Data...\n")
    blogger_run()
    print()
    gsc_run()
    print()
    sitemap_run()

def cmd_site_report():
    from agents.site_report import run as report_run
    report_run()

def cmd_content_opportunities():
    from agents.research_engine import run as research_run
    research_run()

def cmd_analyze_keyword():
    keyword = input("\n  الكلمة المفتاحية: ").strip()
    if not keyword:
        print("  ❌ الكلمة المفتاحية فارغة")
        return
    from agents.intent_agent import run as intent_run
    intent_run(keyword=keyword)

def cmd_content_brief():
    keyword = input("\n  الكلمة المفتاحية: ").strip()
    if not keyword:
        print("  ❌ الكلمة المفتاحية فارغة")
        return
    from agents.content_brief import run as brief_run
    brief_run(keyword=keyword)

def cmd_outline():
    keyword = input("\n  الكلمة المفتاحية: ").strip()
    if not keyword:
        print("  ❌ الكلمة المفتاحية فارغة")
        return
    from agents.outline_generator import run as outline_run
    outline_run(keyword=keyword)

def cmd_full_article():
    keyword = input("\n  الكلمة المفتاحية: ").strip()
    if not keyword:
        print("  ❌ الكلمة المفتاحية فارغة")
        return
    from agents.writing_engine import run as writing_run
    writing_run(keyword=keyword)

def cmd_pipeline():
    keyword = input("\n  الكلمة المفتاحية: ").strip()
    if not keyword:
        print("  ❌ الكلمة المفتاحية فارغة")
        return
    from agents.pipeline import run_pipeline
    result = run_pipeline(keyword)

    from agents.intent_agent import TaskStatus
    status = result.get('status', 'UNKNOWN')

    print("\n" + "=" * 60)
    print("  SEO PIPELINE — FINAL STATUS")
    print("=" * 60)
    print(f"  Keyword: {keyword}\n")

    stages = result.get('stages_completed', [])
    stage_labels = {
        'intent':                  ('✓', 'Intent Analysis'),
        'brief':                   ('✓', 'Content Brief'),
        'outline':                 ('✓', 'Outline'),
        'article_ai':              ('✓', 'Full Article (AI)'),
        'seo':                     ('✓', 'SEO Optimization'),
        'quality_gate':            ('✓', 'Quality Gate'),
        'brief_and_outline_saved': ('⚠', 'Brief + Outline saved (no AI)')
    }

    for key, (icon, label) in stage_labels.items():
        if key in stages:
            print(f"  {icon} {label}")

    if status == TaskStatus.AI_UNAVAILABLE:
        files = result.get('files', {})
        print(f"\n  ⚠  AI unavailable")
        print(f"  ✓  Quality Gate correctly blocked incomplete article")
        if files:
            print(f"  ✓  Filesystem output created ({len(files)} files)")
        print(f"\n  STATUS: AI_UNAVAILABLE\n")
        print(f"  The article was NOT generated.")
        print(f"  The article was NOT approved.")
        print(f"  The article was NOT published.")
        print(f"\n  Next step: Add API key to config/.env")

    elif status == TaskStatus.READY_FOR_REVIEW:
        qr = result.get('quality_report', {})
        files = result.get('files', {})
        print(f"\n  ✓  Quality Gate: PASSED ({qr.get('score', 0)}/100)")
        if files:
            print(f"  ✓  Filesystem output created ({len(files)} files)")
        print(f"\n  STATUS: READY_FOR_REVIEW\n")
        print(f"  The article is ready for human review.")
        print(f"  It has NOT been published yet.")
        print(f"\n  Next step: [9] Human Approval → [10] Blogger Draft")

    elif status == TaskStatus.FAILED:
        errors = result.get('errors', [])
        print(f"\n  STATUS: FAILED")
        for err in errors:
            print(f"  ❌ {err}")

    print("=" * 60)

# ======================================================
# REVIEW & PUBLISH
# ======================================================

def cmd_human_approval():
    from agents.human_approval import run as approval_run
    approval_run()

def cmd_blogger_draft():
    from agents.blogger_draft import run as draft_run
    draft_run()

# ======================================================
# MONITORING
# ======================================================

def cmd_gsc_performance():
    from agents.site_report import run as report_run
    report_run()

def cmd_declining_pages():
    import sqlite3
    from config.settings import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT page, ROUND(AVG(position),1) as avg_pos,
               SUM(clicks) as clicks, SUM(impressions) as imp
        FROM gsc_data
        GROUP BY page
        HAVING avg_pos > 15 AND imp > 100
        ORDER BY imp DESC
        LIMIT 10
    """)
    rows = cursor.fetchall()
    conn.close()
    print("\n📉 Declining / Low-Performing Pages:\n")
    for page, pos, clicks, imp in rows:
        slug = page.rstrip('/').split('/')[-1][:50]
        print(f"  موضع {pos:5} | {imp:5} imp | {clicks:3} clicks | {slug}")

def cmd_rising_pages():
    import sqlite3
    from config.settings import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT page, ROUND(AVG(position),1) as avg_pos,
               SUM(clicks) as clicks, SUM(impressions) as imp
        FROM gsc_data
        GROUP BY page
        HAVING avg_pos BETWEEN 4 AND 15 AND imp > 200
        ORDER BY imp DESC
        LIMIT 10
    """)
    rows = cursor.fetchall()
    conn.close()
    print("\n📈 Rising Pages (موضع 4-15):\n")
    for page, pos, clicks, imp in rows:
        slug = page.rstrip('/').split('/')[-1][:50]
        print(f"  موضع {pos:5} | {imp:5} imp | {clicks:3} clicks | {slug}")

def cmd_internal_linking():
    import sqlite3
    from config.settings import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT query, ROUND(AVG(position),1) as pos,
               SUM(impressions) as imp
        FROM gsc_data
        GROUP BY query
        HAVING pos BETWEEN 11 AND 30 AND imp > 100
        ORDER BY imp DESC
        LIMIT 10
    """)
    rows = cursor.fetchall()
    conn.close()
    print("\n🔗 Internal Linking Opportunities (موضع 11-30):\n")
    for query, pos, imp in rows:
        print(f"  موضع {pos:5} | {imp:5} imp | {query}")

# ======================================================
# SYSTEM
# ======================================================

def cmd_system_status():
    import sqlite3
    from config.settings import DB_PATH
    print("\n⚙️  System Status:\n")

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM articles WHERE status='published'")
        articles = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM gsc_data")
        gsc = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM opportunities")
        opps = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM content_tasks")
        tasks = cursor.fetchone()[0]
        conn.close()
        print(f"  ✅ Database: OK")
        print(f"     Articles: {articles} | GSC rows: {gsc} | Opportunities: {opps} | Tasks: {tasks}")
    except Exception as e:
        print(f"  ❌ Database: {e}")

    files = ['knowledge/style_guide.md', 'knowledge/seo_rules.md', 'knowledge/brand_voice.md']
    all_ok = all(os.path.exists(f) for f in files)
    print(f"  {'✅' if all_ok else '❌'} Knowledge Base: {'OK' if all_ok else 'Missing files'}")

    outputs = len([f for f in os.listdir('outputs') if os.path.isfile(os.path.join('outputs', f))])
    output_dirs = len([f for f in os.listdir('outputs') if os.path.isdir(os.path.join('outputs', f))])
    print(f"  ✅ Outputs: {outputs} files, {output_dirs} pipeline folders")

def cmd_ai_status():
    print("\n🤖 AI Provider Status:\n")
    try:
        from config.settings import OPENROUTER_API_KEY, ANTHROPIC_API_KEY, OPENROUTER_MODEL
        if OPENROUTER_API_KEY and not OPENROUTER_API_KEY.startswith("sk-or-xxx"):
            print(f"  ✅ OpenRouter: configured")
            print(f"     Model: {OPENROUTER_MODEL}")
        else:
            print(f"  ❌ OpenRouter: not configured")

        if ANTHROPIC_API_KEY and not ANTHROPIC_API_KEY.startswith("sk-ant-xxx"):
            print(f"  ✅ Anthropic: configured")
        else:
            print(f"  ❌ Anthropic: not configured")

        from agents.pipeline import get_ai_provider
        active = get_ai_provider()
        print(f"\n  Active provider: {active if active else 'NONE — AI_UNAVAILABLE'}")
    except Exception as e:
        print(f"  ❌ Error: {e}")

def cmd_db_status():
    import sqlite3
    from config.settings import DB_PATH
    print("\n🗄️  Database Status:\n")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        tables = ['articles', 'keywords', 'gsc_data', 'internal_links', 'opportunities', 'content_tasks']
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  ✅ {table}: {count} rows")
        conn.close()
    except Exception as e:
        print(f"  ❌ {e}")

# ======================================================
# Router
# ======================================================

COMMANDS = {
    '1':  cmd_sync_data,
    '2':  cmd_site_report,
    '3':  cmd_content_opportunities,
    '4':  cmd_analyze_keyword,
    '5':  cmd_content_brief,
    '6':  cmd_outline,
    '7':  cmd_full_article,
    '8':  cmd_pipeline,
    '9':  cmd_human_approval,
    '10': cmd_blogger_draft,
    '11': cmd_gsc_performance,
    '12': cmd_declining_pages,
    '13': cmd_rising_pages,
    '14': cmd_internal_linking,
    '15': cmd_system_status,
    '16': cmd_ai_status,
    '17': cmd_db_status,
}

def main():
    print_header()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd in COMMANDS:
            COMMANDS[cmd]()
        else:
            print(f"  ❌ Unknown command: {cmd}")
        return

    while True:
        print_menu()
        choice = input("  > ").strip()

        if choice == '0':
            print("\n  Goodbye.\n")
            break
        elif choice in COMMANDS:
            try:
                COMMANDS[choice]()
            except Exception as e:
                print(f"\n  ❌ Error: {e}")
        else:
            print(f"\n  ❌ Invalid choice: {choice}")

        print()

if __name__ == "__main__":
    main()