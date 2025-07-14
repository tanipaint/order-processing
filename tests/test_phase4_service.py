import pytest

from src.phase4.order_service import OrderService


class FakeNotion:
    def __init__(self):
        # products P1 has stock 5 and page id 'page1'
        self.pages = {"P1": {"properties": {"stock": {"number": 5}}, "id": "page1"}}
        self.created = None
        self.updated = None

    def get_product(self, pid):
        return self.pages.get(pid)

    def get_product_stock(self, pid):
        prod = self.get_product(pid)
        return prod["properties"]["stock"]["number"] if prod else None

    def create_order(self, data):
        self.created = data
        return {"created": True}

    def update_product_stock(self, page_id, new_stock):
        self.updated = new_stock
        return {"updated": True}


@pytest.fixture
def service():
    return OrderService(FakeNotion())


def test_check_stock_ok(service):
    assert service.check_stock("P1", 3)


def test_check_stock_ng(service):
    assert not service.check_stock("P1", 6)


def test_process_order_success(service):
    order = {
        "order_id": "O1",
        "customer_name": "C",
        "product_id": "P1",
        "quantity": 2,
        "delivery_date": "2025-01-01",
        "status": "OK",
        "approved_by": "U",
    }
    res = service.process_order(order)
    assert res == {"created": True}
    # stock should be decremented from 5 to 3
    assert service.notion.updated == 3


def test_process_order_insufficient(service):
    order = {
        "order_id": "O1",
        "customer_name": "C",
        "product_id": "P1",
        "quantity": 10,
        "delivery_date": "2025-01-01",
        "status": "OK",
        "approved_by": "U",
    }
    with pytest.raises(ValueError):
        service.process_order(order)
