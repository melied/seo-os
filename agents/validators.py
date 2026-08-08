import re
import sys
import os
import json as _json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ======================================================
# Placeholder Validator
# ======================================================

PLACEHOLDER_PATTERNS = [
    r'\[اكتب[^\]]*\]',
    r'\[أضف[^\]]*\]',
    r'\[أدخل[^\]]*\]',
    r'\[ضع[^\]]*\]',
    r'\[هنا[^\]]*\]',
    r'\[المحتوى[^\]]*\]',
    r'\[النص[^\]]*\]',
    r'\[الإجابة[^\]]*\]',
    r'\[TODO[^\]]*\]',
    r'\[FIXME[^\]]*\]',
    r'\[TBD[^\]]*\]',
    r'TODO',
    r'FIXME',
    r'Lorem ipsum',
    r'\*ملاحظة[^*]*\*',
    r'\*ملاحظة للكاتب[^*]*\*',
    r'اكتب المقدمة هنا',
    r'اكتب المحتوى هنا',
    r'اكتب الخاتمة هنا',
]

AI_SELF_REFERENCE_PATTERNS = [
    r'سأكتب لك',
    r'سأقدم لك',
    r'في هذا المقال سأ',
    r'دعني أ',
    r'يمكنني أن',
    r'كمساعد',
    r'كنموذج',
]

def find_placeholders(text: str) -> list:
    found = []
    for pattern in PLACEHOLDER_PATTERNS:
        matches = re.findall(pattern, text, re.UNICODE)
        for match in matches:
            if match not in found:
                found.append(match)
    return found

def find_ai_self_references(text: str) -> list:
    found = []
    for pattern in AI_SELF_REFERENCE_PATTERNS:
        matches = re.findall(pattern, text, re.UNICODE)
        found.extend(matches)
    return found

def validate_no_placeholders(text: str) -> dict:
    placeholders = find_placeholders(text)
    ai_refs = find_ai_self_references(text)
    issues = []
    if placeholders:
        issues.extend([f"Placeholder: {p}" for p in placeholders])
    if ai_refs:
        issues.extend([f"AI self-reference: {r}" for r in ai_refs])
    return {
        "passed": len(issues) == 0,
        "placeholders_found": placeholders,
        "ai_references_found": ai_refs,
        "issues": issues
    }


# ======================================================
# Article Validator
# ======================================================

def count_headings(text: str) -> dict:
    h1 = re.findall(r'^# [^#]', text, re.MULTILINE)
    h2 = re.findall(r'^## [^#]', text, re.MULTILINE)
    h3 = re.findall(r'^### [^#]', text, re.MULTILINE)
    return {'h1': len(h1), 'h2': len(h2), 'h3': len(h3)}

def find_duplicate_headings(text: str) -> list:
    headings = re.findall(r'^#{1,3} (.+)$', text, re.MULTILINE)
    seen = []
    duplicates = []
    for h in headings:
        h_clean = h.strip().lower()
        if h_clean in seen:
            duplicates.append(h.strip())
        else:
            seen.append(h_clean)
    return duplicates

def has_introduction(text: str) -> bool:
    lines = text.strip().split('\n')
    content_before_h2 = []
    for line in lines:
        if line.startswith('## '):
            break
        if line.strip() and not line.startswith('#'):
            content_before_h2.append(line)
    return len(content_before_h2) >= 2

def has_conclusion(text: str) -> bool:
    conclusion_patterns = ['## خاتمة', '## الخاتمة', '## ختاماً', '## في الختام']
    for pattern in conclusion_patterns:
        if pattern in text:
            return True
    lines = [l for l in text.strip().split('\n') if l.strip()]
    return len(lines) > 5

def is_full_article(text: str, min_words: int = 300) -> bool:
    """التحقق من أن النص مقال كامل وليس Outline"""
    clean = re.sub(r'^#{1,3} .+$', '', text, flags=re.MULTILINE)
    clean = re.sub(r'```[\s\S]*?```', '', clean)
    clean = re.sub(r'\*\*[^*]+\*\*\s*:.*', '', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    words = [w for w in clean.split() if len(w) > 1]
    return len(words) >= min_words

def check_keyword_density(text: str, keyword: str) -> dict:
    """فحص كثافة الكلمة المفتاحية"""
    clean = re.sub(r'```[\s\S]*?```', '', text)
    clean = re.sub(r'^#{1,3} .+$', '', clean, flags=re.MULTILINE)
    clean = re.sub(r'\s+', ' ', clean).strip()
    words = clean.split()
    total_words = len(words)

    if total_words == 0:
        return {"density": 0, "count": 0, "total_words": 0, "warning": False}

    keyword_lower = keyword.lower()
    count = clean.lower().count(keyword_lower)

    keyword_word_count = len(keyword.split())
    effective_words = total_words / keyword_word_count if keyword_word_count > 1 else total_words
    density = (count / effective_words) * 100 if effective_words > 0 else 0

    return {
        "density": round(density, 2),
        "count": count,
        "total_words": total_words,
        "warning": density > 4.0
    }

def validate_article(text: str, keyword: str = "") -> dict:
    issues = []
    warnings = []

    if not is_full_article(text, min_words=300):
        issues.append("❌ النص قصير جداً أو ليس مقالاً كاملاً (أقل من 300 كلمة)")

    if not has_introduction(text):
        issues.append("❌ المقدمة مفقودة أو قصيرة جداً")

    if not has_conclusion(text):
        warnings.append("⚠️  الخاتمة غير واضحة")

    headings = count_headings(text)
    if headings['h1'] > 1:
        issues.append(f"❌ يوجد {headings['h1']} عناوين H1 — يجب أن يكون واحداً فقط")

    if headings['h2'] < 2:
        issues.append("❌ عدد الأقسام الرئيسية أقل من 2")

    duplicates = find_duplicate_headings(text)
    if duplicates:
        issues.append(f"❌ عناوين مكررة: {', '.join(duplicates)}")

    placeholder_check = validate_no_placeholders(text)
    if not placeholder_check['passed']:
        for issue in placeholder_check['issues']:
            issues.append(f"❌ {issue}")

    if keyword:
        density = check_keyword_density(text, keyword)
        if density['warning']:
            warnings.append(f"⚠️  كثافة الكلمة المفتاحية مرتفعة: {density['density']}%")
        if density['count'] == 0:
            warnings.append(f"⚠️  الكلمة المفتاحية غير موجودة في المقال")

    return {
        "passed": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "headings": headings,
        "word_count": len(text.split()),
        "placeholder_check": placeholder_check
    }


# ======================================================
# Schema Validator
# ======================================================

REQUIRED_SCHEMA_FIELDS = [
    '@context', '@type', 'headline',
    'description', 'author', 'datePublished', 'dateModified', 'url'
]

INVALID_SCHEMA_VALUES = [
    'undefined', 'null', 'TODO', 'FIXME',
    '[', 'placeholder', 'test'
]

def validate_schema(schema_data) -> dict:
    issues = []
    warnings = []

    if isinstance(schema_data, str):
        try:
            schema_data = _json.loads(schema_data)
        except Exception:
            return {
                "passed": False,
                "issues": ["❌ Schema ليس JSON صالحاً"],
                "warnings": []
            }

    for field in REQUIRED_SCHEMA_FIELDS:
        if field not in schema_data:
            issues.append(f"❌ حقل مفقود في Schema: {field}")
        else:
            value = str(schema_data[field])
            for invalid in INVALID_SCHEMA_VALUES:
                if invalid.lower() in value.lower():
                    issues.append(f"❌ قيمة غير صالحة في {field}: {value[:50]}")

    if '@type' in schema_data:
        valid_types = ['Article', 'FAQPage', 'BlogPosting', 'NewsArticle']
        if schema_data['@type'] not in valid_types:
            warnings.append(f"⚠️  نوع Schema غير معروف: {schema_data['@type']}")

    return {
        "passed": len(issues) == 0,
        "issues": issues,
        "warnings": warnings
    }


# ======================================================
# Run All
# ======================================================

def run_all_validations(text: str, keyword: str = "", schema=None) -> dict:
    article_result = validate_article(text, keyword)
    schema_result = validate_schema(schema) if schema else {"passed": True, "issues": [], "warnings": []}
    all_passed = article_result['passed'] and schema_result['passed']
    return {
        "quality_gate": "PASSED" if all_passed else "FAILED",
        "article": article_result,
        "schema": schema_result
    }

def print_validation_report(result: dict):
    gate = result['quality_gate']
    icon = "✅" if gate == "PASSED" else "❌"
    print(f"\n{'=' * 55}")
    print(f"     Validation Report — {icon} {gate}")
    print(f"{'=' * 55}")

    art = result['article']
    print(f"\n  📄 Article Validation:")
    print(f"     الكلمات: {art.get('word_count', 0)}")
    print(f"     H1: {art['headings']['h1']} | H2: {art['headings']['h2']} | H3: {art['headings']['h3']}")

    if art['issues']:
        print(f"\n  ❌ مشاكل حرجة:")
        for issue in art['issues']:
            print(f"     {issue}")

    if art['warnings']:
        print(f"\n  ⚠️  تحذيرات:")
        for w in art['warnings']:
            print(f"     {w}")

    sch = result['schema']
    print(f"\n  📋 Schema Validation: {'✅ صالح' if sch['passed'] else '❌ يحتوي أخطاء'}")
    for issue in sch['issues']:
        print(f"     {issue}")

    print(f"\n  النتيجة النهائية: {icon} QUALITY_GATE = {gate}")
    print(f"{'=' * 55}")


if __name__ == "__main__":
    test_text = """
# تربية الدجاج في الجزائر: دليل شامل

تربية الدجاج في الجزائر من أكثر المشاريع انتشاراً. في هذا المقال ستجد كل ما تحتاجه.

## أنواع الدجاج
هناك عدة أنواع من الدجاج المناسبة للتربية في الجزائر.

## التكاليف والأرباح
تتراوح تكلفة تربية 1000 دجاجة بين 200,000 و300,000 دينار جزائري.

## الخاتمة
تربية الدجاج مشروع مربح إذا أحسنت التخطيط.
"""
    result = run_all_validations(test_text, "تربية الدجاج في الجزائر")
    print_validation_report(result)