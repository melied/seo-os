import os
import pytest
from google.oauth2 import service_account
from googleapiclient.discovery import build

from config.settings import (
    GOOGLE_SERVICE_ACCOUNT_JSON,
    GSC_SITE_URL,
    BLOGGER_BLOG_ID,
)

SCOPES = [
    "https://www.googleapis.com/auth/webmasters.readonly",
    "https://www.googleapis.com/auth/blogger.readonly",
]


def get_credentials():
    if not GOOGLE_SERVICE_ACCOUNT_JSON:
        pytest.skip("Google credentials are not configured.")

    if not os.path.exists(GOOGLE_SERVICE_ACCOUNT_JSON):
        pytest.skip("service_account.json not found.")

    return service_account.Credentials.from_service_account_file(
        GOOGLE_SERVICE_ACCOUNT_JSON,
        scopes=SCOPES,
    )


@pytest.mark.integration
def test_search_console():
    creds = get_credentials()

    service = build(
        "webmasters",
        "v3",
        credentials=creds,
    )

    result = service.searchanalytics().query(
        siteUrl=GSC_SITE_URL,
        body={
            "startDate": "2026-05-01",
            "endDate": "2026-08-01",
            "dimensions": ["query"],
            "rowLimit": 5,
        },
    ).execute()

    assert isinstance(result, dict)

    print("\n=== Search Console ===")

    rows = result.get("rows", [])

    for row in rows:
        print(
            f"- {row['keys'][0]} | "
            f"clicks: {row['clicks']} | "
            f"impressions: {row['impressions']}"
        )


@pytest.mark.integration
def test_blogger():
    creds = get_credentials()

    service = build(
        "blogger",
        "v3",
        credentials=creds,
    )

    blog = service.blogs().getByUrl(
        url="https://www.news-theworld.com/"
    ).execute()

    assert blog.get("id")

    print("\n=== Blogger ===")
    print(f"Blog: {blog.get('name')}")
    print(f"Blog ID: {blog.get('id')}")
    print(
        f"Posts: "
        f"{blog.get('posts', {}).get('totalItems', 0)}"
    )