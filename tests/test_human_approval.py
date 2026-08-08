import sys
import os
import sqlite3
import json
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import DB_PATH
from agents.intent_agent import TaskStatus
from agents.human_approval import (
    get_pending_articles,
    get_approved_articles,
    get_task,
    approve_article,
    reject_article,
    read_article_file
)

# ======================================================
# Fixtures
# ======================================================

@pytest.fixture
def pending_task(tmp_path):
    """إنشاء task في حالة READY_FOR_REVIEW للاختبار"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    quality_report = json.dumps({
        "score": 95,
        "quality_gate": "PASSED",
        "passed": True,
        "critical_issues": [],
        "warnings": []
    })

    cursor.execute("""
        INSERT INTO content_tasks
        (keyword, search_intent, content_type, status, quality_report, created_at)
        VALUES (?, ?, ?, ?, ?, datetime('now'))
    """, (
        "اختبار تربية الدجاج",
        "informational",
        "informational_article",
        TaskStatus.READY_FOR_REVIEW,
        quality_report
    ))

    task_id = cursor.lastrowid
    conn.commit()
    conn.close()

    yield task_id

    # تنظيف بعد الاختبار
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM content_tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()


@pytest.fixture
def approved_task(tmp_path):
    """إنشاء task في حالة APPROVED للاختبار"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO content_tasks
        (keyword, search_intent, content_type, status, created_at)
        VALUES (?, ?, ?, ?, datetime('now'))
    """, (
        "اختبار معتمد",
        "commercial",
        "price_guide",
        TaskStatus.APPROVED
    ))

    task_id = cursor.lastrowid
    conn.commit()
    conn.close()

    yield task_id

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM content_tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()


# ======================================================
# Tests
# ======================================================

class TestGetPendingArticles:

    def test_returns_list(self):
        result = get_pending_articles()
        assert isinstance(result, list)

    def test_pending_task_appears(self, pending_task):
        rows = get_pending_articles()
        ids = [r[0] for r in rows]
        assert pending_task in ids

    def test_approved_task_not_in_pending(self, approved_task):
        rows = get_pending_articles()
        ids = [r[0] for r in rows]
        assert approved_task not in ids


class TestGetTask:

    def test_returns_none_for_missing(self):
        result = get_task(999999)
        assert result is None

    def test_returns_dict_for_existing(self, pending_task):
        result = get_task(pending_task)
        assert result is not None
        assert isinstance(result, dict)

    def test_task_has_required_fields(self, pending_task):
        result = get_task(pending_task)
        required = ['id', 'keyword', 'search_intent', 'content_type',
                    'article_path', 'quality_report', 'status', 'created_at']
        for field in required:
            assert field in result, f"حقل مفقود: {field}"

    def test_task_keyword_matches(self, pending_task):
        result = get_task(pending_task)
        assert result['keyword'] == "اختبار تربية الدجاج"

    def test_task_status_is_ready(self, pending_task):
        result = get_task(pending_task)
        assert result['status'] == TaskStatus.READY_FOR_REVIEW


class TestApproveArticle:

    def test_approve_pending_task_succeeds(self, pending_task):
        result = approve_article(pending_task)
        assert result['success'] == True
        assert result['status'] == TaskStatus.APPROVED

    def test_approve_changes_db_status(self, pending_task):
        approve_article(pending_task)
        task = get_task(pending_task)
        assert task['status'] == TaskStatus.APPROVED

    def test_approve_nonexistent_fails(self):
        result = approve_article(999999)
        assert result['success'] == False

    def test_approve_with_notes(self, pending_task):
        result = approve_article(pending_task, reviewer_notes="مقال ممتاز")
        assert result['success'] == True
        assert 'approval_data' in result
        assert result['approval_data']['reviewer_notes'] == "مقال ممتاز"

    def test_double_approve_fails(self, pending_task):
        approve_article(pending_task)
        result = approve_article(pending_task)
        assert result['success'] == False

    def test_approve_returns_approved_status(self, pending_task):
        result = approve_article(pending_task)
        assert result['status'] == TaskStatus.APPROVED

    def test_approved_task_not_in_pending(self, pending_task):
        approve_article(pending_task)
        rows = get_pending_articles()
        ids = [r[0] for r in rows]
        assert pending_task not in ids

    def test_approved_task_in_approved_list(self, pending_task):
        approve_article(pending_task)
        rows = get_approved_articles()
        ids = [r[0] for r in rows]
        assert pending_task in ids


class TestRejectArticle:

    def test_reject_pending_task_succeeds(self, pending_task):
        result = reject_article(pending_task, reason="جودة المحتوى منخفضة")
        assert result['success'] == True
        assert result['status'] == TaskStatus.FAILED

    def test_reject_changes_db_status(self, pending_task):
        reject_article(pending_task, reason="سبب الرفض")
        task = get_task(pending_task)
        assert task['status'] == TaskStatus.FAILED

    def test_reject_nonexistent_fails(self):
        result = reject_article(999999)
        assert result['success'] == False

    def test_rejected_not_in_pending(self, pending_task):
        reject_article(pending_task)
        rows = get_pending_articles()
        ids = [r[0] for r in rows]
        assert pending_task not in ids

    def test_rejected_not_in_approved(self, pending_task):
        reject_article(pending_task)
        rows = get_approved_articles()
        ids = [r[0] for r in rows]
        assert pending_task not in ids


class TestGetApprovedArticles:

    def test_returns_list(self):
        result = get_approved_articles()
        assert isinstance(result, list)

    def test_approved_task_appears(self, approved_task):
        rows = get_approved_articles()
        ids = [r[0] for r in rows]
        assert approved_task in ids

    def test_pending_not_in_approved(self, pending_task):
        rows = get_approved_articles()
        ids = [r[0] for r in rows]
        assert pending_task not in ids


class TestReadArticleFile:

    def test_missing_file_returns_empty(self):
        task = {'article_path': 'nonexistent/path.md', 'keyword': 'test'}
        result = read_article_file(task)
        assert result == ""

    def test_reads_existing_file(self, tmp_path):
        article_file = tmp_path / "article.md"
        article_file.write_text("# عنوان المقال\n\nمحتوى المقال هنا.", encoding='utf-8')
        task = {'article_path': str(article_file), 'keyword': 'test'}
        result = read_article_file(task)
        assert "عنوان المقال" in result

    def test_none_path_returns_empty(self):
        task = {'article_path': None, 'keyword': 'keyword-that-has-no-folder'}
        result = read_article_file(task)
        assert isinstance(result, str)