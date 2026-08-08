import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.intent_agent import detect_intent, TaskStatus
from agents.content_brief import (
    generate_brief,
    check_content_gap,
    build_recommended_sections,
    get_internal_link_candidates
)

class TestContentGap:

    def test_no_gap_direct_match(self):
        existing = [{'title': 'تربية الدجاج في الجزائر', 'slug': 'test', 'keyword': '', 'status': 'published'}]
        result = check_content_gap("تربية الدجاج في الجزائر", existing)
        assert result['gap_type'] == "no_gap"
        assert result['recommendation'] == "improve_existing"

    def test_partial_gap(self):
        existing = [{'title': 'الدجاج في الجزائر', 'slug': 'test', 'keyword': '', 'status': 'published'}]
        result = check_content_gap("تربية الدجاج البياض في الجزائر 2026", existing)
        assert result['gap_type'] == "partial_gap"

    def test_full_gap_no_existing(self):
        result = check_content_gap("موضوع غير موجود في الموقع", [])
        assert result['gap_type'] == "full_gap"
        assert result['recommendation'] == "create_new"

    def test_gap_has_required_fields(self):
        result = check_content_gap("تربية الدجاج", [])
        required = ['gap_type', 'recommendation', 'gap_description', 'existing_count', 'direct_match']
        for field in required:
            assert field in result


class TestRecommendedSections:

    def test_intro_always_first(self):
        intent = detect_intent("تربية الدجاج في الجزائر 2026")
        sections = build_recommended_sections(intent)
        assert sections[0]['type'] == 'introduction'

    def test_conclusion_always_last(self):
        intent = detect_intent("تربية الدجاج في الجزائر 2026")
        sections = build_recommended_sections(intent)
        assert sections[-1]['type'] == 'conclusion'

    def test_sections_not_empty(self):
        intent = detect_intent("تربية الدجاج في الجزائر 2026")
        sections = build_recommended_sections(intent)
        assert len(sections) >= 3

    def test_faq_only_when_informational(self):
        intent = detect_intent("تربية الدجاج في الجزائر 2026")
        sections = build_recommended_sections(intent)
        faq_sections = [s for s in sections if s['type'] == 'faq']
        if faq_sections:
            assert intent['search_intent'] == 'informational'

    def test_local_section_when_is_local(self):
        intent = detect_intent("تربية الدجاج في الجزائر 2026")
        assert intent['is_local'] == True
        sections = build_recommended_sections(intent)
        headings = [s.get('heading', '') for s in sections]
        local_section = any('الجزائر' in h for h in headings)
        assert local_section


class TestBriefGeneration:

    def test_brief_has_required_fields(self):
        intent = detect_intent("تربية الدجاج في الجزائر 2026")
        brief = generate_brief(intent)
        required = [
            'keyword', 'intent', 'content_type', 'audience',
            'recommended_title', 'sections', 'questions_to_answer',
            'entities', 'internal_link_targets', 'freshness_requirements',
            'target_word_count', 'content_gap', 'seo_notes', 'status'
        ]
        for field in required:
            assert field in brief, f"حقل مفقود: {field}"

    def test_brief_status_is_ready(self):
        intent = detect_intent("تربية الدجاج في الجزائر 2026")
        brief = generate_brief(intent)
        assert brief['status'] == TaskStatus.BRIEF_READY

    def test_brief_keyword_matches(self):
        keyword = "سعر ماعز المورسيانو في الجزائر"
        intent = detect_intent(keyword)
        brief = generate_brief(intent)
        assert brief['keyword'] == keyword

    def test_sections_have_type(self):
        intent = detect_intent("تربية الدجاج في الجزائر 2026")
        brief = generate_brief(intent)
        for section in brief['sections']:
            assert 'type' in section

    def test_freshness_requirements_when_year_in_keyword(self):
        intent = detect_intent("تربية الدجاج في الجزائر 2026")
        brief = generate_brief(intent)
        assert len(brief['freshness_requirements']) > 0

    def test_no_freshness_requirements_without_year(self):
        intent = detect_intent("كيف تربي الماعز")
        brief = generate_brief(intent)
        assert len(brief['freshness_requirements']) == 0

    def test_seo_notes_not_empty(self):
        intent = detect_intent("تربية الدجاج في الجزائر 2026")
        brief = generate_brief(intent)
        assert len(brief['seo_notes']) >= 4

    def test_target_word_count_not_empty(self):
        intent = detect_intent("تربية الدجاج في الجزائر 2026")
        brief = generate_brief(intent)
        assert brief['target_word_count'] != ""