"""Phase3: Slack Bot 基盤セットアップ (Bolt for Python ASGI integration)"""
import os

from slack_bolt.adapter.asgi import AsyncSlackRequestHandler
from slack_bolt.async_app import AsyncApp

# 環境変数からトークンと署名シークレットを取得
slack_token = os.environ.get("SLACK_BOT_TOKEN")
signing_secret = os.environ.get("SLACK_SIGNING_SECRET")

# Bolt AsyncApp 初期化
slack_app = AsyncApp(token=slack_token, signing_secret=signing_secret)

# ASGI ハンドラ
slack_handler = AsyncSlackRequestHandler(slack_app)
