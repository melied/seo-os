import os

files = [
    'knowledge/style_guide.md',
    'knowledge/seo_rules.md',
    'knowledge/brand_voice.md'
]

for f in files:
    if os.path.exists(f):
        size = os.path.getsize(f)
        print(f"✅ {f} ({size} bytes)")
    else:
        print(f"❌ {f} — مفقود")