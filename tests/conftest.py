import pytest

from app import create_app
from app.config import Config


@pytest.fixture()
def app(tmp_path):
    cfg = Config(app_version="test-1.0.0", database_url=f"sqlite:///{tmp_path / 'test.db'}")
    return create_app(cfg)


@pytest.fixture()
def client(app):
    return app.test_client()
