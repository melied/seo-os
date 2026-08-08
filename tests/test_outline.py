import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.intent_agent import detect_intent, TaskStatus
from agents.content_brief import generate_brief
from agents.outline_generator import (
    build_outline_from_brief,
    _validate_outline,
    _generate_h1,
    _generate_meta_title
)

def make_outline(keyword="تربية الدجاج في الجزائر 2026"):
    intent = detect_intent(keyword)
    brief = generate_brief(intent)
    return build_outline_from_brief(brief), brief

class TestOutlineStructure:

    def test_has_required_fields(self):
        outline, _ = make_outline()
        required = ['keyword', 'intent', 'h1', 'meta_title_suggestion',
                    'sections', 'internal_link_candidates',
                    'target_word_count', 'status', 'validation']
        for field in required:
            assert field in outline, f"حقل مفقود: {field}"

    def test_status_is_outline_ready(self):
        outline, _ = make_outline()
        assert outline['status'] == TaskStatus.OUTLINE_READY

    def test_intro_is_first(self):
        outline, _ = make_outline()
        assert outline['sections'][0]['type'] == 'introduction'

    def test_conclusion_is_last(self):
        outline, _ = make_outline()
        assert outline['sections'][-1]['type'] == 'conclusion'

    def test_has_at_least_one_h2(self):
        outline, _ = make_outline()
        h2s = [s for s in outline['sections'] if s['type'] == 'h2']
        assert len(h2s) >= 2

    def test_h1_not_equal_keyword(self):
        keyword = "تربية الدجاج في الجزائر 2026"
        outline, _ = make_outline(keyword)
        assert outline['h1'] != keyword

    def test_h1_not_empty(self):
        outline, _ = make_outline()
        assert outline['h1'] != ""
        assert len(outline['h1']) > 10

    def test_meta_title_no_duplicate_year(self):
        outline, _ = make_outline("تربية الدجاج في الجزائر 2026")
        title = outline['meta_title_suggestion']
        assert title.count('2026') <= 1

    def test_meta_title_length(self):
        outline, _ = make_outline()
        title = outline['meta_title_suggestion']
        assert len(title) <= 65

    def test_faq_max_one(self):
        outline, _ = make_outline()
        faqs = [s for s in outline['sections'] if s['type'] == 'faq']
        assert len(faqs) <= 1

    def test_sections_have_writing_notes(self):
        outline, _ = make_outline()
        for s in outline['sections']:
            assert 'writing_notes' in s, f"writing_notes مفقود في: {s['type']}"


class TestOutlineValidation:

    def test_valid_outline_passes(self):
        sections = [
            {'type': 'introduction', 'h2': None, 'writing_notes': '', 'word_count': '100'},
            {'type': 'h2', 'h2': 'قسم 1', 'writing_notes': '', 'word_count': '200'},
            {'type': 'h2', 'h2': 'قسم 2', 'writing_notes': '', 'word_count': '200'},
            {'type': 'conclusion', 'h2': 'خاتمة', 'writing_notes': '', 'word_count': '100'},
        ]
        result = _validate_outline(sections, "كلمة مفتاحية")
        assert result['is_valid'] == True
        assert len(result['issues']) == 0

    def test_missing_intro_fails(self):
        sections = [
            {'type': 'h2', 'h2': 'قسم 1', 'writing_notes': '', 'word_count': '200'},
            {'type': 'conclusion', 'h2': 'خاتمة', 'writing_notes': '', 'word_count': '100'},
        ]
        result = _validate_outline(sections, "كلمة")
        assert result['is_valid'] == False

    def test_missing_conclusion_fails(self):
        sections = [
            {'type': 'introduction', 'h2': None, 'writing_notes': '', 'word_count': '100'},
            {'type': 'h2', 'h2': 'قسم 1', 'writing_notes': '', 'word_count': '200'},
        ]
        result = _validate_outline(sections, "كلمة")
        assert result['is_valid'] == False

    def test_too_few_h2_fails(self):
        sections = [
            {'type': 'introduction', 'h2': None, 'writing_notes': '', 'word_count': '100'},
            {'type': 'h2', 'h2': 'قسم وحيد', 'writing_notes': '', 'word_count': '200'},
            {'type': 'conclusion', 'h2': 'خاتمة', 'writing_notes': '', 'word_count': '100'},
        ]
        result = _validate_outline(sections, "كلمة")
        assert result['is_valid'] == False

    def test_too_many_h2_warns(self):
        sections = [{'type': 'introduction', 'writing_notes': '', 'word_count': '100'}]
        for i in range(9):
            sections.append({'type': 'h2', 'h2': f'قسم {i}', 'writing_notes': '', 'word_count': '200'})
        sections.append({'type': 'conclusion', 'h2': 'خاتمة', 'writing_notes': '', 'word_count': '100'})
        result = _validate_outline(sections, "كلمة")
        assert any('كبير' in w for w in result['warnings'])