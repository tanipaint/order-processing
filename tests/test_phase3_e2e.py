import pytest


@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    # テスト用環境変数設定 (.env読み込み後に上書き)
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token")
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "test-secret")
    # Notion連携スタブ用: 環境変数をセット
    monkeypatch.setenv("NOTION_API_KEY", "dummy")
    monkeypatch.setenv("NOTION_DATABASE_ID_PRODUCTS", "pid")
    monkeypatch.setenv("NOTION_DATABASE_ID_CUSTOMERS", "cid")
    monkeypatch.setenv("NOTION_DATABASE_ID_ORDERS", "oid")


@pytest.fixture(autouse=True)
def prepare_app(monkeypatch, setup_env):
    # モジュールをリロードしてテスト用envを反映
    import importlib

    mod = importlib.reload(
        __import__("src.phase3.slack_app", fromlist=["slack_app", "slack_handler"])
    )
    # OrderService.process_order をスタブ化（NotionClientとの実接続を回避）
    from src.phase4.order_service import OrderService

    monkeypatch.setattr(OrderService, "process_order", lambda self, o: {})
    # chat_update をモック
    calls = []

    def fake_update(channel: str, ts: str, blocks: list):
        calls.append({"channel": channel, "ts": ts, "blocks": blocks})

    monkeypatch.setattr(mod.slack_app.client, "chat_update", fake_update)
    return calls


@pytest.mark.parametrize("action_type, emoji", [("approve", "✅"), ("reject", "❌")])
def test_action_handlers_e2e(action_type, emoji, prepare_app):
    import src.phase3.slack_app as slack_mod

    calls = prepare_app
    # ハンドラ取得
    handler = (
        slack_mod.handle_approve
        if action_type == "approve"
        else slack_mod.handle_reject
    )
    # ダミーpayload
    user_id = "U1"
    channel_id = "C1"
    ts = "12345.6789"
    body = {
        "user": {"id": user_id},
        "channel": {"id": channel_id},
        "message": {"ts": ts, "blocks": [{"type": "actions"}]},
    }

    # ack モック
    ack_calls = []

    def ack():
        ack_calls.append(True)

    # 実行
    handler(ack, body, slack_mod.slack_app.client, slack_mod.slack_app.logger)
    # ack と chat_update が呼ばれた
    assert ack_calls, "ack が呼ばれていません"
    assert len(calls) == 1, "chat_update が呼ばれていません"
    # コンテキストブロックに emoji が含まれる
    blocks = calls[0]["blocks"]
    assert any(
        b.get("type") == "context" and elem.get("text", "").startswith(emoji)
        for b in blocks
        for elem in b.get("elements", [])
    ), f"{action_type} によるcontextブロックが正しくありません"
