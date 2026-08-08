import os
from dotenv import load_dotenv

load_dotenv(dotenv_path="config/.env")

ANTHROPIC_API_KEY        = os.getenv("ANTHROPIC_API_KEY")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
BLOGGER_BLOG_ID          = os.getenv("BLOGGER_BLOG_ID")
GSC_SITE_URL             = os.getenv("GSC_SITE_URL")
DEFAULT_LANGUAGE         = os.getenv("DEFAULT_LANGUAGE", "ar")
DB_PATH                  = os.path.join("data", "seo_os.db")

OPENROUTER_API_KEY  = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL    = os.getenv("OPENROUTER_MODEL", "openrouter/auto")