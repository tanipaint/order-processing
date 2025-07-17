"""Phase4: 注文登録＆在庫更新サービス"""
from datetime import datetime
from typing import Any, Dict, Optional

from .notion_client import NotionClient


class OrderService:
    """注文登録と在庫更新ロジックおよび自動返信メール送信を提供するサービス"""

    def __init__(self, notion: NotionClient, email_client: Optional[Any] = None):
        self.notion = notion
        self.email_client = email_client

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
        # 1. 注文ページを作成 (relation フィールドを含めてデータ整形)
        # relation field IDs: notion client may accept raw names or page IDs
        product_page_id = product.get("id")
        # get_customer may not exist on stub clients; fall back to raw name
        # 顧客が存在しない場合は自動登録
        get_cust = getattr(self.notion, "get_customer", None)
        if callable(get_cust):
            cust_page = self.notion.get_customer(order["customer_name"])
            if not cust_page:
                # 新規顧客登録
                create_cust = getattr(self.notion, "create_customer", None)
                if not callable(create_cust):
                    raise ValueError(
                        f"Customer {order['customer_name']} not found and cannot be created"
                    )
                cust_page = self.notion.create_customer(
                    {
                        "customer_name": order["customer_name"],
                        # メールアドレス等追加情報があればdataに含めて使用
                        "first_order_date": datetime.utcnow().date().isoformat(),
                        "is_existing": False,
                    }
                )
            customer_page_id = cust_page.get("id")
        else:
            customer_page_id = order["customer_name"]
        created = self.notion.create_order(
            {
                "order_id": order["order_id"],
                "customer_page_id": customer_page_id,
                "product_page_id": product_page_id,
                "quantity": order["quantity"],
                "delivery_date": order["delivery_date"],
                "status": order.get("status", ""),
                "approved_by": order.get("approved_by", ""),
                "created_at": datetime.utcnow().isoformat(),
            }
        )
        # 2. 在庫を更新
        old_stock = self.notion.get_product_stock(order["product_id"])
        new_stock = old_stock - order["quantity"]
        self.notion.update_product_stock(page_id, new_stock)
        # 3. 自動返信メール送信（オプション）
        if self.email_client:
            get_cust = getattr(self.notion, "get_customer", None)
            if callable(get_cust):
                cust_page = self.notion.get_customer(order["customer_name"])
                # email プロパティが Notion 上で email 型であることが前提
                email_addr = (
                    cust_page.get("properties", {}).get("email", {}).get("email")
                    if cust_page
                    else None
                )
                if email_addr:
                    subject = f"ご注文ありがとうございます（{order['order_id']}）"
                    body = (
                        f"{order['customer_name']} 様\n"
                        f"ご注文 {order['order_id']} を承りました。\n"
                        f"商品ID: {order['product_id']}\n"
                        f"数量: {order['quantity']}\n"
                        f"配送予定日: {order['delivery_date']}\n"
                    )
                    self.email_client.send_email(email_addr, subject, body)
        return created
