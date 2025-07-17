"""Phase3: Slack Bot 基盤セットアップ (Bolt for Python ASGI integration)"""
# .envファイルから環境変数をロード
import json
import os
from datetime import datetime

# .envファイルから環境変数をロード
try:
    from dotenv import load_dotenv
except ImportError:

    def load_dotenv():
        """dotenv未インストール時のダミー実装"""
        pass


from slack_bolt import App
from slack_bolt.adapter.starlette import SlackRequestHandler

from src.phase4.notion_client import NotionClient
from src.phase4.order_service import OrderService

# .envファイルから環境変数をロード
load_dotenv()

# 環境変数からトークンと署名シークレットを取得
slack_token = os.environ.get("SLACK_BOT_TOKEN")
signing_secret = os.environ.get("SLACK_SIGNING_SECRET")

# Bolt App (sync) 初期化
# テスト環境での署名検証回避も可能
slack_app = App(
    token=slack_token,
    signing_secret=signing_secret,
    token_verification_enabled=False,
    request_verification_enabled=False,
)

# ASGI ハンドラ
slack_handler = SlackRequestHandler(slack_app)


@slack_app.action("approve")
def handle_approve(ack, body, client, logger):
    """承認ボタン押下時のハンドラ: メッセージを更新して承認者を記録する。"""
    ack()
    user_id = body["user"]["id"]
    channel_id = body["channel"]["id"]
    message_ts = body["message"]["ts"]
    # 承認イベントのタイムスタンプ
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    logger.info(f"approve button clicked by {user_id} at {ts}")
    # actions ブロックを承認ステータス表示に置き換え
    # また、Notionに注文登録＆在庫更新を実行し、その結果を追加表示する
    # ボタン要素のvalueに埋め込んだ注文データを取得（テスト時はbody.actionsがない場合もある）
    order_data = {}
    actions = body.get("actions") or []
    if actions:
        val = actions[0].get("value", "{}")
        try:
            order_data = json.loads(val)
        except Exception:
            order_data = {}
    # Notion連携処理
    notion = NotionClient()
    service = OrderService(notion)
    order_id = f"ORD{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    try:
        service.process_order(
            {
                "order_id": order_id,
                "customer_name": order_data.get("customer_name"),
                "product_id": order_data.get("product_id"),
                "quantity": order_data.get("quantity"),
                "delivery_date": order_data.get("delivery_date"),
                "status": "承認済",
                "approved_by": user_id,
            }
        )
        notion_status = f"🗒 Notion登録済: {order_id}"
    except Exception as e:
        logger.error(f"Notion registration failed: {e}", exc_info=True)
        notion_status = f"❗️ Notion登録失敗: {e}"

    updated_blocks = []
    for block in body["message"]["blocks"]:
        if block.get("type") == "actions":
            updated_blocks.append(
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": f"✅ 承認 by <@{user_id}> ({ts})"}
                    ],
                }
            )
        else:
            updated_blocks.append(block)
    # Notion登録結果を表示
    updated_blocks.append(
        {"type": "context", "elements": [{"type": "mrkdwn", "text": notion_status}]}
    )
    client.chat_update(channel=channel_id, ts=message_ts, blocks=updated_blocks)


@slack_app.action("reject")
def handle_reject(ack, body, client, logger):
    """差し戻しボタン押下時のハンドラ: メッセージを更新して差し戻しを記録する。"""
    ack()
    user_id = body["user"]["id"]
    channel_id = body["channel"]["id"]
    message_ts = body["message"]["ts"]
    # 差し戻しイベントのタイムスタンプ
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    logger.info(f"reject button clicked by {user_id} at {ts}")
    # actions ブロックを差し戻しステータス表示に置き換え（差し戻し者と時刻を表示）
    updated_blocks = []
    for block in body["message"]["blocks"]:
        if block.get("type") == "actions":
            updated_blocks.append(
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": f"❌ 差し戻し by <@{user_id}> ({ts})"}
                    ],
                }
            )
        else:
            updated_blocks.append(block)
    client.chat_update(channel=channel_id, ts=message_ts, blocks=updated_blocks)
