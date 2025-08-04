"""Phase2: 構造化データ変換コンポーネント"""
import re
from dataclasses import dataclass
from datetime import date
from io import BytesIO

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

from src.phase2.llm_stub import extract_order_fields
from src.phase2.ocr_stub import ocr_process


@dataclass
class OrderData:
    customer_name: str
    product_id: str
    quantity: int
    delivery_date: date


# --- helper functions --------------------------------------------------
def extract_items_from_pdf(pdf_bytes: bytes) -> list[dict]:
    """PDF内のテーブルから複数商品のproduct_id, quantityリストを抽出"""
    items: list[dict] = []
    if not pdfplumber:
        return []
    try:
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables() or []
                for table in tables:
                    # header row 判定: 商品/数量 または Product/Quantity
                    header = table[0] if table else []
                    has_prod = any(
                        cell and ("商品" in cell or "Product" in cell) for cell in header
                    )
                    has_qty = any(
                        cell and ("数量" in cell or "Quantity" in cell) for cell in header
                    )
                    if not (has_prod and has_qty):
                        continue
                    # データ行の読み込み
                    for row in table[1:]:
                        if not row or len(row) < 2:
                            continue
                        pid = (row[0] or "").strip()
                        qty_str = (row[1] or "").strip()
                        if not pid or not qty_str.isdigit():
                            continue
                        items.append({"product_id": pid, "quantity": int(qty_str)})
                    if items:
                        return items
    except Exception:
        pass
    # PDFテーブル抽出で取得できなかった場合のフォールバック（日本語請求書形式）
    if not items:
        try:
            text = extract_text_from_pdf(pdf_bytes)
            for line in text.splitlines():
                line_s = line.strip()
                # パターン: 品名 + 単価 + 数量 + 金額
                m = re.match(r"^(.+?)\s+[\d,]+\s+(\d+)\s+[\d,]+$", line_s)
                if m:
                    name = m.group(1).strip()
                    qty = int(m.group(2))
                    items.append({"product_id": name, "quantity": qty})
        except Exception:
            pass
    return items


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """PDFからテキスト抽出。抽出できない場合はOCRスタブを実行"""
    texts: list[str] = []
    if pdfplumber:
        try:
            with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    texts.append(page_text)
            raw = "\n".join(texts).strip()
            if raw:
                return raw
        except Exception:
            pass
    # フォールバック: OCR
    return ocr_process(pdf_bytes)


def extract_metadata_from_text(text: str) -> dict:
    """本文テキストから顧客名と配送希望日を抽出し、配送日はdateオブジェクトで返す"""
    meta: dict = {}
    m_c = re.search(r"顧客[:：]\s*(.+)", text)
    if m_c:
        meta["customer_name"] = m_c.group(1).strip()
    # 配送希望日 or 納期で抽出
    m_d = re.search(r"(?:配送希望日|納期)[:：]\s*([\d年月日\-]+)", text)
    if m_d:
        raw = m_d.group(1).strip()
        # 日本語表記 "YYYY年M月D日" を ISO 形式へ変換
        m_jp = re.match(r"(\d{2,4})年(\d{1,2})月(\d{1,2})日", raw)
        if m_jp:
            y, mo, d = m_jp.groups()
            if len(y) == 2:
                y = "20" + y
            raw_iso = f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
        else:
            raw_iso = raw
        # 年月のみ or 年のみ補完
        if re.fullmatch(r"\d{4}$", raw_iso):
            raw_iso = f"{raw_iso}-01-01"
        elif re.fullmatch(r"\d{4}-\d{2}$", raw_iso):
            raw_iso = f"{raw_iso}-01"
        try:
            meta["delivery_date"] = date.fromisoformat(raw_iso)
        except ValueError:
            pass
    return meta


def build_orders_from_fields(fields: dict) -> list:
    """LLMまたはregex抽出結果のfieldsからOrderDataリストを構築"""
    orders: list[OrderData] = []
    # 複数商品
    if isinstance(fields.get("items"), list) and fields["items"]:
        meta = {
            "customer_name": fields.get("customer_name", ""),
            "delivery_date": fields.get("delivery_date"),
        }
        # delivery_date が文字列なら date に変換
        if isinstance(meta["delivery_date"], str):
            try:
                meta["delivery_date"] = date.fromisoformat(meta["delivery_date"])
            except Exception:
                meta["delivery_date"] = None
        for itm in fields["items"]:
            orders.append(
                OrderData(
                    customer_name=meta.get("customer_name", ""),
                    product_id=itm.get("product_id"),
                    quantity=itm.get("quantity"),
                    delivery_date=meta.get("delivery_date"),
                )
            )
        return orders
    # 単一商品
    # 必須フィールドチェック
    for key in ("customer_name", "product_id", "quantity", "delivery_date"):
        if key not in fields:
            raise ValueError(
                f"Missing required field '{key}' in parsed fields: {fields}"
            )
    raw = fields["delivery_date"]
    if isinstance(raw, str):
        try:
            raw = date.fromisoformat(raw)
        except Exception:
            raise ValueError(f"Invalid delivery_date format: {fields['delivery_date']}")
    orders.append(
        OrderData(
            customer_name=fields["customer_name"],
            product_id=fields["product_id"],
            quantity=fields["quantity"],
            delivery_date=raw,
        )
    )
    return orders


def parse_order(input_data: any) -> list:  # type: ignore
    """
    注文データを解析し、複数／単一問わず OrderData リストで返却するパイプライン。
    1) PDFテーブル抽出を試みる
    2) テーブルなければ本文テキストをOCR/NLP
    3) LLMスタブ or regex でフィールド抽出
    """
    # normalize input
    pdf_bytes = None
    body_text = ""
    if isinstance(input_data, dict) and input_data.get("pdf") is not None:
        pdf_bytes = input_data.get("pdf")
        body_text = input_data.get("body", "") or ""

    # 1) PDFテーブル抽出
    items = []
    if pdf_bytes:
        items = extract_items_from_pdf(pdf_bytes)
    # テーブルから明細取得できた場合、メタ情報を本文から抽出して返す
    if items:
        text_for_meta = body_text or extract_text_from_pdf(pdf_bytes)
        meta = extract_metadata_from_text(text_for_meta)
        orders = []
        for itm in items:
            orders.append(
                OrderData(
                    customer_name=meta.get("customer_name", ""),
                    product_id=itm.get("product_id"),
                    quantity=itm.get("quantity"),
                    delivery_date=meta.get("delivery_date"),
                )
            )
        return orders  # type: ignore

    # 2) 本文テキスト取得
    if pdf_bytes:
        ocr_pdf = extract_text_from_pdf(pdf_bytes)
        text = (body_text + "\n" + ocr_pdf).strip()
    else:
        if isinstance(input_data, bytes):
            text = input_data.decode(errors="ignore")
        else:
            text = str(input_data)

    # 3) フィールド抽出（LLM or regex）
    fields = extract_order_fields(text)
    orders = build_orders_from_fields(fields)
    # 単一注文の場合は OrderData を返却、それ以外はリストを返却
    if isinstance(orders, list) and len(orders) == 1:
        return orders[0]
    return orders
