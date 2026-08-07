import sqlite3

conn = sqlite3.connect('data/seo_os.db')
cursor = conn.cursor()
cursor.execute('SELECT title, slug, blogger_post_id FROM articles LIMIT 5')
rows = cursor.fetchall()
for row in rows:
    print(row)
conn.close()