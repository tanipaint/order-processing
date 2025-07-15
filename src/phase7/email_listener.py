"""Phase7: IMAPメール受信リスナーとメール本文パースロジック"""
import email
import imaplib
import os

try:
    from dotenv import load_dotenv
except ImportError:

    def load_dotenv():
        """dotenv未インストール時のダミー実装"""
        pass


# .envファイルから環境変数をロード
load_dotenv()


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

    def fetch_unseen_emails(self):
        """未読メールを取得し、再取得しないよう既読にする"""
        if self.mail is None:
            self.connect()
        status, data = self.mail.search(None, "UNSEEN")
        if status != "OK":
            return []
        messages = data[0].split()
        emails = []
        for num in messages:
            ok, parts = self.mail.fetch(num, "(RFC822)")
            if ok != "OK":
                continue
            raw = parts[0][1]
            emails.append(raw)
            # 取得後は既読にする
            self.mail.store(num, "+FLAGS", "\\Seen")
        return emails


def parse_email_body(raw_email: bytes) -> str:
    """MIMEマルチパートから本文(text/plain)を抽出し、テキストを返す"""
    msg = email.message_from_bytes(raw_email)
    texts = []
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = part.get("Content-Disposition", "")
            if ctype == "text/plain" and "attachment" not in disp:
                charset = part.get_content_charset() or "utf-8"
                payload = part.get_payload(decode=True) or b""
                texts.append(payload.decode(charset, errors="replace"))
    else:
        if msg.get_content_type() == "text/plain":
            charset = msg.get_content_charset() or "utf-8"
            payload = msg.get_payload(decode=True) or b""
            texts.append(payload.decode(charset, errors="replace"))
    return "\n".join(texts)
