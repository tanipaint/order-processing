"""Phase5: 顧客への自動返信メール送信クライアント"""
import os
import smtplib
from email.mime.text import MIMEText

from dotenv import load_dotenv


class EmailClient:
    """SMTPを使ってメール送信を行うクライアント"""

    def __init__(self):
        load_dotenv()
        host = os.getenv("SMTP_HOST")
        port = os.getenv("SMTP_PORT")
        user = os.getenv("SMTP_USER")
        password = os.getenv("SMTP_PASSWORD")
        if not host or not port or not user or not password:
            raise ValueError(
                "Missing SMTP_HOST/SMTP_PORT/SMTP_USER/SMTP_PASSWORD env vars"
            )
        self.host = host
        self.port = int(port)
        self.user = user
        self.password = password

    def send_email(self, to_address: str, subject: str, body: str) -> None:
        """指定宛先にテキストメールを送信する"""
        msg = MIMEText(body, _charset="utf-8")
        msg["Subject"] = subject
        msg["From"] = self.user
        msg["To"] = to_address

        with smtplib.SMTP(self.host, self.port) as smtp:
            smtp.starttls()
            smtp.login(self.user, self.password)
            smtp.send_message(msg)
