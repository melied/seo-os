import sys
sys.path.insert(0, '.')

from agents.intent_agent import analyze
from agents.content_brief import generate_brief
from agents.outline_generator import build_outline_from_brief
from agents.writing_engine import load_knowledge, generate_content_with_ai

keyword = "تربية الدجاج في الجزائر 2026"

intent_data, _ = analyze(keyword, save=False)
brief = generate_brief(intent_data)
outline = build_outline_from_brief(brief)
knowledge = load_knowledge()

# اطبع الأقسام لنرى المشكلة
print("Sections:")
for s in outline['sections']:
    print(f"  type={s.get('type')} | heading={s.get('heading', 'MISSING')} | h2={s.get('h2', 'MISSING')}")