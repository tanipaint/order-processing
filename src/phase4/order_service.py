"""Phase4: 注文登録＆在庫更新サービス"""
from typing import Any, Dict

from .notion_client import NotionClient


class OrderService:
    """注文登録と在庫更新ロジックを提供するサービス"""

    def __init__(self, notion: NotionClient):
        self.notion = notion

    def check_stock(self, product_id: str, quantity: int) -> bool:
        """在庫が足りるかチェック"""
        stock = self.notion.get_product_stock(product_id)
        if stock is None:
            raise ValueError(f"Product {product_id} not found")
        return stock >= quantity

    def process_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """
        注文をDB登録し、在庫を更新するトランザクション処理。
        stocks 不足時は例外を送出。
        """
        product = self.notion.get_product(order["product_id"])
        if not product:
            raise ValueError(f"Product {order['product_id']} not found")
        page_id = product.get("id")
        if not self.check_stock(order["product_id"], order["quantity"]):
            raise ValueError(f"Insufficient stock for {order['product_id']}")
        # 1. 注文ページを作成
        created = self.notion.create_order(order)
        # 2. 在庫を更新
        old_stock = self.notion.get_product_stock(order["product_id"])
        new_stock = old_stock - order["quantity"]
        self.notion.update_product_stock(page_id, new_stock)
        return created
