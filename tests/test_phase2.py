from datetime import date

from src.phase2.email_stub import read_email_file
from src.phase2.llm_stub import extract_order_fields
from src.phase2.ocr_stub import ocr_process
from src.phase2.transform import OrderData, parse_order

SAMPLE_TEXT = """顧客: テスト商店
商品: A001
数量: 5
配送希望日: 2025-07-20
"""


def test_read_email_file(tmp_path):
    file_path = tmp_path / "email.txt"
    file_path.write_text(SAMPLE_TEXT, encoding="utf-8")
    assert read_email_file(str(file_path)) == SAMPLE_TEXT


def test_ocr_process_passthrough():
    text = "サンプルテキスト"
    assert ocr_process(text) == text


def test_extract_order_fields():
    fields = extract_order_fields(SAMPLE_TEXT)
    assert fields == {
        "customer_name": "テスト商店",
        "product_id": "A001",
        "quantity": 5,
        "delivery_date": "2025-07-20",
    }


def test_parse_order():
    order = parse_order(SAMPLE_TEXT)
    assert isinstance(order, OrderData)
    assert order.customer_name == "テスト商店"
    assert order.product_id == "A001"
    assert order.quantity == 5
    assert order.delivery_date == date(2025, 7, 20)
