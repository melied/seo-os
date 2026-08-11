import sys
sys.path.insert(0, '.')
from config.settings import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODEL
from openai import OpenAI
import re

client = OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)

prompt = """أعد هذا JSON فقط بدون أي نص خارجه:

{
  "status": "REVIEW",
  "score": 70,
  "facts": {"verified": 2, "unsupported": 3, "uncertain": 1, "details": ["سعر الصوص غير موثق"]},
  "calculations": {"status": "PASS", "issues": []},
  "terminology": {"status": "WARNING", "issues": ["الآجي: استخدم إنفلونزا الطيور"]},
  "content_quality": {"depth": "ADEQUATE", "has_practical_info": true, "has_local_context": true},
  "critical_issues": ["أرقام السوق تحتاج مصادر"],
  "recommendations": ["أضف مصادر للأسعار"]
}"""

response = client.chat.completions.create(
    model=OPENROUTER_MODEL,
    messages=[{"role": "user", "content": prompt}],
    max_tokens=500
)

raw = response.choices[0].message.content.strip()
print("RAW RESPONSE:")
print(repr(raw[:300]))