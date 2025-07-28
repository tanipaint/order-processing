"""Phase2: OCR処理モジュール（スタブ実装）"""


def ocr_process(input_data) -> str:
    """テスト用OCRスタブ: 入力データをそのまま返す。
    PDFバイナリの場合はPdfReaderでテキスト抽出する。"""
    # PDFデータを処理する場合（バイナリまたはPDFヘッダー検出）
    # PDFバイト列の場合はBytesIOから直接読み込む
    # PDF添付バイト列をBytesIOで読み込み、テキスト抽出
    pdf_bytes = None
    if isinstance(input_data, (bytes, bytearray)):
        pdf_bytes = input_data
    elif isinstance(input_data, str) and input_data.lstrip().startswith("%PDF"):
        pdf_bytes = input_data.encode("utf-8", errors="replace")
    if pdf_bytes:
        try:
            from io import BytesIO

            from PyPDF2 import PdfReader

            reader = PdfReader(BytesIO(pdf_bytes))
            text_parts = [page.extract_text() or "" for page in reader.pages]
            return "\n".join(text_parts)
        except ImportError:
            # PyPDF2がインストールされていない場合はOCR未実装扱い
            return ""
        except Exception:
            # PDF処理失敗時は空文字を返す
            return ""
    # bytesのまま受け取るケースは文字列化
    if isinstance(input_data, (bytes, bytearray)):
        return input_data.decode("utf-8", errors="replace")
    # 通常テキストはそのまま返却
    return input_data
