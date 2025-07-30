import json
import os

# Bolt App 初期化時の env var チェックをスキップするためダミー設定
os.environ.setdefault("SLACK_BOT_TOKEN", "xoxb-test")  # noqa: E501
os.environ.setdefault("SLACK_SIGNING_SECRET", "test-secret")  # noqa: E501
from src.phase3.slack_app import handle_approve  # noqa: E402


class DummyClient:
    def __init__(self):
        self.updated = []
        self.views = []

    def chat_update(self, channel, ts, blocks, **kwargs):
        self.updated.append((channel, ts, blocks))

    def views_open(self, trigger_id, view):
        self.views.append((trigger_id, view))


def make_body():
    # Minimal body with actions and metadata
    payload = {
        "customer_name": "C",
        "product_id": "P",
        "quantity": 1,
        "delivery_date": "2025-01-01",
    }
    return {
        "user": {"id": "U1"},
        "channel": {"id": "C1"},
        "message": {
            "ts": "123",
            "blocks": [
                {
                    "type": "actions",
                    "elements": [{"value": json.dumps(payload)}],
                }  # noqa: E501
            ],
        },
        "trigger_id": "T1",
    }


def test_handle_approve_opens_modal_and_updates_message(monkeypatch):
    client = DummyClient()
    acked = []

    def ack():
        acked.append(True)

    body = make_body()
    # call handler
    handle_approve(
        ack,
        body,
        client,
        logger=type("L", (), {"debug": lambda *a, **k: None}),
    )
    # ack
    assert acked
    # chat_update invoked with context block containing ✅
    assert client.updated
    channel, ts, blocks = client.updated[0]
    assert channel == "C1" and ts == "123"
    assert any(b.get("type") == "context" for b in blocks)
    # views_open called
    assert client.views and client.views[0][0] == "T1"
