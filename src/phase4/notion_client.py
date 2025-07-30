"""Phase4: Notion APIクライアントラッパー"""
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

import httpx


class NotionClient:
    """Notion APIへの問い合わせを行うクライアント"""

    def __init__(self, base_url: str = "https://api.notion.com/v1"):
        # 必須環境変数の検証
        api_key = os.getenv("NOTION_API_KEY")
        if not api_key:
            raise ValueError("Missing NOTION_API_KEY environment variable")

        self.database_id_products = os.getenv("NOTION_DATABASE_ID_PRODUCTS")
        self.database_id_customers = os.getenv("NOTION_DATABASE_ID_CUSTOMERS")
        self.database_id_orders = os.getenv("NOTION_DATABASE_ID_ORDERS")
        # 注文明細用データベースID
        self.database_id_order_details = os.getenv("NOTION_DATABASE_ID_ORDER_DETAILS")
        # 必須DB IDの検証
        if not self.database_id_products:
            raise ValueError("Missing NOTION_DATABASE_ID_PRODUCTS environment variable")
        if not self.database_id_customers:
            raise ValueError(
                "Missing NOTION_DATABASE_ID_CUSTOMERS environment variable"
            )
        if not self.database_id_orders:
            raise ValueError("Missing NOTION_DATABASE_ID_ORDERS environment variable")
        # 注文明細用データベースIDはオプション（サブオーダー登録時に使用）
        # self.database_id_order_details may be None if detail creation is not needed

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }
        self.client = httpx.Client(base_url=base_url, headers=headers)
        # Logger for warning messages
        import logging

        self.logger = logging.getLogger(__name__)

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
        # First, try lookup by product ID (title property 'id')
        from httpx import HTTPStatusError

        try:
            result = self.query_database(
                self.database_id_products,
                {"property": "id", "rich_text": {"equals": product_id}},
            )
            items = result.get("results", [])
            if items:
                return items[0]
        except HTTPStatusError as e:
            self.logger.warning(f"get_product by id filter failed: {e}")
        # Fallback: lookup by product name (rich_text property 'name')
        try:
            result_name = self.query_database(
                self.database_id_products,
                {"property": "name", "rich_text": {"equals": product_id}},
            )
            items_name = result_name.get("results", [])
            if items_name:
                return items_name[0]
        except HTTPStatusError as e:
            self.logger.warning(f"get_product by name filter failed: {e}")
        return None

    def get_customer(self, customer_name: str) -> Optional[Dict[str, Any]]:
        """指定顧客名（rich_textプロパティ customer_name）にマッチする顧客ページを取得"""
        result = self.query_database(
            self.database_id_customers,
            {"property": "customer_name", "rich_text": {"equals": customer_name}},
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
        """
        注文ヘッダ or 注文明細 or 単一商品注文をデータベースに作成
        data により orders または order_details に振り分け
        """
        # デバッグ: 呼び出しデータをログ出力
        logging.getLogger(__name__).debug("create_order request data: %s", data)
        # 注文明細 (order_details) 登録
        if data.get("sub_total") is not None:
            # 注文明細 (order_details) 登録
            props: Dict[str, Any] = {
                "id": {
                    "title": [
                        {"text": {"content": data.get("id", data.get("order_id", ""))}}
                    ]
                },
                "quantity": {"number": data["quantity"]},
                "sub_total": {"number": data["sub_total"]},
            }
            if data.get("order_page_id"):
                props["orders"] = {"relation": [{"id": data["order_page_id"]}]}
            if data.get("product_page_id"):
                props["products"] = {"relation": [{"id": data["product_page_id"]}]}
            payload = {
                "parent": {"database_id": self.database_id_order_details},
                "properties": props,
            }
            logging.getLogger(__name__).debug(
                "Notion create_order(detail) payload: %s", payload
            )
            resp = self.client.post("/pages", json=payload)
        # 注文ヘッダ (orders) 登録
        elif data.get("total_price") is not None:
            # 注文ヘッダ (orders) 登録
            props: Dict[str, Any] = {
                "order_id": {"title": [{"text": {"content": data["order_id"]}}]},
                "total_price": {"number": data["total_price"]},
                "delivery_date": {"date": {"start": data["delivery_date"]}},
                "status": {"select": {"name": data.get("status", "")}},
                "approved_by": {
                    "rich_text": [{"text": {"content": data.get("approved_by", "")}}]
                },
            }
            if data.get("customer_page_id"):
                props["customers"] = {"relation": [{"id": data["customer_page_id"]}]}
            payload = {
                "parent": {"database_id": self.database_id_orders},
                "properties": props,
            }
            logging.getLogger(__name__).debug(
                "Notion create_order(header) payload: %s", payload
            )
            resp = self.client.post("/pages", json=payload)
        # 従来の単一商品注文
        else:
            cust_page_id = data.get("customer_page_id")
            prod_page_id = data.get("product_page_id")
            props: Dict[str, Any] = {
                "order_id": {"title": [{"text": {"content": data["order_id"]}}]},
                "quantity": {"number": data["quantity"]},
                "delivery_date": {"date": {"start": data["delivery_date"]}},
                "status": {"select": {"name": data.get("status", "")}},
                "approved_by": {
                    "rich_text": [{"text": {"content": data.get("approved_by", "")}}]
                },
                "created_at": {
                    "date": {
                        "start": data.get("created_at", datetime.utcnow().isoformat())
                    }
                },
            }
            if cust_page_id:
                props["customers"] = {"relation": [{"id": cust_page_id}]}
            if prod_page_id:
                props["products"] = {"relation": [{"id": prod_page_id}]}
            resp = self.client.post(
                "/pages",
                json={
                    "parent": {"database_id": self.database_id_orders},
                    "properties": props,
                },
            )
        # エラーハンドリング：詳細ログ出力
        try:
            resp.raise_for_status()
        except Exception:
            text = getattr(resp, "text", None)
            logging.getLogger(__name__).error(
                "Notion create_order failed (status=%s): %s", resp.status_code, text
            )
            raise
        return resp.json()

    def create_product(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """productsデータベースに商品ページを作成"""
        props: Dict[str, Any] = {
            # Notion上のプロパティ型(id: title, name: rich_text)に合わせて設定
            "id": {"title": [{"text": {"content": data["id"]}}]},
            "name": {"rich_text": [{"text": {"content": data["name"]}}]},
            "description": {"rich_text": [{"text": {"content": data["description"]}}]},
            "price": {"number": data["price"]},
            "stock": {"number": data["stock"]},
            "created_at": {"date": {"start": data["created_at"]}},
            "last_updated": {"date": {"start": data["last_updated"]}},
        }
        resp = self.client.post(
            "/pages",
            json={
                "parent": {"database_id": self.database_id_products},
                "properties": props,
            },
        )
        resp.raise_for_status()
        return resp.json()

    def create_customer(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """customersデータベースに顧客ページを作成（存在しない場合の新規登録用）"""
        # titleプロパティ id、rich_textプロパティ customer_name, email, first_order_date, is_existing, created_at
        # properties を必須項目と任意項目に分けて定義
        props: Dict[str, Any] = {
            # 顧客ID（Title）は data['id'] を優先し、未指定時は customer_name を使用
            "id": {
                "title": [{"text": {"content": data.get("id", data["customer_name"])}}]
            },
            "customer_name": {
                "rich_text": [{"text": {"content": data["customer_name"]}}]
            },
        }
        # 任意プロパティ
        if data.get("email"):
            props["email"] = {"email": data["email"]}
        if data.get("first_order_date"):
            props["first_order_date"] = {"date": {"start": data["first_order_date"]}}
        props["is_existing"] = {"checkbox": data.get("is_existing", False)}
        props["created_at"] = {
            "date": {"start": data.get("created_at", datetime.utcnow().isoformat())}
        }
        resp = self.client.post(
            "/pages",
            json={
                "parent": {"database_id": self.database_id_customers},
                "properties": props,
            },
        )
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            text = getattr(e.response, "text", "")
            logging.getLogger(__name__).error(
                f"create_customer failed: {e.response.status_code} {text}",
                exc_info=True,
            )
            raise
        return resp.json()
