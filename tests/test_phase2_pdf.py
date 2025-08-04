from datetime import date
from pathlib import Path

import pytest

from src.phase2.transform import OrderData, parse_order


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    # Ensure OCR fallback and LLM stub path (no API key)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


def test_parse_order_from_pdf_multi():
    # PDFファイルから複数商品注文を抽出できる
    root = Path(__file__).resolve().parents[1]
    pdf_file = root / "doc" / "001_purchase_order.pdf"
    # サンプルPDFが存在しない場合はスキップ（CI環境などで未配置の場合）
    if not pdf_file.exists():
        pytest.skip(f"Sample PDF not found at {pdf_file}, skipping PDF multi-item test")
    pdf_bytes = pdf_file.read_bytes()
    # body が空でもテーブル抽出でitems取得
    orders = parse_order({"pdf": pdf_bytes, "body": ""})
    # 複数 OrderData が返る
    assert isinstance(orders, list)
    assert len(orders) >= 2
    for o in orders:
        assert isinstance(o, OrderData)
        # product_id と quantity は抽出されること
        assert isinstance(o.product_id, str) and o.product_id
        assert isinstance(o.quantity, int) and o.quantity > 0
        # 配送日や顧客名はPDFの内容次第で None の場合もある
        assert o.delivery_date is None or isinstance(o.delivery_date, date)
