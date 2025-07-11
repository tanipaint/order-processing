"""Phase2: メール受信インターフェース（スタブ実装）"""


def read_email_file(file_path: str) -> str:
    """テスト用メール受信スタブ: ファイルからメール本文を取得する"""
    with open(file_path, encoding="utf-8") as f:
        return f.read()
