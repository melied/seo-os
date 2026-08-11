import sys
sys.path.insert(0, '.')

from agents.quality_gate_v2 import run_quality_gate_v2

# اختبار بسيط
result = run_quality_gate_v2(
    article_text="نص قصير جداً",
    keyword="تربية الدجاج",
    content_type="informational_article",
    base_seo_result={"score": 100}
)
print("Keys:", list(result.keys()))
print("final_status:", result.get('final_status'))
print("passed:", result.get('passed'))