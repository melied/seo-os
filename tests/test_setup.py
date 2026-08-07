import os
import sqlite3
from config.settings import DB_PATH


def test_structure():
    folders = [
        "config",
        "knowledge",
        "prompts",
        "templates",
        "data",
        "agents",
        "outputs",
        "logs",
    ]

    missing = []

    for folder in folders:
        if os.path.isdir(folder):
            print(f"✅ {folder}/")
        else:
            print(f"❌ {folder}/ — مفقود")
            missing.append(folder)

    assert not missing, f"مجلدات مفقودة: {', '.join(missing)}"


def test_database():
    conn = sqlite3.connect(DB_PATH)

    try:
        cursor = conn.cursor()

        tables = [
            "articles",
            "keywords",
            "gsc_data",
            "internal_links",
        ]

        missing = []

        for table in tables:
            cursor.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name=?",
                (table,),
            )

            if cursor.fetchone():
                print(f"✅ جدول: {table}")
            else:
                print(f"❌ جدول مفقود: {table}")
                missing.append(table)

        assert not missing, f"جداول مفقودة: {', '.join(missing)}"

    finally:
        conn.close()


if __name__ == "__main__":
    print("=== اختبار هيكل المشروع ===")
    test_structure()

    print("\n=== اختبار قاعدة البيانات ===")
    test_database()

    print("\n🎉 الاختبارات مكتملة")