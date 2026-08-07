import os
import sqlite3
from config.settings import DB_PATH

def test_structure():
    folders = ["config", "knowledge", "prompts", "templates",
               "data", "agents", "outputs", "logs"]
    all_ok = True
    for folder in folders:
        if os.path.isdir(folder):
            print(f"✅ {folder}/")
        else:
            print(f"❌ {folder}/ — مفقود")
            all_ok = False
    return all_ok

def test_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    tables = ["articles", "keywords", "gsc_data", "internal_links"]
    all_ok = True
    for table in tables:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        if cursor.fetchone():
            print(f"✅ جدول: {table}")
        else:
            print(f"❌ جدول مفقود: {table}")
            all_ok = False
    conn.close()
    return all_ok

if __name__ == "__main__":
    print("=== اختبار هيكل المشروع ===")
    s = test_structure()
    print("\n=== اختبار قاعدة البيانات ===")
    d = test_database()
    print()
    if s and d:
        print("🎉 المرحلة 0 مكتملة — الأساس جاهز")
    else:
        print("⚠️  يوجد مشاكل يجب حلها أولًا")