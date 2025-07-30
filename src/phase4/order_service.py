"""Phase4: 注文登録＆在庫更新サービス"""
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from .notion_client import NotionClient


class OrderService:
    """注文登録と在庫更新ロジックおよび自動返信メール送信を提供するサービス"""

    def __init__(self, notion: NotionClient, email_client: Optional[Any] = None):
        self.notion = notion
        self.email_client = email_client
        self.logger = logging.getLogger(__name__)

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
        # 注文アイテムリスト: 複数商品対応。単一商品の場合は items に変換
        items = order.get("items")
        if not items:
            # legacy single-item order: wrap into items list
            items = [
                {
                    "product_id": order.get("product_id"),
                    "quantity": order.get("quantity", 0),
                }
            ]
        # 顧客取得・作成
        cust_page_id = None
        get_cust = getattr(self.notion, "get_customer", None)
        if callable(get_cust):
            cust_page = self.notion.get_customer(order.get("customer_name", ""))
            if not cust_page:
                create_cust = getattr(self.notion, "create_customer", None)
                if callable(create_cust):
                    data_cust = {
                        "id": f"CUST{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                        "customer_name": order.get("customer_name"),
                        "first_order_date": datetime.utcnow().date().isoformat(),
                        "email": order.get("email"),
                        "is_existing": False,
                    }
                    try:
                        cust_page = self.notion.create_customer(data_cust)
                    except Exception as e:
                        self.logger.warning(f"failed to create customer: {e}")
            if cust_page:
                cust_page_id = cust_page.get("id")
        # マルチアイテムの場合
        if items:
            # 価格取得と在庫チェック
            total_price = 0
            # 先に注文ヘッダを作成
            header_id = order.get("order_id")
            created_at = datetime.utcnow().isoformat()
            header_data = {
                "order_id": header_id,
                "customer_page_id": cust_page_id,
                "delivery_date": order.get("delivery_date"),
                "status": order.get("status", "approved"),
                "approved_by": order.get("approved_by"),
                "total_price": 0,
                "created_at": created_at,
            }
            header_page = self.notion.create_order(header_data)
            header_page_id = header_page.get("id")
            # 各明細処理
            for item in items:
                pid = item.get("product_id")
                qty = item.get("quantity")
                prod = self.notion.get_product(pid)
                if not prod:
                    raise ValueError(f"Product {pid} not found")
                prod_page_id = prod.get("id")
                # 在庫チェック
                if not self.check_stock(pid, qty):
                    raise ValueError(f"Insufficient stock for {pid}")
                price = prod.get("properties", {}).get("price", {}).get("number") or 0
                sub_total = price * qty
                total_price += sub_total
                # 明細レコード作成
                detail_id = f"{header_id}-{pid}"  # 明細ID生成
                detail_data = {
                    "order_id": header_id,
                    "id": detail_id,
                    "order_page_id": header_page_id,
                    "product_page_id": prod_page_id,
                    "quantity": qty,
                    "sub_total": sub_total,
                    "created_at": created_at,
                }
                self.notion.create_order(detail_data)
                # 在庫更新
                old_stock = self.notion.get_product_stock(pid)
                self.notion.update_product_stock(prod_page_id, old_stock - qty)
            # ヘッダの total_price 更新
            try:
                # total_priceフィールドを更新
                self.notion.client.patch(
                    f"/pages/{header_page.get('id')}",
                    json={"properties": {"total_price": {"number": total_price}}},
                )
            except Exception as e:
                self.logger.error(f"failed to update header total_price: {e}")
            return header_page
        # 単一アイテムの場合は従来の処理
        product = self.notion.get_product(order["product_id"])
        if not product:
            raise ValueError(f"Product {order['product_id']} not found")
        page_id = product.get("id")
        if not self.check_stock(order["product_id"], order["quantity"]):
            raise ValueError(f"Insufficient stock for {order['product_id']}")
        # 注文登録
        try:
            created = self.notion.create_order(
                {
                    "order_id": order["order_id"],
                    "customer_page_id": cust_page_id,
                    "product_page_id": page_id,
                    "quantity": order["quantity"],
                    "delivery_date": order["delivery_date"],
                    "status": order.get("status", "approved"),
                    "approved_by": order.get("approved_by", ""),
                    "created_at": datetime.utcnow().isoformat(),
                }
            )
        except Exception as e:
            self.logger.warning(f"failed to create order: {e}", exc_info=True)
            created = None
        # 在庫更新
        new_stock = (
            product.get("properties", {}).get("stock", {}).get("number", 0)
            - order["quantity"]
        )
        self.notion.update_product_stock(page_id, new_stock)
        # 自動返信メール送信
        if self.email_client:
            get_cust = getattr(self.notion, "get_customer", None)
            if callable(get_cust):
                cust_page = self.notion.get_customer(order["customer_name"])
                email_addr = (
                    cust_page.get("properties", {}).get("email", {}).get("email")
                    if cust_page
                    else None
                )
                if email_addr:
                    subject = f"ご注文ありがとうございます（{order['order_id']}）"
                    body_text = (
                        f"{order['customer_name']} 様\n"
                        f"ご注文 {order['order_id']} を承りました。\n"
                        f"商品ID: {order['product_id']}\n"
                        f"数量: {order['quantity']}\n"
                        f"配送予定日: {order['delivery_date']}\n"
                    )
                    self.email_client.send_email(email_addr, subject, body_text)
        return created
