import json

import pytest

import src.phase2.llm_stub as llm_stub


class DummyChoice:
    def __init__(self, content):
        self.message = type("M", (), {"content": content})


class DummyResp:
    def __init__(self, content):
        self.choices = [DummyChoice(content)]


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


def test_extract_order_fields_stub(monkeypatch):
    # APIキー未設定時は正規表現スタブを使用
    text = """顧客: テスト店
商品: B123
数量: 2
配送希望日: 2025-08-01
"""
    fields = llm_stub.extract_order_fields(text)
    assert fields == {
        "customer_name": "テスト店",
        "product_id": "B123",
        "quantity": 2,
        "delivery_date": "2025-08-01",
    }


def test_extract_order_fields_llm(monkeypatch):
    # APIキー設定時は OpenAI を呼び出す
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    expected = {
        "customer_name": "A",
        "product_id": "P",
        "quantity": 1,
        "delivery_date": "2025-01-01",
    }
    dummy_json = json.dumps(expected)
    # モックして ChatCompletion.create を差し替え
    monkeypatch.setattr(
        llm_stub.openai.ChatCompletion,
        "create",
        lambda **kwargs: DummyResp(dummy_json),
    )
    fields = llm_stub.extract_order_fields("dummy")
    assert fields == expected
