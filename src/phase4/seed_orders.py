"""注文データを Notion の orders テーブルへ登録するスクリプト"""
import csv
from datetime import datetime

try:
    from dotenv import load_dotenv
except ImportError:

    def load_dotenv():
        pass


from src.phase4.notion_client import NotionClient


def parse_jp_date(s: str) -> str:
    """日本語年月日表記をISOフォーマット(YYYY-MM-DD)に変換"""
    for fmt in ("%Y年%m月%d日", "%Y年%m月%d日 %H:%M"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.date().isoformat()
        except Exception:
            continue
    return s


def main():
    load_dotenv()
    client = NotionClient()
    path = "doc/orders.csv"
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cust = row.get("customers", "").split()[0]
            prod = row.get("products", "").split()[0]
            data = {
                "order_id": row.get("order_id", ""),
                "customer_page_id": cust,
                "product_page_id": prod,
                "quantity": int(row.get("quantity", 0)),
                "delivery_date": parse_jp_date(row.get("delivery_date", "")),
                "status": row.get("status", ""),
                "approved_by": row.get("approved_by", ""),
                "created_at": parse_jp_date(row.get("created_at", "")),
            }
            try:
                res = client.create_order(data)
                print(f"Created order page id: {res.get('id')} for {data['order_id']}")
            except Exception as e:
                print(f"Failed to create order {data['order_id']}: {e}")


if __name__ == "__main__":
    main()
