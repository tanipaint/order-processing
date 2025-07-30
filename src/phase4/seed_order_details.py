"""注文明細データを Notion の order_details テーブルへ登録するスクリプト"""
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
            # preserve time if format includes time
            if "H" in fmt:
                return dt.isoformat()
            return dt.date().isoformat()
        except Exception:
            continue
    return s


def main():
    load_dotenv()
    client = NotionClient()
    path = "doc/order_details.csv"
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # orders and products columns contain '<id> (<url>)'
            order_page_id = row.get("orders", "").split()[0]
            product_page_id = row.get("products", "").split()[0]
            data = {
                "id": row.get("id", ""),
                "order_page_id": order_page_id,
                "product_page_id": product_page_id,
                "quantity": int(row.get("quantity", 0)),
                "sub_total": float(row.get("sub_total", 0)),
                "created_at": parse_jp_date(row.get("created_at", "")),
            }
            try:
                res = client.create_order(data)
                print(f"Created order_detail page id: {res.get('id')} for {data['id']}")
            except Exception as e:
                print(f"Failed to create order_detail {data['id']}: {e}")


if __name__ == "__main__":
    main()
