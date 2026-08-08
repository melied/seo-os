import sys
import os
sys.path.insert(0, '.')

from config.settings import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODEL

def test_provider():
    print("=" * 55)
    print("  AI Provider Test")
    print("=" * 55)
    print(f"  Provider : OpenRouter")
    print(f"  Base URL : {OPENROUTER_BASE_URL}")
    print(f"  Model    : {OPENROUTER_MODEL}")
    print(f"  Key      : {'configured' if OPENROUTER_API_KEY else 'MISSING'}")
    print()

    if not OPENROUTER_API_KEY:
        print("  ❌ OPENROUTER_API_KEY not set")
        print("  STATUS: AI_UNAVAILABLE")
        return False

    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url=OPENROUTER_BASE_URL
        )
        print("  جاري الاتصال بـ OpenRouter...")
        response = client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[{"role": "user", "content": "قل فقط: النظام يعمل بنجاح"}],
            max_tokens=50
        )
        reply = response.choices[0].message.content.strip()
        print(f"  Response : {reply}")
        print(f"\n  ✅ AI Provider: AVAILABLE")
        print(f"  STATUS: READY")
        return True

    except Exception as e:
        print(f"  ❌ Error: {e}")
        print(f"\n  STATUS: AI_UNAVAILABLE")
        return False

if __name__ == "__main__":
    test_provider()