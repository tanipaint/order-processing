"""Phase3: Slack Bot 基盤セットアップ (Bolt for Python ASGI integration)"""
# .envファイルから環境変数をロード
import os
from datetime import datetime

try:
    from dotenv import load_dotenv
except ImportError:

    def load_dotenv():
        """dotenv未インストール時のダミー実装"""
        pass


from slack_bolt import App
from slack_bolt.adapter.starlette import SlackRequestHandler

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
    # actions ブロックを承認ステータス表示に置き換え（承認者と時刻を表示）
    updated_blocks = []
    for block in body["message"]["blocks"]:
        if block.get("type") == "actions":
            updated_blocks.append(
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"✅ 承認 by <@{user_id}> ({ts})",
                        }
                    ],
                }
            )
        else:
            updated_blocks.append(block)
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
