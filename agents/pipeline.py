import sqlite3
import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import DB_PATH
from agents.intent_agent import TaskStatus, analyze as analyze_intent
from agents.content_brief import generate_brief, save_brief_to_db
from agents.outline_generator import build_outline_from_brief, save_outline_to_db
from agents.quality_gate import save_quality_report
from agents.quality_gate_v2 import run_quality_gate_v2, print_quality_report_v2

def save_to_filesystem(keyword: str, stage: str, data, base_dir: str = "outputs") -> str:
    import re
    safe_name = re.sub(r'[^\w\s-]', '', keyword).strip()
    safe_name = re.sub(r'[\s]+', '-', safe_name)[:50]
    task_dir = os.path.join(base_dir, safe_name)
    os.makedirs(task_dir, exist_ok=True)

    filename_map = {
        'intent': 'intent.json', 'brief': 'brief.json',
        'outline': 'outline.json', 'article': 'article.md',
        'schema': 'schema.json', 'quality': 'quality_report.json'
    }
    filename = filename_map.get(stage, f"{stage}.json")
    filepath = os.path.join(task_dir, filename)

    if isinstance(data, str):
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(data)
    else:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    return filepath

def get_ai_provider():
    try:
        from config.settings import OPENROUTER_API_KEY, ANTHROPIC_API_KEY
        if OPENROUTER_API_KEY and not OPENROUTER_API_KEY.startswith("sk-or-xxx"):
            return "openrouter"
        if ANTHROPIC_API_KEY and not ANTHROPIC_API_KEY.startswith("sk-ant-xxx"):
            return "anthropic"
    except Exception:
        pass
    return None

def generate_article_with_ai(keyword: str, outline: dict, brief: dict) -> tuple:
    try:
        from agents.writing_engine import (
            generate_meta_with_ai, generate_content_with_ai,
            generate_slug, generate_schema, load_knowledge
        )
        knowledge = load_knowledge()
        slug = generate_slug(keyword)
        meta_title, meta_desc = generate_meta_with_ai(keyword, knowledge)
        if not meta_title:
            return None, None, None, slug, None

        content = generate_content_with_ai(keyword, outline['sections'], knowledge)
        if not content:
            return None, meta_title, meta_desc, slug, None

        faqs = []
        for s in outline['sections']:
            if s['type'] == 'faq':
                faqs = s.get('questions', [])
                break

        article_schema, _ = generate_schema(keyword, meta_title, meta_desc, slug, faqs)
        return content, meta_title, meta_desc, slug, article_schema

    except Exception as e:
        print(f"      ⚠️  خطأ في AI: {e}")
        return None, None, None, None, None

def run_pipeline(keyword: str, save_files: bool = True) -> dict:
    print("\n" + "=" * 60)
    print("     SEO OS — Content Pipeline")
    print("=" * 60)
    print(f"  الكلمة المفتاحية: {keyword}")
    print(f"  الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    result = {
        "keyword": keyword,
        "status": TaskStatus.PLANNED,
        "stages_completed": [],
        "files": {},
        "errors": []
    }

    # Stage 1 — Intent
    print(f"\n📊 Stage 1: Intent Analysis")
    try:
        intent_data, task_id = analyze_intent(keyword, save=True)
        result['intent'] = intent_data
        result['task_id'] = task_id
        result['status'] = TaskStatus.RESEARCHING
        result['stages_completed'].append('intent')
        print(f"   ✅ Intent: {intent_data['search_intent']}")
        print(f"   ✅ نوع المحتوى: {intent_data['content_type']}")
        print(f"   ✅ Task ID: {task_id}")
        if save_files:
            result['files']['intent'] = save_to_filesystem(keyword, 'intent', intent_data)
    except Exception as e:
        result['errors'].append(f"Intent Analysis فشل: {e}")
        result['status'] = TaskStatus.FAILED
        return result

    # Stage 2 — Brief
    print(f"\n📋 Stage 2: Content Brief")
    try:
        brief = generate_brief(intent_data)
        save_brief_to_db(task_id, brief)
        result['brief'] = brief
        result['status'] = TaskStatus.BRIEF_READY
        result['stages_completed'].append('brief')
        gap = brief['content_gap']
        print(f"   ✅ Content Gap: {gap['gap_type']}")
        print(f"   ✅ التوصية: {gap['recommendation']}")
        print(f"   ✅ الأقسام: {len(brief['sections'])}")
        print(f"   ✅ روابط داخلية: {len(brief['internal_link_targets'])}")
        if save_files:
            result['files']['brief'] = save_to_filesystem(keyword, 'brief', brief)
    except Exception as e:
        result['errors'].append(f"Content Brief فشل: {e}")
        result['status'] = TaskStatus.FAILED
        return result

    # Stage 3 — Outline
    print(f"\n📐 Stage 3: Outline Generation")
    try:
        outline = build_outline_from_brief(brief)
        save_outline_to_db(task_id, outline)
        result['outline'] = outline
        result['status'] = TaskStatus.OUTLINE_READY
        result['stages_completed'].append('outline')
        validation = outline['validation']
        print(f"   ✅ H1: {outline['h1'][:50]}...")
        print(f"   ✅ الأقسام: {len(outline['sections'])}")
        print(f"   ✅ Outline صالح: {validation['is_valid']}")
        if not validation['is_valid']:
            result['errors'].extend(validation['issues'])
            result['status'] = TaskStatus.FAILED
            return result
        if save_files:
            result['files']['outline'] = save_to_filesystem(keyword, 'outline', outline)
    except Exception as e:
        result['errors'].append(f"Outline فشل: {e}")
        result['status'] = TaskStatus.FAILED
        return result

    # Stage 4 — Full Article
    print(f"\n✍️  Stage 4: Full Article Generation")
    ai_provider = get_ai_provider()
    article_text = None
    meta_title = ""
    meta_desc = ""
    slug = ""
    schema = None

    if ai_provider:
        print(f"   🤖 مزود AI: {ai_provider}")
        result['status'] = TaskStatus.WRITING
        article_text, meta_title, meta_desc, slug, schema = generate_article_with_ai(
            keyword, outline, brief
        )
        if article_text:
            print(f"   ✅ تم توليد المقال ({len(article_text.split())} كلمة)")
            result['stages_completed'].append('article_ai')
            if save_files:
                result['files']['article'] = save_to_filesystem(keyword, 'article', article_text)
            if schema and save_files:
                result['files']['schema'] = save_to_filesystem(keyword, 'schema', schema)
        else:
            print(f"   ⚠️  AI فشل في توليد المقال")
            ai_provider = None
    else:
        print(f"   ⏭️  AI غير متاح")

    if not ai_provider or not article_text:
        print(f"\n{'=' * 60}")
        print(f"  ⚙️  الحالة: AI_UNAVAILABLE")
        print(f"{'=' * 60}")
        print(f"  تم حفظ:\n    ✅ Intent Analysis\n    ✅ Content Brief\n    ✅ Outline")
        print(f"  لم يتم:\n    ⏭️  Full Article\n    ⏭️  Schema\n    ⏭️  Quality Gate")
        print(f"\n  لإكمال Pipeline: أضف API Key في config/.env")
        print(f"{'=' * 60}")
        result['status'] = TaskStatus.AI_UNAVAILABLE
        result['stages_completed'].append('brief_and_outline_saved')
        if save_files:
            ai_report = {
                "status": TaskStatus.AI_UNAVAILABLE,
                "keyword": keyword,
                "message": "AI غير متاح",
                "stages_completed": result['stages_completed'],
                "files_saved": list(result['files'].keys())
            }
            result['files']['quality_report'] = save_to_filesystem(keyword, 'quality', ai_report)
        return result

    # Stage 5 — SEO
    print(f"\n🔍 Stage 5: SEO Optimization")
    result['status'] = TaskStatus.SEO_OPTIMIZATION

    if not meta_title:
        meta_title = outline['meta_title_suggestion']
    if not slug:
        from agents.writing_engine import generate_slug
        slug = generate_slug(keyword)
    if not meta_desc:
        meta_desc = brief.get('seo_notes', [''])[0] if brief.get('seo_notes') else ""

    result['meta_title'] = meta_title
    result['meta_description'] = meta_desc
    result['slug'] = slug
    result['stages_completed'].append('seo')
    print(f"   ✅ Meta Title: {meta_title[:50]}...")
    print(f"   ✅ Slug: {slug}")
    print(f"   ✅ Meta Desc: {len(meta_desc)} حرف")

    # Stage 6 — Quality Gate V2
    print(f"\n🔒 Stage 6: Quality Gate V2")
    result['status'] = TaskStatus.QUALITY_CHECK

    try:
        content_type = result.get('intent', {}).get('content_type', 'general_article')

        # V2 مباشرة — Static + AI + Deterministic
        quality_report = run_quality_gate_v2(
            article_text=article_text,
            keyword=keyword,
            content_type=content_type,
            base_seo_result={"score": 100}
        )

        quality_report['meta_title'] = meta_title
        quality_report['slug'] = slug

        save_quality_report(task_id, quality_report)
        result['quality_report'] = quality_report
        result['stages_completed'].append('quality_gate')

        if save_files:
            result['files']['quality_report'] = save_to_filesystem(keyword, 'quality', quality_report)

        print_quality_report_v2(quality_report)

        if quality_report['passed']:
            result['status'] = TaskStatus.READY_FOR_REVIEW
        else:
            result['status'] = TaskStatus.FAILED

    except Exception as e:
        result['errors'].append(f"Quality Gate V2 فشل: {e}")
        result['status'] = TaskStatus.FAILED
        print(f"   ❌ فشل: {e}")

    # Final Report
    print(f"\n{'=' * 60}")
    status = result['status']
    icon = "✅" if status == TaskStatus.READY_FOR_REVIEW else "❌" if status == TaskStatus.FAILED else "⚙️"
    print(f"  {icon} النتيجة النهائية: {status}")
    print(f"  المراحل المكتملة: {', '.join(result['stages_completed'])}")

    if result['files']:
        print(f"\n  الملفات المحفوظة:")
        for stage, path in result['files'].items():
            print(f"    📄 {stage}: {path}")

    if result['errors']:
        print(f"\n  الأخطاء:")
        for err in result['errors']:
            print(f"    ❌ {err}")

    if status == TaskStatus.READY_FOR_REVIEW:
        print(f"\n  ✅ المقال جاهز للمراجعة البشرية")
        print(f"  ⏳ في انتظار الموافقة قبل النشر على Blogger")

    print(f"{'=' * 60}")
    return result


if __name__ == "__main__":
    if len(sys.argv) > 1:
        kw = ' '.join(sys.argv[1:])
    else:
        kw = "تربية الدجاج في الجزائر 2026"
    run_pipeline(kw)