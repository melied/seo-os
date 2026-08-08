import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.intent_agent import TaskStatus
from agents.quality_gate import run_quality_gate
from tests.test_validators import FULL_ARTICLE, ARTICLE_WITH_PLACEHOLDERS

VALID_SCHEMA = {
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": "تربية الدجاج في الجزائر: دليل شامل 2026",
    "description": "دليل شامل لتربية الدجاج في الجزائر",
    "author": {"@type": "Organization", "name": "الثروة الحيوانية"},
    "datePublished": "2026-08-08",
    "dateModified": "2026-08-08",
    "url": "https://www.news-theworld.com/2026/chicken-farming.html"
}


class TestQualityGatePass:

    def test_full_article_passes(self):
        result = run_quality_gate(
            FULL_ARTICLE,
            keyword="تربية الدجاج في الجزائر",
            schema=VALID_SCHEMA,
            meta_title="تربية الدجاج في الجزائر: دليل شامل 2026",
            meta_description="كل ما تحتاجه لبدء مشروع تربية الدجاج في الجزائر.",
            slug="chicken-farming-algeria-2026"
        )
        assert result['quality_gate'] == "PASSED"
        assert result['status'] == TaskStatus.READY_FOR_REVIEW
        assert result['passed'] == True
        assert len(result['critical_issues']) == 0

    def test_score_is_high_for_full_article(self):
        result = run_quality_gate(
            FULL_ARTICLE,
            keyword="تربية الدجاج في الجزائر",
            schema=VALID_SCHEMA,
            meta_title="تربية الدجاج في الجزائر 2026",
            meta_description="دليل شامل لتربية الدجاج.",
            slug="chicken-farming-algeria"
        )
        assert result['score'] >= 80

    def test_result_has_required_fields(self):
        result = run_quality_gate(FULL_ARTICLE)
        required = ['status', 'passed', 'critical_issues',
                    'warnings', 'checks', 'score', 'quality_gate']
        for field in required:
            assert field in result, f"حقل مفقود: {field}"


class TestQualityGateFail:

    def test_empty_text_returns_ai_unavailable(self):
        result = run_quality_gate("")
        assert result['status'] == TaskStatus.AI_UNAVAILABLE
        assert result['passed'] == False
        assert result['score'] == 0

    def test_none_text_returns_ai_unavailable(self):
        result = run_quality_gate(None)
        assert result['status'] == TaskStatus.AI_UNAVAILABLE

    def test_placeholder_article_fails(self):
        result = run_quality_gate(ARTICLE_WITH_PLACEHOLDERS)
        assert result['quality_gate'] == "FAILED"
        assert result['status'] == TaskStatus.FAILED
        assert result['passed'] == False

    def test_short_text_fails(self):
        result = run_quality_gate("نص قصير جداً")
        assert result['quality_gate'] == "FAILED"
        assert result['passed'] == False

    def test_missing_meta_title_fails(self):
        result = run_quality_gate(
            FULL_ARTICLE,
            meta_title="",
            meta_description="وصف كافٍ للمقال يتجاوز الحد الأدنى",
            slug="test-slug"
        )
        assert result['quality_gate'] == "FAILED"
        assert any('Meta Title' in i for i in result['critical_issues'])

    def test_invalid_schema_fails(self):
        bad_schema = {"@type": "Article"}
        result = run_quality_gate(
            FULL_ARTICLE,
            keyword="تربية الدجاج",
            schema=bad_schema,
            meta_title="تربية الدجاج في الجزائر 2026",
            meta_description="دليل شامل لتربية الدجاج في الجزائر من الصفر.",
            slug="chicken-farming"
        )
        assert result['quality_gate'] == "FAILED"


class TestQualityGateChecks:

    def test_checks_dict_present(self):
        result = run_quality_gate(FULL_ARTICLE)
        assert isinstance(result['checks'], dict)
        assert len(result['checks']) > 0

    def test_keyword_present_check(self):
        result = run_quality_gate(
            FULL_ARTICLE,
            keyword="تربية الدجاج",
            meta_title="تربية الدجاج 2026",
            meta_description="دليل شامل لتربية الدجاج في الجزائر.",
            slug="chicken-farming"
        )
        assert result['checks'].get('keyword_present') == True

    def test_keyword_absent_adds_warning(self):
        result = run_quality_gate(
            FULL_ARTICLE,
            keyword="موضوع غير موجود في النص أبداً xyz",
            meta_title="عنوان المقال الكامل هنا",
            meta_description="وصف المقال الكامل هنا يتجاوز الخمسين حرفاً.",
            slug="test-slug"
        )
        assert any('الكلمة المفتاحية' in w for w in result['warnings'])

    def test_word_count_in_result(self):
        result = run_quality_gate(FULL_ARTICLE)
        assert result.get('word_count', 0) > 0

    def test_headings_in_result(self):
        result = run_quality_gate(FULL_ARTICLE)
        headings = result.get('headings', {})
        assert 'h1' in headings
        assert 'h2' in headings


class TestQualityGateStatus:

    def test_passed_article_status_ready(self):
        result = run_quality_gate(
            FULL_ARTICLE,
            meta_title="تربية الدجاج في الجزائر 2026",
            meta_description="دليل شامل لتربية الدجاج في الجزائر من الصفر حتى الربح.",
            slug="chicken-farming-algeria"
        )
        assert result['status'] == TaskStatus.READY_FOR_REVIEW

    def test_failed_article_status_failed(self):
        result = run_quality_gate("نص قصير")
        assert result['status'] == TaskStatus.FAILED

    def test_empty_article_status_ai_unavailable(self):
        result = run_quality_gate("")
        assert result['status'] == TaskStatus.AI_UNAVAILABLE