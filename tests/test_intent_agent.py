import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.intent_agent import detect_intent, SearchIntent, TaskStatus

class TestIntentDetection:

    def test_informational_intent(self):
        result = detect_intent("تربية الدجاج في الجزائر 2026")
        assert result['search_intent'] == SearchIntent.INFORMATIONAL

    def test_commercial_intent(self):
        result = detect_intent("سعر ماعز المورسيانو في الجزائر")
        assert result['search_intent'] == SearchIntent.COMMERCIAL

    def test_commercial_intent_cost(self):
        result = detect_intent("تكلفة مشروع تربية الدواجن")
        assert result['search_intent'] in [SearchIntent.COMMERCIAL, SearchIntent.MIXED]

    def test_freshness_required(self):
        result = detect_intent("تربية الدجاج في الجزائر 2026")
        assert result['freshness_required'] == True

    def test_no_freshness(self):
        result = detect_intent("كيف تربي الماعز")
        assert result['freshness_required'] == False

    def test_is_local(self):
        result = detect_intent("تربية الدجاج في الجزائر")
        assert result['is_local'] == True

    def test_not_local(self):
        result = detect_intent("تربية الدجاج")
        assert result['is_local'] == False

    def test_subtopics_not_empty_for_chicken(self):
        result = detect_intent("تربية الدجاج في الجزائر")
        assert len(result['important_subtopics']) > 0

    def test_questions_not_empty(self):
        result = detect_intent("تربية الدجاج في الجزائر")
        assert len(result['questions']) > 0

    def test_content_type_price_guide(self):
        result = detect_intent("سعر الدجاج في الجزائر 2026")
        assert result['content_type'] == "price_guide"

    def test_content_type_feasibility(self):
        result = detect_intent("دراسة جدوى مشروع تربية الدجاج")
        assert result['content_type'] == "feasibility_study"

    def test_required_fields_present(self):
        result = detect_intent("تربية الماعز")
        required = [
            'primary_keyword', 'search_intent', 'content_type',
            'user_goal', 'important_subtopics', 'questions',
            'commercial_angle', 'freshness_required', 'is_local', 'status'
        ]
        for field in required:
            assert field in result, f"حقل مفقود: {field}"

    def test_status_is_researching(self):
        result = detect_intent("تربية الدجاج")
        assert result['status'] == TaskStatus.RESEARCHING