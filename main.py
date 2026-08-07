import sys
import os

def print_header():
    print("=" * 60)
    print("       SEO Operating System — news-theworld.com")
    print("=" * 60)
    print()

def print_menu():
    print("ما الذي تريد تشغيله؟")
    print()
    print("  [1] جمع البيانات (Blogger + GSC + Sitemap)")
    print("  [2] تقرير الموقع")
    print("  [3] تحليل فرص المحتوى")
    print("  [4] توليد هيكل مقال (أفضل فرصة)")
    print("  [5] توليد هيكل مقال (كلمة مفتاحية محددة)")
    print("  [6] تشغيل كامل (1 + 2 + 3)")
    print("  [0] خروج")
    print()

def run_data_collection():
    print("\n📡 جمع البيانات...\n")
    from agents.blogger_connector import run as blogger_run
    from agents.gsc_connector import run as gsc_run
    from agents.sitemap_parser import run as sitemap_run
    blogger_run()
    print()
    gsc_run()
    print()
    sitemap_run()

def run_site_report():
    print("\n📊 تقرير الموقع...\n")
    from agents.site_report import run as report_run
    report_run()

def run_research():
    print("\n🔍 تحليل فرص المحتوى...\n")
    from agents.research_engine import run as research_run
    research_run()

def run_writing(keyword=None):
    print("\n✍️  توليد هيكل المقال...\n")
    from agents.writing_engine import run as writing_run
    writing_run(keyword=keyword)

def main():
    print_header()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == 'collect':
            run_data_collection()
        elif cmd == 'report':
            run_site_report()
        elif cmd == 'research':
            run_research()
        elif cmd == 'write':
            keyword = ' '.join(sys.argv[2:]) if len(sys.argv) > 2 else None
            run_writing(keyword=keyword)
        elif cmd == 'all':
            run_data_collection()
            print()
            run_site_report()
            print()
            run_research()
        else:
            print(f"❌ أمر غير معروف: {cmd}")
        return

    # وضع التفاعلي
    while True:
        print_menu()
        choice = input("اختر رقماً: ").strip()

        if choice == '0':
            print("وداعاً!")
            break
        elif choice == '1':
            run_data_collection()
        elif choice == '2':
            run_site_report()
        elif choice == '3':
            run_research()
        elif choice == '4':
            run_writing()
        elif choice == '5':
            keyword = input("أدخل الكلمة المفتاحية: ").strip()
            if keyword:
                run_writing(keyword=keyword)
            else:
                print("❌ الكلمة المفتاحية فارغة")
        elif choice == '6':
            run_data_collection()
            print()
            run_site_report()
            print()
            run_research()
        else:
            print("❌ اختيار غير صحيح\n")

        print("\n" + "-" * 60 + "\n")

if __name__ == "__main__":
    main()