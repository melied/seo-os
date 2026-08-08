import sys
import os
import pytest
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.intent_agent import TaskStatus
from agents.pipeline import run_pipeline, save_to_filesystem, get_ai_provider


class TestPipelineStates:

    def test_pipeline_returns_dict(self):
        result = run_pipeline("تربية الدجاج في الجزائر", save_files=False)
        assert isinstance(result, dict)

    def test_pipeline_has_required_fields(self):
        result = run_pipeline("تربية الدجاج في الجزائر", save_files=False)
        required = ['keyword', 'status', 'stages_completed', 'files', 'errors']
        for field in required:
            assert field in result, f"حقل مفقود: {field}"

    def test_pipeline_keyword_matches(self):
        keyword = "سعر ماعز المورسيانو في الجزائر"
        result = run_pipeline(keyword, save_files=False)
        assert result['keyword'] == keyword

    def test_intent_stage_always_completes(self):
        result = run_pipeline("تربية الدجاج في الجزائر", save_files=False)
        assert 'intent' in result['stages_completed']

    def test_brief_stage_always_completes(self):
        result = run_pipeline("تربية الدجاج في الجزائر", save_files=False)
        assert 'brief' in result['stages_completed']

    def test_outline_stage_always_completes(self):
        result = run_pipeline("تربية الدجاج في الجزائر", save_files=False)
        assert 'outline' in result['stages_completed']

    def test_intent_data_in_result(self):
        result = run_pipeline("تربية الدجاج في الجزائر", save_files=False)
        assert 'intent' in result
        assert 'search_intent' in result['intent']

    def test_brief_data_in_result(self):
        result = run_pipeline("تربية الدجاج في الجزائر", save_files=False)
        assert 'brief' in result
        assert 'sections' in result['brief']

    def test_outline_data_in_result(self):
        result = run_pipeline("تربية الدجاج في الجزائر", save_files=False)
        assert 'outline' in result
        assert 'h1' in result['outline']


class TestAIUnavailableState:

    def test_no_ai_returns_ai_unavailable(self, monkeypatch):
        monkeypatch.setattr('agents.pipeline.get_ai_provider', lambda: None)
        result = run_pipeline("تربية الدجاج في الجزائر", save_files=False)
        assert result['status'] == TaskStatus.AI_UNAVAILABLE

    def test_ai_unavailable_not_success(self, monkeypatch):
        monkeypatch.setattr('agents.pipeline.get_ai_provider', lambda: None)
        result = run_pipeline("تربية الدجاج في الجزائر", save_files=False)
        assert result['status'] != TaskStatus.READY_FOR_REVIEW
        assert result['status'] != "SUCCESS"

    def test_ai_unavailable_still_has_intent(self, monkeypatch):
        monkeypatch.setattr('agents.pipeline.get_ai_provider', lambda: None)
        result = run_pipeline("تربية الدجاج في الجزائر", save_files=False)
        assert 'intent' in result['stages_completed']

    def test_ai_unavailable_still_has_brief(self, monkeypatch):
        monkeypatch.setattr('agents.pipeline.get_ai_provider', lambda: None)
        result = run_pipeline("تربية الدجاج في الجزائر", save_files=False)
        assert 'brief' in result['stages_completed']

    def test_ai_unavailable_still_has_outline(self, monkeypatch):
        monkeypatch.setattr('agents.pipeline.get_ai_provider', lambda: None)
        result = run_pipeline("تربية الدجاج في الجزائر", save_files=False)
        assert 'outline' in result['stages_completed']

    def test_ai_unavailable_no_article(self, monkeypatch):
        monkeypatch.setattr('agents.pipeline.get_ai_provider', lambda: None)
        result = run_pipeline("تربية الدجاج في الجزائر", save_files=False)
        assert 'article_ai' not in result['stages_completed']

    def test_ai_unavailable_no_fake_article(self, monkeypatch):
        monkeypatch.setattr('agents.pipeline.get_ai_provider', lambda: None)
        result = run_pipeline("تربية الدجاج في الجزائر", save_files=False)
        assert result.get('article_text') is None or result.get('article_text') == ""


class TestFilesystemPlugin:

    def test_save_creates_file(self, tmp_path):
        data = {"test": "data", "keyword": "تربية الدجاج"}
        path = save_to_filesystem("تربية الدجاج", "intent", data, base_dir=str(tmp_path))
        assert os.path.exists(path)

    def test_save_json_readable(self, tmp_path):
        data = {"keyword": "تربية الدجاج", "intent": "informational"}
        path = save_to_filesystem("تربية الدجاج", "intent", data, base_dir=str(tmp_path))
        with open(path, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        assert loaded['keyword'] == "تربية الدجاج"

    def test_save_article_as_markdown(self, tmp_path):
        text = "# عنوان المقال\n\nمحتوى المقال هنا."
        path = save_to_filesystem("تربية الدجاج", "article", text, base_dir=str(tmp_path))
        assert path.endswith('.md')
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert "عنوان المقال" in content

    def test_creates_task_directory(self, tmp_path):
        data = {"test": True}
        save_to_filesystem("تربية الدجاج في الجزائر", "intent", data, base_dir=str(tmp_path))
        dirs = [d for d in os.listdir(tmp_path) if os.path.isdir(os.path.join(tmp_path, d))]
        assert len(dirs) == 1

    def test_multiple_stages_same_directory(self, tmp_path):
        keyword = "تربية الدجاج"
        save_to_filesystem(keyword, "intent", {"a": 1}, base_dir=str(tmp_path))
        save_to_filesystem(keyword, "brief", {"b": 2}, base_dir=str(tmp_path))
        save_to_filesystem(keyword, "outline", {"c": 3}, base_dir=str(tmp_path))
        dirs = [d for d in os.listdir(tmp_path) if os.path.isdir(os.path.join(tmp_path, d))]
        assert len(dirs) == 1
        files = os.listdir(os.path.join(tmp_path, dirs[0]))
        assert len(files) == 3