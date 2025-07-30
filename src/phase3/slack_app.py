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
from src.phase5.email_client import EmailClient

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
    """承認ボタン押下時のハンドラ: モーダルを開いて注文内容を最終確認する。"""
    ack()
    # 元メッセージを更新して承認ステータスを反映
    user_id = body["user"]["id"]
    channel_id = body["channel"]["id"]
    message_ts = body["message"]["ts"]
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    updated_blocks = []
    for block in body.get("message", {}).get("blocks", []):
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
    client.chat_update(channel=channel_id, ts=message_ts, blocks=updated_blocks)
    # 抽出データを取得
    order_data = {}
    actions = body.get("actions") or []
    if actions:
        try:
            order_data = json.loads(actions[0].get("value", "{}"))
        except Exception:
            order_data = {}
    # マルチ商品注文はモーダルを省略し直接登録
    if order_data.get("items"):
        from src.phase4.notion_client import NotionClient
        from src.phase4.order_service import OrderService
        from src.phase5.email_client import EmailClient

        notion = NotionClient()
        service = OrderService(notion, EmailClient())
        order_id = f"ORD{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        # 登録処理
        try:
            service.process_order(
                {
                    "order_id": order_id,
                    **order_data,
                    "status": "approved",
                    "approved_by": body["user"]["id"],
                }
            )
            # メッセージに登録完了を追加
            client.chat_postMessage(
                channel=body["channel"]["id"],
                thread_ts=body["message"]["ts"],
                text=f":white_check_mark: 注文 {order_id} を登録しました",
            )
        except Exception as e:
            logger.error(f"Order registration failed: {e}")
        return
    # 単一商品はモーダルで確認・修正してもらう
    try:
        client.views_open(
            trigger_id=body.get("trigger_id"),
            view={
                "type": "modal",
                "callback_id": "注文内容確認",
                "title": {"type": "plain_text", "text": "注文内容確認"},
                "submit": {"type": "plain_text", "text": "確定"},
                "blocks": [
                    {
                        "type": "input",
                        "block_id": "cust",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "customer_name",
                            "initial_value": order_data.get("customer_name", ""),
                        },
                        "label": {"type": "plain_text", "text": "顧客名"},
                    },
                    {
                        "type": "input",
                        "block_id": "prod",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "product_id",
                            "initial_value": order_data.get("product_id", ""),
                        },
                        "label": {"type": "plain_text", "text": "商品ID"},
                    },
                    {
                        "type": "input",
                        "block_id": "qty",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "quantity",
                            "initial_value": str(order_data.get("quantity", "")),
                        },
                        "label": {"type": "plain_text", "text": "数量"},
                    },
                    {
                        "type": "input",
                        "block_id": "del",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "delivery_date",
                            "initial_value": order_data.get("delivery_date", ""),
                        },
                        "label": {"type": "plain_text", "text": "配送希望日"},
                    },
                ],
            },
        )
    except Exception:
        logger.debug("views_open skipped (test env)")


@slack_app.view("注文内容確認")
def view_submission(ack, body, client, logger):
    """モーダル送信時: 入力内容をもとに注文処理を実行し、Slackメッセージを更新する。"""
    ack()
    vals = body["view"]["state"]["values"]
    fixed = {
        "customer_name": vals["cust"]["customer_name"]["value"],
        "product_id": vals["prod"]["product_id"]["value"],
        "quantity": int(vals["qty"]["quantity"]["value"]),
        "delivery_date": vals["del"]["delivery_date"]["value"],
    }
    notion = NotionClient()
    service = OrderService(notion)
    order_id = f"ORD{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    # 実際の注文登録＆在庫更新
    try:
        service.process_order(
            {
                "order_id": order_id,
                **fixed,
                "status": "承認済",
                "approved_by": body["user"]["id"],
            }
        )
    except Exception as e:
        logger.error(f"Notion registration failed: {e}", exc_info=True)
    # 元メッセージを更新
    # private_metadataにmessage_tsやchannelを事前格納している場合は利用
    # 今回は省略: 別途実装を検討してください
    # TODO: Slackメッセージ更新処理を適切に実装


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
    # 差し戻し時の自動返信メール送信（オプション）
    try:
        # ボタンvalueに埋め込んだ注文データを取得
        order_data = {}
        actions = body.get("actions") or []
        if actions:
            order_data = json.loads(actions[0].get("value", "{}"))
        email_client = EmailClient()
        # 顧客のメールアドレス取得
        cust_page = NotionClient().get_customer(order_data.get("customer_name", ""))
        email_addr = (
            cust_page.get("properties", {}).get("email", {}).get("email")
            if cust_page
            else None
        )
        if email_addr:
            subject = "ご注文の差し戻し通知"
            body_text = (
                f"{order_data.get('customer_name', '')} 様\n"
                "お客様のご注文が差し戻されました。\n"
                "お手数ですが再度ご確認のうえご連絡ください。"
            )
            email_client.send_email(email_addr, subject, body_text)
    except Exception as e:
        logger.error(f"failed to send rejection email: {e}", exc_info=True)
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
    client.chat_update(
        channel=channel_id,
        ts=message_ts,
        blocks=updated_blocks,
        text=f"注文の差し戻し: <@{user_id}> ({ts})",
    )
