import pytest

from src.phase4.notion_client import NotionClient


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "test-key")
    monkeypatch.setenv("NOTION_DATABASE_ID_PRODUCTS", "db_products")
    monkeypatch.setenv("NOTION_DATABASE_ID_CUSTOMERS", "db_customers")
    monkeypatch.setenv("NOTION_DATABASE_ID_ORDERS", "db_orders")


class DummyResponse:
    def __init__(self, json_data):
        self._json = json_data

    def raise_for_status(self):
        pass

    def json(self):
        return self._json


def test_get_product_stock(monkeypatch):
    client = NotionClient()
    monkeypatch.setattr(
        client, "query_database", lambda db, f=None: {"results": [{"properties": {"stock": {"number": 5}}}]}  # type: ignore
    )
    assert client.get_product_stock("P1") == 5


def test_get_product_stock_not_found(monkeypatch):
    client = NotionClient()
    monkeypatch.setattr(client, "query_database", lambda db, f=None: {"results": []})  # type: ignore
    assert client.get_product_stock("P1") is None


def test_update_product_stock(monkeypatch):
    client = NotionClient()
    dummy = DummyResponse({"id": "page1"})
    monkeypatch.setattr(client.client, "patch", lambda url, json: dummy)
    res = client.update_product_stock("page1", 10)
    assert res["id"] == "page1"


def test_create_order(monkeypatch):
    client = NotionClient()
    data = {
        "order_id": "O1",
        "customer_name": "C",
        "product_id": "P",
        "quantity": 2,
        "delivery_date": "2025-01-01",
        "status": "OK",
        "approved_by": "U",
    }
    dummy = DummyResponse({"id": "newpage"})
    monkeypatch.setattr(client.client, "post", lambda url, json: dummy)
    res = client.create_order(data)
    assert res["id"] == "newpage"
