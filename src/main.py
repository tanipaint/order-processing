#!/usr/bin/env python3
"""
メインエントリポイントおよびFastAPIアプリケーションの初期設定
"""
import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request

# .envファイルから環境変数をロード
load_dotenv()

app = FastAPI(
    title="注文処理システム",
    description="注文受付から承認ワークフローまでを実行するAPI",
    version="0.1.0",
)


@app.get("/health", summary="ヘルスチェック")
async def health_check():
    """サービスのヘルスチェックエンドポイント"""
    return {"status": "ok"}


def main():
    """アプリケーション起動ポイント"""
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=port,
        reload=bool(os.environ.get("DEV", False)),
    )


if __name__ == "__main__":
    main()


@app.post("/slack/events")
async def slack_events(req: Request):
    """Slack Events API 用エンドポイント"""
    from src.phase3.slack_app import slack_handler

    # Boltアプリへリクエストをハンドル (Starlette adapter)
    return await slack_handler.handle(req)
