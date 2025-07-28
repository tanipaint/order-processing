"""Phase7: IMAPメール受信リスナーとメール本文パースロジック"""
import email
import imaplib
import logging
import os

try:
    from dotenv import load_dotenv
except ImportError:

    def load_dotenv():
        """dotenv未インストール時のダミー実装"""
        pass


# .envファイルから環境変数をロード
load_dotenv()


logger = logging.getLogger(__name__)


class EmailListener:
    """IMAPを使って新着メールを取得するリスナー"""

    def __init__(self):
        host = os.getenv("IMAP_HOST")
        user = os.getenv("IMAP_USER")
        password = os.getenv("IMAP_PASS")
        if not host or not user or not password:
            raise ValueError("Missing IMAP_HOST/IMAP_USER/IMAP_PASS env vars")
        self.host = host
        self.user = user
        self.password = password
        self.mail = None

    def connect(self):
        """IMAPサーバへ接続し、INBOXを選択する"""
        self.mail = imaplib.IMAP4_SSL(self.host)
        self.mail.login(self.user, self.password)
        self.mail.select("INBOX")
        logger.info(f"IMAP connected to {self.host} as {self.user}")

    def fetch_unseen_emails(self):
        """未読メールを取得する。既読フラグは外部で制御する"""
        if self.mail is None:
            self.connect()
        else:
            # 再ポーリング時もINBOXを再選択 (Gmail等で必要な場合あり)
            try:
                self.mail.select("INBOX")
                logger.debug("Re-selected INBOX mailbox")
            except AttributeError:
                # テストダブルなどで select が未実装の場合はスキップ
                pass
        logger.debug("Searching for UNSEEN emails")
        status, data = self.mail.search(None, "UNSEEN")
        logger.debug(f"Search result: status={status}, data={data}")
        if status != "OK":
            logger.error("IMAP search failed")
            return []
        messages = data[0].split()
        results = []
        for num in messages:
            ok, parts = self.mail.fetch(num, "(RFC822)")
            if ok != "OK":
                logger.warning(f"Failed to fetch email {num!r}")
                continue
            raw = parts[0][1]
            results.append(raw)
            # 取得したメールを既読に設定
            self.mail.store(num, "+FLAGS", "\\Seen")
            logger.info(f"Email {num!r} flagged as Seen on server")
        return results

    def mark_as_seen(self, num):
        """指定したメッセージ番号を既読にする"""
        if self.mail is None:
            self.connect()
        self.mail.store(num, "+FLAGS", "\\Seen")
        logger.info(f"Email {num!r} flagged as Seen on server")


def parse_email_body(raw_email: bytes) -> str:
    """MIMEマルチパートから本文(text/plain)を抽出し、テキストを返す"""
    msg = email.message_from_bytes(raw_email)
    body_texts = []
    pdf_payload = None
    # Walk parts to collect body text and PDF attachment
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = part.get("Content-Disposition", "")
            # PDF attachment
            if ctype == "application/pdf" or (
                "attachment" in disp and ctype == "application/octet-stream"
            ):
                pdf_payload = part.get_payload(decode=True)
                continue
            # text/plain body parts
            if ctype == "text/plain" and "attachment" not in disp:
                charset = part.get_content_charset() or "utf-8"
                payload = part.get_payload(decode=True) or b""
                body_texts.append(payload.decode(charset, errors="replace"))
    else:
        # Single part, treat as plain text
        if msg.get_content_type() == "text/plain":
            charset = msg.get_content_charset() or "utf-8"
            payload = msg.get_payload(decode=True) or b""
            body_texts.append(payload.decode(charset, errors="replace"))
    body = "\n".join(body_texts)
    # If PDF attachment found, return both body text and PDF bytes
    if pdf_payload:
        return {"body": body, "pdf": pdf_payload}
    # Otherwise return body text
    return body
