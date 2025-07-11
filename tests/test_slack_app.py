import pytest

# TODO: CI 環境での依存不整合を解消予定のため一時的にファイル全体をスキップ
pytest.skip("Skip Slack app initialization tests", allow_module_level=True)


@pytest.fixture(autouse=True)
def set_slack_env(monkeypatch):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token")
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "test-secret")


def test_slack_app_initialization():
    import importlib

    mod = importlib.reload(
        __import__("src.phase3.slack_app", fromlist=["slack_app", "slack_handler"])
    )
    assert hasattr(mod, "slack_app"), "slack_app が存在しません"
    assert hasattr(mod, "slack_handler"), "slack_handler が存在しません"
    from slack_bolt.async_app import AsyncApp

    assert isinstance(mod.slack_app, AsyncApp)
