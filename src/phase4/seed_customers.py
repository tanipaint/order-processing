"""顧客データを Notion の customers テーブルへ登録するスクリプト"""
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
    # 例: '2025年7月18日' or '2025年7月18日 10:44'
    for fmt in ("%Y年%m月%d日 %H:%M", "%Y年%m月%d日"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.isoformat()
        except Exception:
            continue
    return s


def main():
    load_dotenv()
    client = NotionClient()
    path = "doc/customers.csv"
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            data = {
                "customer_name": row["customer_name"],
                "email": row.get("email", ""),
                "first_order_date": parse_jp_date(row.get("first_order_date", "")),
                "is_existing": row.get("is_existing", "").lower()
                in ("yes", "true", "1"),
                "created_at": parse_jp_date(row.get("created_at", "")),
            }
            try:
                res = client.create_customer(data)
                print(f"Created customer page id: {res.get('id')} for {row['id']}")
            except Exception as e:
                print(f"Failed to create customer {row.get('id')}: {e}")


if __name__ == "__main__":
    main()
