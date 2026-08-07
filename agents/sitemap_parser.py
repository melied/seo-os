import sqlite3
import sys
import os
import requests
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import GSC_SITE_URL, DB_PATH

SITEMAP_URL = GSC_SITE_URL.rstrip('/') + '/sitemap.xml'

def fetch_sitemap(url):
    print(f"جاري قراءة Sitemap: {url}")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"❌ خطأ في جلب Sitemap: {e}")
        return None

def parse_sitemap(content):
    urls = []
    try:
        root = ET.fromstring(content)
        ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

        # تحقق إن كان sitemap index (يحتوي على sitemap أخرى)
        sitemaps = root.findall('sm:sitemap', ns)
        if sitemaps:
            print(f"   وجدنا Sitemap Index يحتوي على {len(sitemaps)} sitemap")
            for sitemap in sitemaps:
                loc = sitemap.find('sm:loc', ns)
                if loc is not None:
                    sub_content = fetch_sitemap(loc.text.strip())
                    if sub_content:
                        sub_urls = parse_sitemap(sub_content)
                        urls.extend(sub_urls)
        else:
            # sitemap عادي يحتوي على URLs
            url_elements = root.findall('sm:url', ns)
            for url_el in url_elements:
                loc = url_el.find('sm:loc', ns)
                lastmod = url_el.find('sm:lastmod', ns)
                if loc is not None:
                    urls.append({
                        'url': loc.text.strip(),
                        'lastmod': lastmod.text.strip() if lastmod is not None else ''
                    })

    except Exception as e:
        print(f"❌ خطأ في تحليل Sitemap: {e}")

    return urls

def match_with_articles(urls):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    matched = 0
    for item in urls:
        url = item['url']
        lastmod = item['lastmod']

        slug = url.rstrip('/').split('/')[-1].replace('.html', '')

        cursor.execute("""
            UPDATE articles SET published_at = ?
            WHERE slug = ?
        """, (lastmod, slug))

        if cursor.rowcount > 0:
            matched += 1

    conn.commit()
    conn.close()
    return matched
def run():
    content = fetch_sitemap(SITEMAP_URL)
    if not content:
        return

    urls = parse_sitemap(content)
    print(f"   إجمالي URLs في Sitemap: {len(urls)}")

    matched = match_with_articles(urls)

    print(f"\n✅ اكتمل تحليل Sitemap:")
    print(f"   - إجمالي URLs: {len(urls)}")
    print(f"   - URLs مطابقة لمقالات: {matched}")

    # عرض أول 5 URLs
    print(f"\n📋 عينة من URLs:")
    for item in urls[:5]:
        print(f"   - {item['url']}")

if __name__ == "__main__":
    run()