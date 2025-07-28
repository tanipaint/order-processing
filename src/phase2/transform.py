"""Phase2: 構造化データ変換コンポーネント"""
import re
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
    # text may be str, bytes, or dict with body/pdf keys
    if isinstance(text, dict) and text.get("pdf") is not None:
        # Combine body text and PDF OCR text
        body = text.get("body", "")
        pdf_bytes = text.get("pdf")
        ocr_pdf_text = ocr_process(pdf_bytes)
        ocr_text = body + "\n" + ocr_pdf_text
    else:
        # str or bytes fallback
        ocr_text = ocr_process(text)
    fields = extract_order_fields(ocr_text)
    # 複数商品対応: items リストがある場合は複数の OrderData を返却
    if "items" in fields:
        # 必須フィールドチェック (customer_name, delivery_date)
        for key in ("customer_name", "delivery_date"):
            if key not in fields:
                raise ValueError(
                    f"Missing required field '{key}' for multi-item order: {fields!r}"
                )
        raw_date = fields.get("delivery_date") or ""
        # 日付補完
        if re.fullmatch(r"\d{4}", raw_date):
            raw_date = f"{raw_date}-01-01"
        elif re.fullmatch(r"\d{4}-\d{2}", raw_date):
            raw_date = f"{raw_date}-01"
        try:
            d = date.fromisoformat(raw_date)
        except ValueError:
            raise ValueError(
                f"Invalid delivery_date format: {raw_date!r}, expected YYYY-MM-DD"
            )
        orders = []
        for item in fields["items"]:
            orders.append(
                OrderData(
                    customer_name=fields["customer_name"],
                    product_id=item.get("product_id"),
                    quantity=item.get("quantity"),
                    delivery_date=d,
                )
            )
        return orders  # type: ignore
    # 単一商品の場合
    # 必須フィールドの検証
    required = ["customer_name", "product_id", "quantity", "delivery_date"]
    missing = [k for k in required if k not in fields]
    if missing:
        raise ValueError(
            f"Missing required fields in extracted data: {missing}, extracted={fields!r}"
        )
    # ISOフォーマットの日付文字列をdateオブジェクトに変換
    raw_date = fields.get("delivery_date", "")
    if not raw_date:
        raise ValueError(f"Missing delivery_date in extracted fields: {fields!r}")
    # 簡易対応: 年のみ or 年-月のみの場合は先頭日を補完
    if re.fullmatch(r"\d{4}", raw_date):
        raw_date = f"{raw_date}-01-01"
    elif re.fullmatch(r"\d{4}-\d{2}", raw_date):
        raw_date = f"{raw_date}-01"
    try:
        d = date.fromisoformat(raw_date)
    except ValueError:
        raise ValueError(
            f"Invalid delivery_date format: {raw_date!r}, expected YYYY-MM-DD"
        )
    return OrderData(
        customer_name=fields["customer_name"],
        product_id=fields["product_id"],
        quantity=fields["quantity"],
        delivery_date=d,
    )
