"""Phase2: LLM抽出プロンプト設計＆呼び出しラッパー（スタブ実装）"""
import re


def extract_order_fields(text: str) -> dict:
    """テスト用LLMスタブ: テキストから注文情報を抽出するシンプルな実装"""
    data: dict = {}
    # 顧客
    m = re.search(r"顧客[:：]\s*(.+)", text)
    if m:
        data["customer_name"] = m.group(1).strip()
    # 商品
    m = re.search(r"商品[:：]\s*([A-Za-z0-9]+)", text)
    if m:
        data["product_id"] = m.group(1).strip()
    # 数量
    m = re.search(r"数量[:：]\s*(\d+)", text)
    if m:
        data["quantity"] = int(m.group(1))
    # 配送希望日
    m = re.search(r"配送希望日[:：]\s*([\d\-]+)", text)
    if m:
        data["delivery_date"] = m.group(1).strip()
    return data
