import pytest


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    # stub 実装を動作させるため、APIキーをクリア
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


from datetime import date

from src.phase2.llm_stub import extract_order_fields
from src.phase2.transform import OrderData, parse_order

SAMPLE_MULTI = """
顧客: テスト商店
商品: A001
数量: 2
商品: B002
数量: 3
配送希望日: 2025-08-01
"""


def test_extract_order_fields_multi():
    fields = extract_order_fields(SAMPLE_MULTI)
    # 顧客名・日付抽出
    assert fields.get("customer_name") == "テスト商店"
    assert fields.get("delivery_date") == "2025-08-01"
    # items リスト
    assert "items" in fields
    items = fields["items"]
    assert isinstance(items, list)
    assert items == [
        {"product_id": "A001", "quantity": 2},
        {"product_id": "B002", "quantity": 3},
    ]


def test_parse_order_multi():
    result = parse_order(SAMPLE_MULTI)
    # 複数 OrderData のリストを返却
    assert isinstance(result, list)
    assert len(result) == 2
    # 各要素が OrderData 型
    assert all(isinstance(o, OrderData) for o in result)
    # 各フィールドの検証
    o1, o2 = result
    assert o1.customer_name == "テスト商店"
    assert o1.product_id == "A001"
    assert o1.quantity == 2
    assert o1.delivery_date == date(2025, 8, 1)
    assert o2.customer_name == "テスト商店"
    assert o2.product_id == "B002"
    assert o2.quantity == 3
    assert o2.delivery_date == date(2025, 8, 1)
