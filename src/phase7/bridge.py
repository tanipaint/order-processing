"""Phase7: メール受信リスナーとSlack通知を橋渡しするブリッジスクリプト"""
# ログ設定
import logging
import os
import time

from dotenv import load_dotenv

from src.phase2.transform import parse_order
from src.phase3.message import build_order_notification
from src.phase3.slack_app import slack_app
from src.phase4.notion_client import NotionClient
from src.phase4.order_service import OrderService
from src.phase7.email_listener import EmailListener, parse_email_body

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# .envファイルから環境変数をロード
load_dotenv()

# ポーリング間隔（秒）
POLL_INTERVAL = int(os.getenv("IMAP_POLL_INTERVAL", "60"))
# 通知先Slackチャンネル
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL")


def main():
    if not SLACK_CHANNEL:
        raise ValueError("Missing SLACK_CHANNEL environment variable")
    listener = EmailListener()
    notion = NotionClient()
    order_service = OrderService(notion)

    logger.info(
        f"Starting email->Slack bridge: poll_interval={POLL_INTERVAL}s, channel={SLACK_CHANNEL}"
    )

    while True:
        logger.info("Polling for new emails…")
        try:
            raws = listener.fetch_unseen_emails()
        except Exception as e:
            logger.error(f"Error during IMAP polling: {e}", exc_info=True)
            time.sleep(POLL_INTERVAL)
            continue
        logger.info(f"  → found {len(raws)} unseen email(s)")
        for num, raw in raws:
            try:
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
                logger.info(f"Posting notification to Slack channel {SLACK_CHANNEL}")
                slack_app.client.chat_postMessage(
                    channel=SLACK_CHANNEL,
                    **payload,
                )
                # 正常処理したメールは既読にする
                listener.mark_as_seen(num)
                logger.info(f"Marked email {num!r} as seen")
            except Exception as e:
                logger.error(f"Failed to process email: {e}", exc_info=True)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
