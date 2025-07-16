"""Phase7: メール受信リスナーとSlack通知を橋渡しするブリッジスクリプト"""
import os
import time

from dotenv import load_dotenv

from src.phase2.transform import parse_order
from src.phase3.message import build_order_notification
from src.phase3.slack_app import slack_app
from src.phase4.notion_client import NotionClient
from src.phase4.order_service import OrderService
from src.phase7.email_listener import EmailListener, parse_email_body

# .envファイルから環境変数をロード
load_dotenv()

# ポーリング間隔（秒）
POLL_INTERVAL = int(os.getenv("IMAP_POLL_INTERVAL", "60"))
# 通知先Slackチャンネル
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL")


def main():
    listener = EmailListener()
    notion = NotionClient()
    order_service = OrderService(notion)

    while True:
        raws = listener.fetch_unseen_emails()
        for raw in raws:
            text = parse_email_body(raw)
            # 注文抽出
            order = parse_order(text)
            # 在庫チェック
            in_stock = order_service.check_stock(order.product_id, order.quantity)
            # Slack通知メッセージ生成
            payload = build_order_notification(
                original_text=text,
                extracted=vars(order),
                in_stock=in_stock,
            )
            # 送信
            slack_app.client.chat_postMessage(
                channel=SLACK_CHANNEL,
                **payload,
            )
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
