# -*- coding: utf-8 -*-
"""
# conftest for pytest: ensure project root is on PYTHONPATH
"""
import os
import sys

# プロジェクトルートを sys.path に追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
