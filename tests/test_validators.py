import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.validators import (
    find_placeholders,
    validate_no_placeholders,
    validate_article,
    validate_schema,
    run_all_validations,
    is_full_article,
    has_introduction,
    has_conclusion,
    count_headings,
    find_duplicate_headings,
    check_keyword_density
)

# ======================================================
# نصوص الاختبار
# ======================================================

FULL_ARTICLE = """
# تربية الدجاج في الجزائر: دليل شامل 2026

تربية الدجاج في الجزائر من أكثر المشاريع الزراعية انتشاراً وربحاً في السنوات الأخيرة.
يبحث كثير من الشباب الجزائري عن مشاريع زراعية مربحة، وتربية الدجاج تعد من أفضل الخيارات
المتاحة بسبب انخفاض رأس المال المطلوب وسرعة العائد. في هذا الدليل ستجد كل ما تحتاجه
للبدء في مشروع تربية الدجاج في الجزائر من الصفر حتى الربح الفعلي.
يستفيد من هذا الدليل المبتدئون الذين يريدون بدء مشروع صغير، والمربون ذوو الخبرة الذين
يرغبون في توسيع مشاريعهم أو تحسين إنتاجيتهم.

## أنواع وسلالات الدجاج المناسبة للجزائر

هناك عدة سلالات مناسبة للتربية في الجزائر. السلالات المحلية تتميز بمقاومتها
للأمراض وتأقلمها مع المناخ الجزائري المتغير بين الشمال والجنوب.
أما السلالات المستوردة مثل الكوب وهيبارد فتتميز بسرعة النمو وزيادة الوزن في وقت قصير.
اختيار السلالة المناسبة يعتمد على هدفك: هل تريد دجاج لحم أم بيض؟

### السلالات المحلية
الدجاج البلدي الجزائري يتميز بمقاومة عالية للأمراض ويناسب التربية الحرة في المناطق الريفية.
سعره في السوق أعلى من الدجاج الصناعي بسبب الطلب المتزايد عليه.

### السلالات المستوردة
سلالة الكوب 308 من أكثر السلالات استخداماً في الجزائر للدجاج اللاحم.
تصل إلى الوزن المطلوب في 42 إلى 45 يوماً فقط مما يجعلها الأفضل للإنتاج التجاري.

## تجهيز الحظيرة ومتطلبات المكان

يحتاج كل دجاج إلى مساحة لا تقل عن 0.1 متر مربع في التربية المكثفة.
الحظيرة يجب أن تكون جيدة التهوية مع إضاءة مناسبة وحماية من البرد والحر.
يجب تركيب نظام تدفئة في الشتاء لأن الكتاكيت الصغيرة حساسة جداً لانخفاض الحرارة.
الأرضية يجب تغطيتها بالفرشة الجيدة من نشارة الخشب أو القش لامتصاص الرطوبة.

## التغذية والأعلاف

تحتاج الدجاجة يومياً إلى حوالي 120 غرام من العلف في مرحلة النمو.
أسعار الأعلاف في الجزائر تتراوح بين 3500 و4500 دينار للقنطار حسب النوع والجودة.
العلف يمثل حوالي 65 إلى 70 بالمئة من إجمالي تكاليف الإنتاج لذا يجب اختياره بعناية.
يمكن تقليل تكاليف الأعلاف باستخدام المخاليط المحلية من الذرة والصوجا والنخالة.

## التكاليف والأرباح المتوقعة

تكلفة تربية 1000 دجاجة في الجزائر تتراوح بين 250000 و350000 دينار جزائري.
هذه التكلفة تشمل الكتاكيت والأعلاف والأدوية والكهرباء والعمالة.
العائد المتوقع بعد 45 يوماً يتراوح بين 150000 و200000 دينار صافي ربح.
يمكن تحسين هامش الربح بالبيع المباشر للمستهلك بدلاً من الوسطاء.

## الأخطاء الشائعة عند المبتدئين

أكثر الأخطاء شيوعاً هي الاكتظاظ في الحظيرة مما يؤدي إلى انتشار الأمراض بسرعة.
كذلك إهمال التطعيم في الأوقات المحددة يتسبب في خسائر كبيرة للمربي.
شراء الكتاكيت من مصادر غير موثوقة خطأ فادح يجب تجنبه تماماً.

## الخاتمة

تربية الدجاج في الجزائر مشروع مربح يستحق الدراسة والتخطيط الجيد.
ابدأ بعدد صغير مثل 500 دجاجة ثم وسع تدريجياً بناءً على خبرتك وإمكانياتك المادية.
التوفيق في مشروعك يبدأ بالتخطيط الجيد والاستشارة من ذوي الخبرة في هذا المجال.
"""

ARTICLE_WITH_PLACEHOLDERS = """
# عنوان المقال

مقدمة المقال هنا وهي طويلة بما يكفي لتجاوز الحد الأدنى من الكلمات في المقدمة.

## القسم الأول

[اكتب المحتوى هنا]

## القسم الثاني

محتوى حقيقي في هذا القسم يصف موضوعاً مهماً.

## الخاتمة

[اكتب الخاتمة هنا]
"""


class TestPlaceholderValidator:

    def test_clean_text_passes(self):
        result = validate_no_placeholders("نص عربي عادي بدون أي placeholder")
        assert result['passed'] == True

    def test_arabic_placeholder_detected(self):
        result = validate_no_placeholders("[اكتب المحتوى هنا]")
        assert result['passed'] == False
        assert len(result['placeholders_found']) > 0

    def test_add_placeholder_detected(self):
        result = validate_no_placeholders("[أضف الإجابة هنا]")
        assert result['passed'] == False

    def test_todo_detected(self):
        result = validate_no_placeholders("هذا النص يحتوي TODO في المنتصف")
        assert result['passed'] == False

    def test_writer_note_detected(self):
        result = validate_no_placeholders("*ملاحظة للكاتب: اكتب هنا*")
        assert result['passed'] == False

    def test_ai_self_reference_detected(self):
        result = validate_no_placeholders("سأكتب لك مقالاً عن هذا الموضوع")
        assert result['passed'] == False

    def test_multiple_placeholders(self):
        text = "[اكتب هنا] و[أضف هنا] و TODO"
        result = validate_no_placeholders(text)
        assert result['passed'] == False
        assert len(result['issues']) >= 2


class TestArticleValidator:

    def test_full_article_passes(self):
        result = validate_article(FULL_ARTICLE, "تربية الدجاج في الجزائر")
        assert result['passed'] == True
        assert len(result['issues']) == 0

    def test_article_with_placeholders_fails(self):
        result = validate_article(ARTICLE_WITH_PLACEHOLDERS)
        assert result['passed'] == False

    def test_short_text_fails(self):
        result = validate_article("نص قصير جداً")
        assert result['passed'] == False

    def test_word_count_returned(self):
        result = validate_article(FULL_ARTICLE)
        assert result['word_count'] > 0

    def test_headings_counted(self):
        result = validate_article(FULL_ARTICLE)
        assert result['headings']['h1'] == 1
        assert result['headings']['h2'] >= 3
        assert result['headings']['h3'] >= 1

    def test_duplicate_headings_detected(self):
        text = FULL_ARTICLE + "\n## التغذية والأعلاف\nمحتوى مكرر هنا.\n"
        result = validate_article(text)
        assert result['passed'] == False
        assert any('مكررة' in i for i in result['issues'])

    def test_multiple_h1_fails(self):
        text = "# عنوان 1\n\nمقدمة طويلة بما يكفي لهذا الاختبار.\n\n# عنوان 2\n\n## قسم\n\nمحتوى\n\n## خاتمة\n\nنهاية"
        result = validate_article(text)
        assert result['passed'] == False
        assert any('H1' in i for i in result['issues'])


class TestIsFullArticle:

    def test_long_text_is_article(self):
        assert is_full_article(FULL_ARTICLE, min_words=200) == True

    def test_short_text_is_not_article(self):
        assert is_full_article("نص قصير", min_words=300) == False

    def test_outline_only_is_not_article(self):
        outline = "## قسم 1\n## قسم 2\n## قسم 3\n## خاتمة"
        assert is_full_article(outline, min_words=300) == False


class TestKeywordDensity:

    def test_normal_density(self):
        text = "تربية الدجاج " * 5 + "محتوى آخر مختلف تماماً " * 95
        result = check_keyword_density(text, "تربية الدجاج")
        assert result['warning'] == False

    def test_high_density_warns(self):
        text = "تربية الدجاج " * 50
        result = check_keyword_density(text, "تربية الدجاج")
        assert result['warning'] == True

    def test_keyword_count(self):
        text = "تربية الدجاج في الجزائر. تربية الدجاج مهمة. تربية الدجاج."
        result = check_keyword_density(text, "تربية الدجاج")
        assert result['count'] == 3


class TestSchemaValidator:

    def test_valid_schema_passes(self):
        schema = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": "تربية الدجاج في الجزائر",
            "description": "دليل شامل لتربية الدجاج",
            "author": {"@type": "Organization", "name": "الموقع"},
            "datePublished": "2026-08-08",
            "dateModified": "2026-08-08",
            "url": "https://www.news-theworld.com/article"
        }
        result = validate_schema(schema)
        assert result['passed'] == True

    def test_missing_field_fails(self):
        schema = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": "عنوان"
        }
        result = validate_schema(schema)
        assert result['passed'] == False

    def test_invalid_json_fails(self):
        result = validate_schema("not valid json {{{")
        assert result['passed'] == False

    def test_placeholder_in_schema_fails(self):
        schema = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": "[أضف العنوان هنا]",
            "description": "وصف",
            "author": {"@type": "Organization", "name": "الموقع"},
            "datePublished": "2026-08-08",
            "dateModified": "2026-08-08",
            "url": "https://www.news-theworld.com/article"
        }
        result = validate_schema(schema)
        assert result['passed'] == False


class TestRunAllValidations:

    def test_full_valid_article_passes(self):
        schema = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": "تربية الدجاج في الجزائر",
            "description": "دليل شامل",
            "author": {"@type": "Organization", "name": "الموقع"},
            "datePublished": "2026-08-08",
            "dateModified": "2026-08-08",
            "url": "https://www.news-theworld.com/article"
        }
        result = run_all_validations(FULL_ARTICLE, "تربية الدجاج", schema)
        assert result['quality_gate'] == "PASSED"

    def test_article_with_placeholder_fails_gate(self):
        result = run_all_validations(ARTICLE_WITH_PLACEHOLDERS)
        assert result['quality_gate'] == "FAILED"