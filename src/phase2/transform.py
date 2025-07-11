"""Phase2: 構造化データ変換コンポーネント"""
from dataclasses import dataclass
from datetime import date

from src.phase2.llm_stub import extract_order_fields
from src.phase2.ocr_stub import ocr_process


@dataclass
class OrderData:
    customer_name: str
    product_id: str
    quantity: int
    delivery_date: date


def parse_order(text: str) -> OrderData:
    """テキストを受け取り、OCR→LLM抽出→OrderDataに変換するパイプライン"""
    ocr_text = ocr_process(text)
    fields = extract_order_fields(ocr_text)
    # ISOフォーマットの日付文字列をdateオブジェクトに変換
    d = date.fromisoformat(fields["delivery_date"])
    return OrderData(
        customer_name=fields["customer_name"],
        product_id=fields["product_id"],
        quantity=fields["quantity"],
        delivery_date=d,
    )
