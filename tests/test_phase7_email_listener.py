import imaplib

import pytest

from src.phase7.email_listener import EmailListener, parse_email_body


def test_email_listener_missing_env(monkeypatch):
    monkeypatch.delenv("IMAP_HOST", raising=False)
    monkeypatch.delenv("IMAP_USER", raising=False)
    monkeypatch.delenv("IMAP_PASS", raising=False)
    with pytest.raises(ValueError):
        EmailListener()


def test_connect_and_login(monkeypatch):
    events = {}

    class DummyIMAP:
        def __init__(self, host):
            events["host"] = host
            self.logged_in = False

        def login(self, user, password):
            events["login"] = (user, password)
            self.logged_in = True

        def select(self, box):
            events["select"] = box

    monkeypatch.setenv("IMAP_HOST", "imap.example.com")
    monkeypatch.setenv("IMAP_USER", "user@example.com")
    monkeypatch.setenv("IMAP_PASS", "secret")
    monkeypatch.setattr(imaplib, "IMAP4_SSL", DummyIMAP)

    listener = EmailListener()
    listener.connect()
    assert events["host"] == "imap.example.com"
    assert events["login"] == ("user@example.com", "secret")
    assert events["select"] == "INBOX"


def test_fetch_unseen_emails_and_mark_seen(monkeypatch):
    class DummyMail:
        def __init__(self):
            self._store = []

        def search(self, charset, criterion):
            return "OK", [b"1 2"]

        def fetch(self, num, spec):
            return "OK", [(None, b"RAW_CONTENT_" + num)]

        def store(self, num, flags, flag):
            self._store.append((num, flags, flag))

    monkeypatch.setenv("IMAP_HOST", "h")
    monkeypatch.setenv("IMAP_USER", "u")
    monkeypatch.setenv("IMAP_PASS", "p")
    listener = EmailListener()
    dummy = DummyMail()
    listener.mail = dummy
    mails = listener.fetch_unseen_emails()
    assert mails == [b"RAW_CONTENT_1", b"RAW_CONTENT_2"]
    assert dummy._store == [(b"1", "+FLAGS", "\\Seen"), (b"2", "+FLAGS", "\\Seen")]


def test_parse_email_body_plain_and_multipart():
    # plain text email
    raw_plain = b"Content-Type: text/plain; charset=utf-8\r\n\r\nHello World"
    assert parse_email_body(raw_plain).strip() == "Hello World"

    # multipart email with text/plain and text/html
    boundary = b"BOUND"
    raw_multi = (
        b"Content-Type: multipart/alternative; boundary=" + boundary + b"\r\n\r\n"
    )
    raw_multi += (
        b"--"
        + boundary
        + b"\r\nContent-Type: text/plain; charset=utf-8\r\n\r\nPlain Text\r\n"
    )
    raw_multi += (
        b"--"
        + boundary
        + b"\r\nContent-Type: text/html; charset=utf-8\r\n\r\n<html>HTML</html>\r\n"
    )
    raw_multi += b"--" + boundary + b"--\r\n"
    assert "Plain Text" in parse_email_body(raw_multi)
