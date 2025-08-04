# -*- coding: utf-8 -*-
"""
# conftest for pytest: ensure project root is on PYTHONPATH
"""
import os
import sys

import pytest

# プロジェクトルートを sys.path に追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture(autouse=True)
def clear_openai_key(monkeypatch):
    """
    テスト実行時はデフォルトで OPENAI_API_KEY をクリアし、スタブ実行を保証する
    特定のテストで real LLM 呼び出しをテストする場合は monkeypatch.setenv を利用してください
    """
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
