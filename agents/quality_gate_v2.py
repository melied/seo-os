import re
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.intent_agent import TaskStatus

# ======================================================
# Layer 1 — Static Analysis
# ======================================================

AI_REVIEW_REQUIRED_TYPES = [
    'feasibility_study',
    'price_guide',
    'informational_article',
    'commercial_guide'
]

INCORRECT_TERMINOLOGY = {
    'الآجي':       'Avian Influenza / H5N1 (استخدم "إنفلونزا الطيور")',
    'التحصيم':     'التطعيم أو التحصين (وليس التحصيم)',
    'اللقح':       'اللقاح (وليس اللقح)',
    'الصيصان':     'صحيح لكن تأكد من السياق (الكتاكيت أوضح)',
    'بروتيني':     'تحقق من السياق — قد يكون "بروتين"',
}

FINANCIAL_PATTERNS = [
    r'\d+[\.,]?\d*\s*(دج|دينار|DA)',
    r'\d+[\.,]?\d*\s*(دج|دينار)\s*/\s*(كغ|كيلو|لتر|وحدة)',
    r'سعر[^.،]{0,50}\d+',
    r'تكلفة[^.،]{0,50}\d+',
    r'ربح[^.،]{0,50}\d+',
    r'إيراد[^.،]{0,50}\d+',
    r'\d+[\.,]?\d*\s*%',
    r'\d+[\.,]?\d*\s*(طن|قنطار|كيس)',
]

SENSITIVE_CLAIM_PATTERNS = [
    r'(يثبت|ثبت علمياً|دراسات تؤكد)',
    r'(أفضل|الأول|الوحيد|الأكثر)',
    r'(مضمون|بدون خسارة|ربح مؤكد)',
    r'(وزارة|حكومة|قانون|مرسوم)',
    r'(علاج|دواء|جرعة|تركيز)',
]

def extract_numbers_and_claims(text: str) -> dict:
    financial_matches = []
    for pattern in FINANCIAL_PATTERNS:
        matches = re.findall(pattern, text)
        financial_matches.extend(matches)

    sensitive_matches = []
    for pattern in SENSITIVE_CLAIM_PATTERNS:
        matches = re.findall(pattern, text, re.UNICODE)
        sensitive_matches.extend(matches)

    sentences_with_numbers = []
    sentences = re.split(r'[.،\n]', text)
    for sent in sentences:
        sent = sent.strip()
        if sent and re.search(r'\d+', sent):
            if any(kw in sent for kw in ['سعر', 'تكلفة', 'ربح', 'دج', 'دينار', 'كغ', '%']):
                sentences_with_numbers.append(sent[:150])

    return {
        "financial_references": len(financial_matches),
        "sensitive_claims": len(sensitive_matches),
        "financial_sentences": sentences_with_numbers[:10],
        "raw_financial": list(set(str(m) for m in financial_matches))[:10]
    }

def check_terminology(text: str) -> dict:
    issues = []
    for wrong_term, correction in INCORRECT_TERMINOLOGY.items():
        if wrong_term in text:
            issues.append({"term": wrong_term, "correction": correction})
    return {"status": "WARNING" if issues else "PASS", "issues": issues}

def check_calculations(text: str) -> dict:
    issues = []
    warnings = []

    addition_pattern = r'(\d+[\.,]?\d*)\s*\+\s*(\d+[\.,]?\d*)\s*=\s*(\d+[\.,]?\d*)'
    for a, b, result in re.findall(addition_pattern, text):
        try:
            if abs((float(a.replace(',', '')) + float(b.replace(',', ''))) - float(result.replace(',', ''))) > 1:
                issues.append(f"حساب خاطئ: {a} + {b} ≠ {result}")
        except Exception:
            pass

    mult_pattern = r'(\d+[\.,]?\d*)\s*×\s*(\d+[\.,]?\d*)\s*=\s*(\d+[\.,]?\d*)'
    for a, b, result in re.findall(mult_pattern, text):
        try:
            r_val = float(result.replace(',', ''))
            if abs((float(a.replace(',', '')) * float(b.replace(',', ''))) - r_val) > r_val * 0.05:
                issues.append(f"حساب خاطئ: {a} × {b} ≠ {result}")
        except Exception:
            pass

    has_total_cost = bool(re.search(r'(إجمالي التكاليف|إجمالي التكلفة|المصاريف الإجمالية)', text))
    has_revenue = bool(re.search(r'(الإيرادات|العائد|إجمالي المبيعات)', text))
    has_profit = bool(re.search(r'(صافي الربح|الربح الصافي|هامش الربح)', text))

    if has_total_cost and has_revenue and not has_profit:
        warnings.append("⚠️ يوجد تكاليف وإيرادات لكن لا يوجد صافي ربح واضح")

    return {
        "status": "FAIL" if issues else "PASS",
        "issues": issues,
        "warnings": warnings,
        "has_total_cost": has_total_cost,
        "has_revenue": has_revenue,
        "has_profit": has_profit
    }

def check_content_depth(text: str, content_type: str, keyword: str = "") -> dict:
    words = len(text.split())
    issues = []
    warnings = []

    min_words = {
        'feasibility_study':     1200,
        'price_guide':           600,
        'how_to_guide':          900,
        'informational_article': 700,
        'commercial_guide':      900,
        'general_article':       500
    }

    required = min_words.get(content_type, 700)
    if words < required:
        issues.append(f"❌ المقال قصير للنوع '{content_type}': {words} كلمة (المطلوب: {required}+)")
    elif words < required * 1.2:
        warnings.append(f"⚠️ المقال قريب من الحد الأدنى: {words} كلمة")

    has_numbers = bool(re.search(r'\d+', text))
    if content_type in ['feasibility_study', 'price_guide'] and not has_numbers:
        issues.append("❌ دراسة الجدوى/الأسعار لا تحتوي على أرقام")

    return {
        "status": "FAIL" if issues else ("WARNING" if warnings else "PASS"),
        "word_count": words,
        "required_words": required,
        "issues": issues,
        "warnings": warnings,
        "has_numbers": has_numbers
    }

def needs_ai_review(text: str, content_type: str, numbers_data: dict) -> bool:
    if content_type in AI_REVIEW_REQUIRED_TYPES:
        return True
    if numbers_data['financial_references'] >= 3:
        return True
    if numbers_data['sensitive_claims'] >= 2:
        return True
    return False

def run_static_analysis(text: str, keyword: str = "",
                        content_type: str = "general_article") -> dict:
    numbers_data = extract_numbers_and_claims(text)
    terminology = check_terminology(text)
    calculations = check_calculations(text)
    depth = check_content_depth(text, content_type, keyword)
    ai_required = needs_ai_review(text, content_type, numbers_data)

    all_issues = []
    all_warnings = []
    all_issues.extend(calculations['issues'])
    all_issues.extend(depth['issues'])
    all_warnings.extend(calculations['warnings'])
    all_warnings.extend(depth['warnings'])

    if terminology['status'] == 'WARNING':
        for issue in terminology['issues']:
            all_warnings.append(f"مصطلح: {issue['term']} — {issue['correction']}")

    return {
        "layer": "static",
        "numbers": numbers_data,
        "terminology": terminology,
        "calculations": calculations,
        "depth": depth,
        "ai_review_required": ai_required,
        "issues": all_issues,
        "warnings": all_warnings,
        "static_passed": len(all_issues) == 0
    }

# ======================================================
# Layer 2 — AI Review
# ======================================================

AI_REVIEW_PROMPT = """أنت مدقق محتوى متخصص في المقالات الزراعية والبيطرية والمالية العربية.

مهمتك: مراجعة المقال وإعادة JSON فقط بدون أي نص خارجه.

الكلمة المفتاحية: {keyword}
نوع المحتوى: {content_type}

الأرقام المستخرجة:
{financial_sentences}

المقال:
---
{article}
---

أعد هذا JSON فقط:

{{"status":"PASS أو REVIEW أو REJECT","score":0-100,"facts":{{"verified":0,"unsupported":0,"uncertain":0,"details":[]}},"calculations":{{"status":"PASS أو WARNING أو FAIL","issues":[]}},"terminology":{{"status":"PASS أو WARNING أو FAIL","issues":[]}},"content_quality":{{"depth":"SHALLOW أو ADEQUATE أو DEEP","has_practical_info":true,"has_local_context":true}},"critical_issues":[],"recommendations":[]}}

قواعد:
- رقم بدون مصدر = unsupported
- رقم مع افتراض = uncertain
- حساب خاطئ = REJECT
- ادعاء طبي خاطئ = REJECT
- JSON فقط"""

def run_ai_review(text: str, keyword: str = "",
                  content_type: str = "", static_result: dict = None) -> dict:
    try:
        from config.settings import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODEL
        from openai import OpenAI

        if not OPENROUTER_API_KEY:
            return {"layer": "ai", "status": "SKIPPED", "reason": "AI غير متاح"}

        client = OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)

        financial_sentences = "\n".join(
            static_result.get('numbers', {}).get('financial_sentences', [])
            if static_result else []
        )

        # تقليص المقال لتوفير tokens وضمان JSON كامل
        article_preview = text[:2000] if len(text) > 2000 else text

        prompt = AI_REVIEW_PROMPT.format(
            keyword=keyword,
            content_type=content_type,
            financial_sentences=financial_sentences or "لا توجد أرقام",
            article=article_preview
        )

        response = client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500
        )

        raw = response.choices[0].message.content.strip()
        raw = re.sub(r'```json\s*', '', raw)
        raw = re.sub(r'```\s*', '', raw)
        raw = raw.strip()

        # استخرج أول JSON block
        json_match = re.search(r'\{[\s\S]*\}', raw)
        if json_match:
            raw = json_match.group(0)

        ai_result = json.loads(raw)
        ai_result['layer'] = 'ai'
        return ai_result

    except json.JSONDecodeError as e:
        return {
            "layer": "ai",
            "status": "REVIEW",
            "score": 60,
            "error": f"JSON parse error: {e}",
            "facts": {"verified": 0, "unsupported": 0, "uncertain": 0, "details": []},
            "calculations": {"status": "UNKNOWN", "issues": []},
            "terminology": {"status": "UNKNOWN", "issues": []},
            "content_quality": {"depth": "UNKNOWN"},
            "critical_issues": ["فشل في تحليل رد AI"],
            "recommendations": []
        }
    except Exception as e:
        return {"layer": "ai", "status": "SKIPPED", "reason": str(e)}

# ======================================================
# Final Decision — Deterministic
# ======================================================

def make_final_decision(static: dict, ai: dict,
                        base_seo_score: int = 100) -> dict:
    critical_issues = []
    warnings = list(static.get('warnings', []))
    score = base_seo_score

    if not static.get('static_passed'):
        for issue in static.get('issues', []):
            critical_issues.append(issue)
        score -= 20

    if ai.get('status') not in ['SKIPPED', None]:
        ai_score = ai.get('score', 100)
        score = int((score + ai_score) / 2)

        if ai.get('status') == 'REJECT':
            critical_issues.append("❌ AI Review: REJECT")

        calc = ai.get('calculations', {})
        if calc.get('status') == 'FAIL':
            for issue in calc.get('issues', []):
                critical_issues.append(f"❌ حساب خاطئ: {issue}")

        facts = ai.get('facts', {})
        unsupported = facts.get('unsupported', 0)
        if unsupported >= 3:
            critical_issues.append(f"❌ {unsupported} حقائق غير موثوقة — يتجاوز الحد المسموح")
        elif unsupported > 0:
            warnings.append(f"⚠️ {unsupported} حقيقة/حقائق غير موثوقة تحتاج مراجعة")

        term = ai.get('terminology', {})
        if term.get('status') == 'FAIL':
            for issue in term.get('issues', []):
                critical_issues.append(f"❌ مصطلح خاطئ: {issue}")
        elif term.get('status') == 'WARNING':
            for issue in term.get('issues', []):
                warnings.append(f"⚠️ مصطلح: {issue}")

        for issue in ai.get('critical_issues', []):
            critical_issues.append(f"❌ {issue}")

        for rec in ai.get('recommendations', []):
            warnings.append(f"💡 {rec}")

    if critical_issues:
        final_status = "REJECT"
        gate_status = TaskStatus.FAILED
    elif score >= 85:
        final_status = "PASS"
        gate_status = TaskStatus.READY_FOR_REVIEW
    elif score >= 65:
        final_status = "REVIEW"
        gate_status = TaskStatus.READY_FOR_REVIEW
    else:
        final_status = "REJECT"
        gate_status = TaskStatus.FAILED

    return {
        "final_status": final_status,
        "gate_status": gate_status,
        "passed": final_status in ["PASS", "REVIEW"],
        "score": score,
        "critical_issues": critical_issues,
        "warnings": warnings,
        "quality_gate": "PASSED" if final_status in ["PASS", "REVIEW"] else "FAILED"
    }

# ======================================================
# Main Entry Point
# ======================================================

def run_quality_gate_v2(
    article_text: str,
    keyword: str = "",
    content_type: str = "general_article",
    base_seo_result: dict = None
) -> dict:
    if not article_text or article_text.strip() == "":
        return {
            "final_status": "REJECT",
            "gate_status": TaskStatus.AI_UNAVAILABLE,
            "passed": False,
            "score": 0,
            "critical_issues": ["لا يوجد محتوى"],
            "warnings": [],
            "quality_gate": "FAILED"
        }

    base_seo_score = base_seo_result.get('score', 100) if base_seo_result else 100
    static_result = run_static_analysis(article_text, keyword, content_type)

    ai_result = {"layer": "ai", "status": "SKIPPED"}
    if static_result['ai_review_required']:
        ai_result = run_ai_review(article_text, keyword, content_type, static_result)

    decision = make_final_decision(static_result, ai_result, base_seo_score)

    return {
        **decision,
        "static_analysis": static_result,
        "ai_review": ai_result,
        "keyword": keyword,
        "content_type": content_type
    }

def print_quality_report_v2(result: dict):
    status = result['final_status']
    icons = {"PASS": "✅", "REVIEW": "⚠️", "REJECT": "❌"}
    icon = icons.get(status, "❓")

    print(f"\n{'=' * 60}")
    print(f"  Quality Gate V2 — {icon} {status}")
    print(f"{'=' * 60}")
    print(f"  Score        : {result['score']}/100")
    print(f"  Gate Status  : {result['quality_gate']}")

    static = result.get('static_analysis', {})
    print(f"\n  📊 Layer 1 — Static Analysis:")
    print(f"     Calculations : {static.get('calculations', {}).get('status', 'N/A')}")
    print(f"     Terminology  : {static.get('terminology', {}).get('status', 'N/A')}")
    print(f"     Depth        : {static.get('depth', {}).get('status', 'N/A')} ({static.get('depth', {}).get('word_count', 0)} كلمة)")
    print(f"     Fin. refs    : {static.get('numbers', {}).get('financial_references', 0)}")
    print(f"     AI Required  : {'نعم' if static.get('ai_review_required') else 'لا'}")

    ai = result.get('ai_review', {})
    if ai.get('status') not in ['SKIPPED', None]:
        print(f"\n  🤖 Layer 2 — AI Review:")
        print(f"     Status       : {ai.get('status', 'N/A')}")
        print(f"     Score        : {ai.get('score', 'N/A')}")
        facts = ai.get('facts', {})
        if facts:
            print(f"     Facts        : ✓{facts.get('verified',0)} / ⚠{facts.get('uncertain',0)} / ✗{facts.get('unsupported',0)}")
        content_q = ai.get('content_quality', {})
        if content_q:
            print(f"     Depth        : {content_q.get('depth', 'N/A')}")
    else:
        print(f"\n  🤖 Layer 2 — AI Review: SKIPPED")

    if result.get('critical_issues'):
        print(f"\n  ❌ Critical Issues ({len(result['critical_issues'])}):")
        for issue in result['critical_issues']:
            print(f"     {issue}")

    if result.get('warnings'):
        print(f"\n  ⚠️  Warnings ({len(result['warnings'])}):")
        for w in result['warnings'][:5]:
            print(f"     {w}")

    print(f"\n  {'=' * 58}")
    if status == "PASS":
        print(f"  ✅ المقال جاهز للمراجعة البشرية")
    elif status == "REVIEW":
        print(f"  ⚠️  المقال يحتاج مراجعة إضافية قبل النشر")
    else:
        print(f"  ❌ المقال مرفوض — يجب إصلاح المشاكل الحرجة")
    print(f"  {'=' * 58}")


if __name__ == "__main__":
    article_path = "outputs/تربية-الدجاج-في-الجزائر-2026/article.md"
    sample = open(article_path, encoding='utf-8').read() \
        if os.path.exists(article_path) else "نص قصير للاختبار"

    result = run_quality_gate_v2(
        article_text=sample,
        keyword="تربية الدجاج في الجزائر 2026",
        content_type="informational_article"
    )
    print_quality_report_v2(result)