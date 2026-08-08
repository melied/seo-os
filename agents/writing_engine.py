import sqlite3
import sys
import os
import json
import re
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import DB_PATH, OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODEL, ANTHROPIC_API_KEY

def detect_ai_provider():
    """تحديد مزود الـ AI المتاح"""
    if OPENROUTER_API_KEY and not OPENROUTER_API_KEY.startswith("sk-or-xxx"):
        return "openrouter"
    elif ANTHROPIC_API_KEY and not ANTHROPIC_API_KEY.startswith("sk-ant-xxx"):
        return "anthropic"
    return None

def get_ai_client():
    from openai import OpenAI
    return OpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url=OPENROUTER_BASE_URL
    )

def ask_ai(prompt, system_prompt="", max_tokens=2000):
    try:
        client = get_ai_client()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=messages,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return None

def load_knowledge():
    files = {
        'style': 'knowledge/style_guide.md',
        'seo': 'knowledge/seo_rules.md',
        'brand': 'knowledge/brand_voice.md'
    }
    knowledge = {}
    for key, path in files.items():
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                knowledge[key] = f.read()
        else:
            knowledge[key] = ""
    return knowledge

def get_top_opportunities(limit=5):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT query, impressions, clicks, position, ctr, type
        FROM opportunities
        WHERE status = 'pending'
        ORDER BY score DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_related_articles(keyword, limit=3):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    words = keyword.split()
    results = []
    for word in words:
        if len(word) > 3:
            cursor.execute("""
                SELECT title, slug FROM articles
                WHERE title LIKE ? AND status = 'published'
                LIMIT 3
            """, (f'%{word}%',))
            results.extend(cursor.fetchall())
    conn.close()
    seen = []
    unique = []
    for r in results:
        if r[1] not in seen:
            seen.append(r[1])
            unique.append(r)
    return unique[:limit]

def generate_slug(keyword):
    arabic_map = {
        'ا': 'a', 'أ': 'a', 'إ': 'a', 'آ': 'a',
        'ب': 'b', 'ت': 't', 'ث': 'th', 'ج': 'j',
        'ح': 'h', 'خ': 'kh', 'د': 'd', 'ذ': 'dh',
        'ر': 'r', 'ز': 'z', 'س': 's', 'ش': 'sh',
        'ص': 's', 'ض': 'd', 'ط': 't', 'ظ': 'z',
        'ع': 'a', 'غ': 'gh', 'ف': 'f', 'ق': 'q',
        'ك': 'k', 'ل': 'l', 'م': 'm', 'ن': 'n',
        'ه': 'h', 'و': 'w', 'ي': 'y', 'ى': 'a',
        'ة': 'a', 'ء': '', 'ئ': 'y', 'ؤ': 'w',
        ' ': '-'
    }
    slug = ''
    for char in keyword:
        slug += arabic_map.get(char, '')
    slug = re.sub(r'-+', '-', slug).strip('-').lower()
    slug = f"{slug}-{datetime.now().year}"
    return slug

def generate_meta_with_ai(keyword, knowledge):
    system = f"""أنت خبير SEO متخصص في المحتوى العربي الزراعي.
{knowledge['seo']}
{knowledge['brand']}"""

    prompt = f"""اكتب لي Meta Title و Meta Description لمقال عن: {keyword}

القواعد:
- Meta Title: بين 55-60 حرف، يحتوي الكلمة المفتاحية
- Meta Description: بين 140-155 حرف، يحتوي الكلمة المفتاحية وفائدة واضحة
- اللغة: عربية فصحى مبسطة
- السنة الحالية: {datetime.now().year}

أجب بهذا الشكل فقط:
META_TITLE: [النص هنا]
META_DESC: [النص هنا]"""

    result = ask_ai(prompt, system)
    if result:
        lines = result.strip().split('\n')
        meta_title = keyword
        meta_desc = ""
        for line in lines:
            if line.startswith('META_TITLE:'):
                meta_title = line.replace('META_TITLE:', '').strip()
            elif line.startswith('META_DESC:'):
                meta_desc = line.replace('META_DESC:', '').strip()
        return meta_title, meta_desc
    return None, None

def generate_outline_with_ai(keyword, knowledge):
    system = f"""أنت محرر محتوى متخصص في الثروة الحيوانية والزراعة في الجزائر.
{knowledge['style']}"""

    prompt = f"""اكتب هيكل مقال SEO احترافي عن: {keyword}

المطلوب:
- مقدمة قوية تذكر الكلمة المفتاحية في أول 50 كلمة
- 4-5 عناوين H2 واضحة وعملية
- قسم أسئلة شائعة (3 أسئلة)
- خاتمة

أجب بهذا الشكل:
INTRO: [تعليمات المقدمة]
H2: [عنوان القسم الأول]
H2: [عنوان القسم الثاني]
H2: [عنوان القسم الثالث]
H2: [عنوان القسم الرابع]
FAQ: [السؤال الأول]
FAQ: [السؤال الثاني]
FAQ: [السؤال الثالث]
CONCLUSION: [تعليمات الخاتمة]"""

    result = ask_ai(prompt, system)
    outline = []
    faqs = []

    if result:
        for line in result.strip().split('\n'):
            line = line.strip()
            if line.startswith('INTRO:'):
                outline.append({'type': 'intro', 'heading': 'مقدمة', 'notes': line.replace('INTRO:', '').strip()})
            elif line.startswith('H2:'):
                outline.append({'type': 'h2', 'heading': line.replace('H2:', '').strip(), 'notes': ''})
            elif line.startswith('FAQ:'):
                faqs.append(line.replace('FAQ:', '').strip())
            elif line.startswith('CONCLUSION:'):
                outline.append({'type': 'conclusion', 'heading': 'خاتمة', 'notes': line.replace('CONCLUSION:', '').strip()})
        if faqs:
            outline.append({'type': 'faq', 'heading': 'أسئلة شائعة', 'notes': '', 'questions': faqs})

    return outline if outline else None, faqs if faqs else None

def generate_content_with_ai(keyword, outline, knowledge):
    system = f"""أنت كاتب محتوى متخصص في الثروة الحيوانية والزراعة في الجزائر والمغرب العربي.
{knowledge['style']}
{knowledge['brand']}"""

    sections_text = '\n'.join([
        f"- {s.get('h2') or s.get('heading') or s['type']}" for s in outline
        if s['type'] in ['introduction', 'intro', 'h2', 'conclusion']
    ])

    prompt = f"""اكتب مقالاً كاملاً باللغة العربية الفصحى المبسطة عن: {keyword}

الهيكل:
{sections_text}

القواعد:
- الكلمة المفتاحية في أول 50 كلمة
- كل فقرة لا تتجاوز 4 أسطر
- استخدم أرقاماً وإحصائيات محددة
- المقال بين 1000-1500 كلمة
- اكتب المقال كاملاً بدون تعليقات أو ملاحظات

ابدأ مباشرة بالمقدمة."""

    return ask_ai(prompt, system, max_tokens=3000)

def get_fallback_outline(keyword):
    year = datetime.now().year
    return [
        {'type': 'intro', 'heading': 'مقدمة', 'notes': f"ابدأ بسؤال أو إحصائية عن {keyword}. اذكر الكلمة المفتاحية في أول 50 كلمة."},
        {'type': 'h2', 'heading': f"ما هو {keyword}؟", 'notes': 'تعريف واضح ومبسط. 100-150 كلمة.'},
        {'type': 'h2', 'heading': f"أهمية {keyword}", 'notes': 'اذكر 3-4 نقاط عملية.'},
        {'type': 'h2', 'heading': f"كيفية التعامل مع {keyword}", 'notes': 'خطوات عملية أو معلومات تفصيلية.'},
        {'type': 'h2', 'heading': f"{keyword} في الجزائر {year}", 'notes': 'أرقام وبيانات محلية.'},
        {'type': 'faq', 'heading': 'أسئلة شائعة', 'notes': '', 'questions': [
            f"ما هو {keyword}؟",
            f"كم تكلفة {keyword} في الجزائر؟",
            f"كيف أبدأ {keyword}؟"
        ]},
        {'type': 'conclusion', 'heading': 'خاتمة', 'notes': 'لخّص أهم 3 نقاط. اطرح سؤالاً للقارئ.'}
    ]

def get_fallback_faqs(keyword):
    return [
        f"ما هو {keyword}؟",
        f"كم تكلفة {keyword} في الجزائر؟",
        f"كيف أبدأ {keyword}؟"
    ]

def generate_schema(keyword, meta_title, meta_desc, slug, faqs):
    year = datetime.now().year
    url = f"https://www.news-theworld.com/{year}/{slug}.html"

    article_schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": meta_title,
        "description": meta_desc,
        "url": url,
        "inLanguage": "ar",
        "author": {
            "@type": "Organization",
            "name": "الثروة الحيوانية والفلاحة"
        },
        "publisher": {
            "@type": "Organization",
            "name": "الثروة الحيوانية والفلاحة",
            "url": "https://www.news-theworld.com"
        },
        "datePublished": datetime.now().strftime('%Y-%m-%d'),
        "dateModified": datetime.now().strftime('%Y-%m-%d')
    }

    faq_schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": f"[أضف الإجابة هنا عن {q}]"
                }
            }
            for q in faqs
        ]
    }

    return article_schema, faq_schema

def save_article(keyword, slug, meta_title, meta_desc, content, outline, related, schemas, ai_wrote_content):
    article_schema, faq_schema = schemas

    output = f"# {meta_title}\n\n"
    output += f"**الكلمة المفتاحية:** {keyword}\n"
    output += f"**Slug:** {slug}\n"
    output += f"**Meta Description:** {meta_desc}\n\n"
    output += "---\n\n"

    if ai_wrote_content and content:
        output += content
        output += "\n\n"
    else:
        for section in outline:
            if section['type'] == 'intro':
                output += f"## مقدمة\n*{section['notes']}*\n\n[اكتب المقدمة هنا]\n\n"
            elif section['type'] == 'h2':
                output += f"## {section['heading']}\n\n[اكتب المحتوى هنا]\n\n"
            elif section['type'] == 'faq':
                output += "## أسئلة شائعة\n"
                for q in section.get('questions', []):
                    output += f"### {q}\n[أضف الإجابة هنا]\n\n"
            elif section['type'] == 'conclusion':
                output += f"## خاتمة\n*{section['notes']}*\n\n[اكتب الخاتمة هنا]\n\n"

    if related:
        output += "---\n\n## روابط داخلية مقترحة\n"
        for title, article_slug in related:
            year = datetime.now().year
            output += f"- [{title}](https://www.news-theworld.com/{year}/{article_slug}.html)\n"
        output += "\n"

    output += "---\n\n## Schema (JSON-LD)\n"
    output += "```json\n"
    output += json.dumps(article_schema, ensure_ascii=False, indent=2)
    output += "\n```\n\n```json\n"
    output += json.dumps(faq_schema, ensure_ascii=False, indent=2)
    output += "\n```\n"

    filepath = os.path.join('outputs', f"{slug}.md")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(output)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO articles (title, slug, keyword, status, content, meta_title, meta_description, schema)
        VALUES (?, ?, ?, 'draft', ?, ?, ?, ?)
    """, (
        meta_title, slug, keyword, output, meta_title, meta_desc,
        json.dumps(article_schema, ensure_ascii=False)
    ))
    conn.commit()
    conn.close()

    return filepath

def run(keyword=None):
    print("=" * 60)
    print("     Writing Engine — توليد المقال")
    print("=" * 60)

    if not keyword:
        opportunities = get_top_opportunities(limit=1)
        if not opportunities:
            print("❌ لا توجد فرص. شغّل research_engine أولاً.")
            return
        keyword, impressions, clicks, position, ctr, opp_type = opportunities[0]
    else:
        impressions, position, opp_type = 0, 0, "مقال جديد"

    print(f"\n📝 الكلمة المفتاحية: {keyword}")

    ai_provider = detect_ai_provider()

    if ai_provider:
        print(f"   ⚙️  الوضع: AI نشط ({ai_provider})")
    else:
        print("   ⚙️  الوضع: Fallback — بدون AI")

    knowledge = load_knowledge()
    slug = generate_slug(keyword)
    related = get_related_articles(keyword)
    year = datetime.now().year

    # --- Meta Title & Description ---
    print("\n   🤖 Meta Title و Meta Description:")
    meta_title, meta_desc = None, None

    if ai_provider:
        meta_title, meta_desc = generate_meta_with_ai(keyword, knowledge)
        if meta_title:
            print(f"      ✅ تم التوليد بنجاح")
        else:
            print("      ⚠️  فشل AI — استخدام القالب المحلي")

    if not meta_title:
        print("      ⏭️  AI غير متاح — استخدام القالب المحلي")
        meta_title = f"{keyword}: دليل شامل {year}"
        meta_desc = f"كل ما تحتاج معرفته عن {keyword}. معلومات دقيقة ومحدثة {year} من السوق المحلي الجزائري."
        if len(meta_desc) > 155:
            meta_desc = meta_desc[:152] + "..."

    # --- Outline ---
    print("\n   🤖 هيكل المقال:")
    outline, faqs = None, None

    if ai_provider:
        outline, faqs = generate_outline_with_ai(keyword, knowledge)
        if outline:
            print(f"      ✅ تم التوليد بنجاح ({len(outline)} قسم)")
        else:
            print("      ⚠️  فشل AI — استخدام القواعد المحلية")

    if not outline:
        print("      ⏭️  AI غير متاح — استخدام القواعد المحلية")
        outline = get_fallback_outline(keyword)
        faqs = get_fallback_faqs(keyword)

    # --- Content ---
    print("\n   🤖 كتابة المحتوى:")
    content = None
    ai_wrote_content = False

    if ai_provider:
        content = generate_content_with_ai(keyword, outline, knowledge)
        if content:
            print(f"      ✅ تم الكتابة ({len(content.split())} كلمة)")
            ai_wrote_content = True
        else:
            print("      ⚠️  فشل AI في كتابة المحتوى")
    else:
        print("      ⏭️  لم يتم تنفيذ الكتابة بالـ AI")

    # --- Schema & Save ---
    schemas = generate_schema(keyword, meta_title, meta_desc, slug, faqs)
    filepath = save_article(keyword, slug, meta_title, meta_desc, content, outline, related, schemas, ai_wrote_content)

    if ai_wrote_content:
        print(f"\n✅ تم إنشاء المقال الكامل بالـ AI")
    else:
        print(f"\n✅ تم إنشاء مخطط المقال بنجاح")

    print(f"   - Meta Title: {meta_title}")
    print(f"   - Slug: {slug}")
    print(f"   - الروابط الداخلية: {len(related)}")
    print(f"   - الملف: {filepath}")
    if ai_wrote_content and content:
        print(f"   - عدد الكلمات: {len(content.split())}")
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        keyword = ' '.join(sys.argv[1:])
        run(keyword=keyword)
    else:
        run()