import pytest
from pydantic import ValidationError

from app.config import Settings


def test_demo_mode_fails_closed_without_admin_key():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, demo_mode=True, admin_api_key="", app_api_key="")


def test_hcaptcha_keys_must_be_configured_as_a_pair():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, hcaptcha_site_key="site-only")


def test_cloud_embeddings_require_qdrant_credentials():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, embedding_provider="qdrant_cloud")

    configured = Settings(
        _env_file=None,
        embedding_provider="qdrant_cloud",
        qdrant_url="https://example.qdrant.io",
        qdrant_api_key="secret",
    )
    assert configured.qdrant_cloud_inference is True
