"""Phase2: 構造化データ変換コンポーネント"""
import re
from dataclasses import dataclass
from datetime import date
from io import BytesIO

import pdfplumber

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
    ocr_text = ""
    if isinstance(text, dict) and text.get("pdf") is not None:
        body = text.get("body", "")
        pdf_bytes = text.get("pdf")
        # 1) Try table extraction via pdfplumber
        items = []
        try:
            with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables or []:
                        # assume first row is header
                        for row in table[1:]:
                            if not row or len(row) < 2:
                                continue
                            pid = (row[0] or "").strip()
                            q = (row[1] or "").strip()
                            if pid and q.isdigit():
                                items.append((pid, int(q)))
            if items:
                # Build multi-item order directly
                # Extract customer_name and delivery_date from body
                fields = extract_order_fields(body)
                # Build OrderData list
                orders = []
                # parse delivery_date
                raw_date = fields.get("delivery_date", "")
                d = date.fromisoformat(raw_date) if raw_date else None
                for pid, qty in items:
                    orders.append(
                        OrderData(
                            customer_name=fields.get("customer_name", ""),
                            product_id=pid,
                            quantity=qty,
                            delivery_date=d,
                        )
                    )
                return orders  # type: ignore
        except Exception:
            pass
        # Fallback: combine body and OCR text
        ocr_pdf_text = ocr_process(pdf_bytes)
        ocr_text = body + "\n" + ocr_pdf_text
    else:
        # str or bytes fallback
        ocr_text = ocr_process(text)
    fields = extract_order_fields(ocr_text)
    # フォールバック: items 空かつ単一商品も抽出されない場合は regex で抽出
    if not fields.get("items") and not fields.get("product_id"):
        # 顧客名抽出
        m_c = re.search(r"顧客[:：]\s*(.+)", ocr_text)
        if m_c:
            fields["customer_name"] = m_c.group(1).strip()
        # 配送希望日抽出
        m_d = re.search(r"配送希望日[:：]\s*([\d\-]+)", ocr_text)
        if m_d:
            fields["delivery_date"] = m_d.group(1).strip()
        # 商品・数量抽出
        prods = re.findall(r"商品[:：]\s*([A-Za-z0-9]+)", ocr_text)
        qtys = re.findall(r"数量[:：]\s*(\d+)", ocr_text)
        if len(prods) > 1 and len(prods) == len(qtys):
            fields["items"] = [
                {"product_id": p, "quantity": int(q)} for p, q in zip(prods, qtys)
            ]
        elif prods and qtys:
            fields["product_id"] = prods[0]
            fields["quantity"] = int(qtys[0])
    # LLM抽出で空のitemsかつproduct_id未設定の場合は正規表現ベースのフォールバック
    if not fields.get("items") and not fields.get("product_id"):
        # 顧客名
        m_c = re.search(r"顧客[:：]\s*(.+)", ocr_text)
        if m_c:
            fields["customer_name"] = m_c.group(1).strip()
        # 配送希望日
        m_d = re.search(r"配送希望日[:：]\s*([\d\-]+)", ocr_text)
        if m_d:
            fields["delivery_date"] = m_d.group(1).strip()
        # 商品と数量
        prods = re.findall(r"商品[:：]\s*([A-Za-z0-9]+)", ocr_text)
        qtys = re.findall(r"数量[:：]\s*(\d+)", ocr_text)
        if len(prods) > 1 and len(prods) == len(qtys):
            fields["items"] = [
                {"product_id": p, "quantity": int(q)} for p, q in zip(prods, qtys)
            ]
        elif prods and qtys:
            fields["product_id"] = prods[0]
            fields["quantity"] = int(qtys[0])
    # 複数商品対応: items リストが存在し、かつ要素がある場合は複数の OrderData を返却
    if "items" in fields and isinstance(fields["items"], list) and fields["items"]:
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
