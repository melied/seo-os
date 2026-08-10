import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.quality_gate_v2 import (
    run_static_analysis,
    extract_numbers_and_claims,
    check_terminology,
    check_calculations,
    check_content_depth,
    needs_ai_review,
    make_final_decision,
    run_quality_gate_v2
)
from agents.intent_agent import TaskStatus

GOOD_ARTICLE = """
# تربية الدجاج في الجزائر: دليل شامل 2026

تربية الدجاج في الجزائر من أكثر المشاريع الزراعية انتشاراً وربحاً في السنوات الأخيرة.
يبحث كثير من الشباب الجزائري عن مشاريع زراعية مربحة، وتربية الدجاج تعد من أفضل الخيارات.

## أنواع وسلالات الدجاج

هناك عدة سلالات مناسبة للتربية في الجزائر. السلالات المحلية تتميز بمقاومتها للأمراض.
أما السلالات المستوردة مثل الكوب فتتميز بسرعة النمو وزيادة الوزن في وقت قصير.

## تجهيز الحظيرة

يحتاج كل دجاج إلى مساحة مناسبة في التربية المكثفة.
الحظيرة يجب أن تكون جيدة التهوية مع إضاءة مناسبة وحماية من البرد والحر.

## التغذية والأعلاف

تحتاج الدجاجة يومياً إلى كمية مناسبة من العلف حسب مرحلة النمو.
أسعار الأعلاف في الجزائر تتراوح بين 3500 و4500 دينار للقنطار حسب النوع.

## التكاليف والأرباح

مثال حسابي افتراضي: إذا افترضنا سعر الصوص بـ 120 دج فإن تكلفة 1000 صوص تبلغ 120,000 دج.
يجب استبدال هذا الافتراض بالسعر الفعلي من السوق عند إعداد دراسة الجدوى الحقيقية.

## الأخطاء الشائعة

أكثر الأخطاء شيوعاً هي الاكتظاظ في الحظيرة مما يؤدي إلى انتشار الأمراض بسرعة.
إهمال التطعيم في الأوقات المحددة يتسبب في خسائر كبيرة للمربي.

## الخاتمة

تربية الدجاج في الجزائر مشروع مربح يستحق الدراسة والتخطيط الجيد.
ابدأ بعدد صغير ثم وسع تدريجياً بناءً على خبرتك وإمكانياتك المادية.
""" * 2

SHORT_ARTICLE = "نص قصير جداً لا يكفي"

ARTICLE_WITH_BAD_TERMS = """
# مقال عن الدجاج

هذا مقال طويل بما يكفي للاختبار ويحتوي على محتوى كافٍ للتحقق منه.

## الأمراض

يجب التطعيم ضد الآجي والجمبورو. التحصيم ضروري في الأسبوع الأول.

## التغذية

العلف مهم جداً لنمو الدجاج وتطوره في المراحل المختلفة.

## الخاتمة

مشروع مربح يحتاج تخطيطاً جيداً وخبرة كافية.
""" * 3

ARTICLE_WITH_BAD_CALC = """
# دراسة جدوى

مشروع تربية الدواجن في الجزائر مشروع مربح ويستحق الدراسة الجادة.

## التكاليف

تكلفة الصيصان: 100,000 دج
تكلفة العلف: 200,000 دج
100,000 + 200,000 = 400,000 دج

## الخاتمة

مشروع ممتاز للاستثمار في الجزائر.
""" * 2


class TestExtractNumbers:

    def test_detects_financial_references(self):
        text = "سعر الصوص 120 دج وتكلفة العلف 450,000 دج"
        result = extract_numbers_and_claims(text)
        assert result['financial_references'] > 0

    def test_detects_sensitive_claims(self):
        text = "هذا أفضل مشروع وربح مؤكد بدون خسارة"
        result = extract_numbers_and_claims(text)
        assert result['sensitive_claims'] > 0

    def test_extracts_financial_sentences(self):
        text = "سعر الكيلو 350 دج في السوق المحلي."
        result = extract_numbers_and_claims(text)
        assert len(result['financial_sentences']) > 0

    def test_clean_text_has_zero_sensitive(self):
        text = "تربية الدجاج مشروع جيد يحتاج تخطيطاً."
        result = extract_numbers_and_claims(text)
        assert result['sensitive_claims'] == 0


class TestTerminology:

    def test_detects_wrong_term(self):
        result = check_terminology("يجب التطعيم ضد الآجي")
        assert result['status'] == 'WARNING'
        assert len(result['issues']) > 0

    def test_detects_tahseem(self):
        result = check_terminology("التحصيم ضروري في الأسبوع الأول")
        assert result['status'] == 'WARNING'

    def test_clean_text_passes(self):
        result = check_terminology("يجب التطعيم ضد إنفلونزا الطيور")
        assert result['status'] == 'PASS'
        assert len(result['issues']) == 0

    def test_multiple_wrong_terms(self):
        result = check_terminology("الآجي والتحصيم من أهم المصطلحات")
        assert len(result['issues']) >= 2


class TestCalculations:

    def test_correct_addition_passes(self):
        result = check_calculations("100 + 200 = 300 دج إجمالي")
        assert result['status'] == 'PASS'

    def test_wrong_addition_fails(self):
        result = check_calculations("100 + 200 = 400 دج إجمالي")
        assert result['status'] == 'FAIL'
        assert len(result['issues']) > 0

    def test_correct_multiplication_passes(self):
        result = check_calculations("1000 × 120 = 120000 دج")
        assert result['status'] == 'PASS'

    def test_no_calculations_passes(self):
        result = check_calculations("نص بدون أي حسابات رياضية")
        assert result['status'] == 'PASS'

    def test_detects_missing_profit(self):
        text = "إجمالي التكاليف 500,000 دج. الإيرادات 700,000 دج."
        result = check_calculations(text)
        assert len(result['warnings']) > 0


class TestContentDepth:

    def test_short_article_fails(self):
        result = check_content_depth("نص قصير", "informational_article")
        assert result['status'] == 'FAIL'

    def test_long_article_passes(self):
        long_text = "كلمة " * 900
        result = check_content_depth(long_text, "informational_article")
        assert result['status'] == 'PASS'

    def test_feasibility_requires_more_words(self):
        medium_text = "كلمة " * 900
        info_result = check_content_depth(medium_text, "informational_article")
        feasibility_result = check_content_depth(medium_text, "feasibility_study")
        assert info_result['required_words'] < feasibility_result['required_words']

    def test_word_count_returned(self):
        text = "كلمة " * 100
        result = check_content_depth(text, "general_article")
        assert result['word_count'] == 100


class TestNeedsAIReview:

    def test_informational_requires_ai(self):
        numbers = {"financial_references": 0, "sensitive_claims": 0}
        assert needs_ai_review("", "informational_article", numbers) == True

    def test_feasibility_requires_ai(self):
        numbers = {"financial_references": 0, "sensitive_claims": 0}
        assert needs_ai_review("", "feasibility_study", numbers) == True

    def test_many_financial_refs_requires_ai(self):
        numbers = {"financial_references": 5, "sensitive_claims": 0}
        assert needs_ai_review("", "general_article", numbers) == True

    def test_simple_article_no_ai(self):
        numbers = {"financial_references": 0, "sensitive_claims": 0}
        assert needs_ai_review("", "general_article", numbers) == False


class TestStaticAnalysis:

    def test_returns_required_fields(self):
        result = run_static_analysis("نص اختبار", "كلمة", "general_article")
        required = ['layer', 'numbers', 'terminology', 'calculations',
                    'depth', 'ai_review_required', 'issues', 'warnings', 'static_passed']
        for field in required:
            assert field in result, f"حقل مفقود: {field}"

    def test_bad_calc_not_static_passed(self):
        result = run_static_analysis(ARTICLE_WITH_BAD_CALC, "", "feasibility_study")
        assert result['static_passed'] == False

    def test_wrong_terms_in_warnings(self):
        result = run_static_analysis(ARTICLE_WITH_BAD_TERMS, "", "informational_article")
        assert len(result['warnings']) > 0


class TestMakeFinalDecision:

    def test_no_issues_high_score_pass(self):
        static = {"static_passed": True, "issues": [], "warnings": []}
        ai = {"status": "SKIPPED"}
        result = make_final_decision(static, ai, base_seo_score=90)
        assert result['final_status'] == "PASS"

    def test_critical_issue_rejects(self):
        static = {"static_passed": False, "issues": ["❌ خطأ"], "warnings": []}
        ai = {"status": "SKIPPED"}
        result = make_final_decision(static, ai, base_seo_score=90)
        assert result['final_status'] == "REJECT"

    def test_ai_reject_causes_reject(self):
        static = {"static_passed": True, "issues": [], "warnings": []}
        ai = {
            "status": "REJECT",
            "score": 40,
            "calculations": {"status": "PASS", "issues": []},
            "facts": {"unsupported": 0},
            "terminology": {"status": "PASS", "issues": []},
            "critical_issues": ["حساب خاطئ"],
            "recommendations": []
        }
        result = make_final_decision(static, ai, base_seo_score=90)
        assert result['final_status'] == "REJECT"

    def test_many_unsupported_facts_rejects(self):
        static = {"static_passed": True, "issues": [], "warnings": []}
        ai = {
            "status": "REVIEW",
            "score": 70,
            "calculations": {"status": "PASS", "issues": []},
            "facts": {"unsupported": 4},
            "terminology": {"status": "PASS", "issues": []},
            "critical_issues": [],
            "recommendations": []
        }
        result = make_final_decision(static, ai, base_seo_score=90)
        assert result['final_status'] == "REJECT"

    def test_medium_score_review(self):
        static = {"static_passed": True, "issues": [], "warnings": []}
        ai = {
            "status": "REVIEW",
            "score": 70,
            "calculations": {"status": "PASS", "issues": []},
            "facts": {"unsupported": 0},
            "terminology": {"status": "PASS", "issues": []},
            "critical_issues": [],
            "recommendations": []
        }
        result = make_final_decision(static, ai, base_seo_score=80)
        assert result['final_status'] == "REVIEW"

    def test_passed_is_true_for_pass(self):
        static = {"static_passed": True, "issues": [], "warnings": []}
        ai = {"status": "SKIPPED"}
        result = make_final_decision(static, ai, base_seo_score=90)
        assert result['passed'] == True

    def test_passed_is_false_for_reject(self):
        static = {"static_passed": False, "issues": ["❌ خطأ"], "warnings": []}
        ai = {"status": "SKIPPED"}
        result = make_final_decision(static, ai, base_seo_score=90)
        assert result['passed'] == False


class TestRunQualityGateV2:

    def test_empty_text_rejects(self):
        result = run_quality_gate_v2("")
        assert result['final_status'] == "REJECT"
        assert result['passed'] == False

    def test_none_text_rejects(self):
        result = run_quality_gate_v2(None)
        assert result['final_status'] == "REJECT"

    def test_returns_required_fields(self):
        result = run_quality_gate_v2(SHORT_ARTICLE, content_type="general_article")
        required = ['final_status', 'gate_status', 'passed',
                    'score', 'critical_issues', 'warnings', 'quality_gate']
        for field in required:
            assert field in result, f"حقل مفقود: {field}"

    def test_wrong_calc_fails(self):
        result = run_quality_gate_v2(
            ARTICLE_WITH_BAD_CALC * 3,
            content_type="feasibility_study"
        )
        assert result['passed'] == False

    def test_quality_gate_field_matches_passed(self):
        result = run_quality_gate_v2(SHORT_ARTICLE)
        if result['passed']:
            assert result['quality_gate'] == "PASSED"
        else:
            assert result['quality_gate'] == "FAILED"