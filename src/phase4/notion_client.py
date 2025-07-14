"""Phase4: Notion APIクライアントラッパー"""
import os
from datetime import datetime
from typing import Any, Dict, Optional

import httpx

# 環境変数からNotion設定を取得
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
DATABASE_ID_PRODUCTS = os.getenv("NOTION_DATABASE_ID_PRODUCTS")
DATABASE_ID_CUSTOMERS = os.getenv("NOTION_DATABASE_ID_CUSTOMERS")
DATABASE_ID_ORDERS = os.getenv("NOTION_DATABASE_ID_ORDERS")

if not NOTION_API_KEY:
    raise ValueError("Missing NOTION_API_KEY environment variable")

_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}


class NotionClient:
    """Notion APIへの問い合わせを行うクライアント"""

    def __init__(self, base_url: str = "https://api.notion.com/v1"):
        self.client = httpx.Client(base_url=base_url, headers=_HEADERS)

    def query_database(
        self, database_id: str, filter: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {}
        if filter:
            payload["filter"] = filter
        resp = self.client.post(f"/databases/{database_id}/query", json=payload)
        resp.raise_for_status()
        return resp.json()

    def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        """指定IDの商品ページを取得"""
        result = self.query_database(
            DATABASE_ID_PRODUCTS,
            {"property": "id", "rich_text": {"equals": product_id}},
        )
        items = result.get("results", [])
        return items[0] if items else None

    def get_customer(self, customer_name: str) -> Optional[Dict[str, Any]]:
        """指定顧客名の顧客ページを取得"""
        result = self.query_database(
            DATABASE_ID_CUSTOMERS,
            {"property": "name", "title": {"equals": customer_name}},
        )
        items = result.get("results", [])
        return items[0] if items else None

    def get_product_stock(self, product_id: str) -> Optional[int]:
        """指定商品の在庫数を返す"""
        page = self.get_product(product_id)
        if not page:
            return None
        props = page.get("properties", {})
        return props.get("stock", {}).get("number")

    def update_product_stock(self, page_id: str, new_stock: int) -> Dict[str, Any]:
        """商品ページの在庫数と更新日時を更新"""
        props = {
            "stock": {"number": new_stock},
            "last_updated": {"date": {"start": datetime.utcnow().isoformat()}},
        }
        resp = self.client.patch(f"/pages/{page_id}", json={"properties": props})
        resp.raise_for_status()
        return resp.json()

    def create_order(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """ordersデータベースに注文ページを作成"""
        props: Dict[str, Any] = {
            "order_id": {"title": [{"text": {"content": data["order_id"]}}]},
            "customer_name": {
                "rich_text": [{"text": {"content": data["customer_name"]}}]
            },
            "product_id": {"rich_text": [{"text": {"content": data["product_id"]}}]},
            "quantity": {"number": data["quantity"]},
            "delivery_date": {"date": {"start": data["delivery_date"]}},
            "status": {"select": {"name": data.get("status", "")}},
            "approved_by": {
                "rich_text": [{"text": {"content": data.get("approved_by", "")}}]
            },
        }
        resp = self.client.post(
            "/pages",
            json={"parent": {"database_id": DATABASE_ID_ORDERS}, "properties": props},
        )
        resp.raise_for_status()
        return resp.json()
