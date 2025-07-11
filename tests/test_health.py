import os

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture(autouse=True)
def set_env_dev(monkeypatch):
    # テスト時にリロードを無効化
    monkeypatch.setenv("DEV", "0")


def test_health_check():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
