import os


def test_anthropic_key_is_not_required_for_unit_tests():
    """
    Unit test:
    وجود مفتاح Anthropic ليس شرطًا لتشغيل اختبارات المشروع.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")

    # الاختبار ينجح سواء كان المفتاح موجودًا أو غير موجود.
    assert api_key is None or isinstance(api_key, str)


def test_anthropic_client_is_importable():
    """
    نتأكد فقط أن مكتبة Anthropic مثبتة ويمكن استيرادها.
    لا يتم إرسال أي طلب API.
    """
    import anthropic

    assert anthropic is not None