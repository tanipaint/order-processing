"""商品データをNotionのproductsテーブルへ登録するスクリプト"""
import json

from dotenv import load_dotenv

from src.phase4.notion_client import NotionClient


def main():
    load_dotenv()
    products_json = """[
  {
    "id": "A001",
    "name": "ノートパソコン 15インチ",
    "description": "15インチディスプレイ搭載の軽量ノートパソコンです。",
    "price": 98000,
    "stock": 12,
    "created_at": "2025-05-10T09:00:00",
    "last_updated": "2025-07-15T10:00:00"
  },
  {
    "id": "B002",
    "name": "USB-C 充電ケーブル（1m）",
    "description": "高速充電対応のUSB-Cケーブル（1メートル）。",
    "price": 1200,
    "stock": 50,
    "created_at": "2025-04-25T14:20:00",
    "last_updated": "2025-07-15T10:05:00"
  },
  {
    "id": "C003",
    "name": "ワイヤレスマウス",
    "description": "静音・高精度センサー搭載のワイヤレスマウス。",
    "price": 2400,
    "stock": 30,
    "created_at": "2025-03-12T10:45:00",
    "last_updated": "2025-07-15T10:10:00"
  },
  {
    "id": "D004",
    "name": "A4対応レーザープリンター",
    "description": "モノクロA4対応の高速レーザープリンター。",
    "price": 39800,
    "stock": 5,
    "created_at": "2025-02-01T13:00:00",
    "last_updated": "2025-07-15T10:15:00"
  },
  {
    "id": "E005",
    "name": "モニターアーム（デュアル）",
    "description": "2台のモニターに対応したスムーズな可動式アーム。",
    "price": 7800,
    "stock": 8,
    "created_at": "2025-01-18T11:30:00",
    "last_updated": "2025-07-15T10:20:00"
  }
]
"""
    products = json.loads(products_json)
    client = NotionClient()
    for prod in products:
        res = client.create_product(prod)
        print(f"Created product page id: {res.get('id')} for {prod['id']}")


if __name__ == "__main__":
    main()
