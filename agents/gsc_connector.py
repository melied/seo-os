import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
from config.settings import GOOGLE_SERVICE_ACCOUNT_JSON, GSC_SITE_URL, DB_PATH

SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']

def get_service():
    creds = service_account.Credentials.from_service_account_file(
        GOOGLE_SERVICE_ACCOUNT_JSON, scopes=SCOPES
    )
    return build('webmasters', 'v3', credentials=creds)

def fetch_gsc_data(days=90):
    service = get_service()
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=days)).strftime('%Y-%m-%d')
    date_range = f"{start_date} to {end_date}"

    print(f"جاري جلب بيانات Search Console ({date_range})...")

    all_rows = []
    start_row = 0
    row_limit = 25000

    while True:
        result = service.searchanalytics().query(
            siteUrl=GSC_SITE_URL,
            body={
                'startDate': start_date,
                'endDate': end_date,
                'dimensions': ['query', 'page'],
                'rowLimit': row_limit,
                'startRow': start_row
            }
        ).execute()

        rows = result.get('rows', [])
        if not rows:
            break

        all_rows.extend(rows)
        print(f"   تم جلب {len(all_rows)} صف...")

        if len(rows) < row_limit:
            break

        start_row += row_limit

    return all_rows, date_range

def save_gsc_data(rows, date_range):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # احذف البيانات القديمة لنفس النطاق الزمني
    cursor.execute("DELETE FROM gsc_data WHERE date_range = ?", (date_range,))

    saved = 0
    for row in rows:
        keys = row.get('keys', [])
        query = keys[0] if len(keys) > 0 else ''
        page = keys[1] if len(keys) > 1 else ''

        cursor.execute("""
            INSERT INTO gsc_data (page, query, clicks, impressions, ctr, position, date_range)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            page,
            query,
            int(row.get('clicks', 0)),
            int(row.get('impressions', 0)),
            round(row.get('ctr', 0), 4),
            round(row.get('position', 0), 1),
            date_range
        ))
        saved += 1

    conn.commit()
    conn.close()
    return saved

def run():
    rows, date_range = fetch_gsc_data(days=90)
    saved = save_gsc_data(rows, date_range)

    print(f"\n✅ اكتمل جلب بيانات Search Console:")
    print(f"   - النطاق الزمني: {date_range}")
    print(f"   - إجمالي الصفوف المحفوظة: {saved}")

if __name__ == "__main__":
    run()