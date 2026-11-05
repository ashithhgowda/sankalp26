import asyncio

import httpx

from backend import emailer


BREVO_API_KEY = "xkeysib-test-secret"
RECIPIENT = "recipient@example.org"


def _configure_brevo(monkeypatch):
    monkeypatch.setenv("BREVO_API_KEY", BREVO_API_KEY)
    monkeypatch.setenv("EMAIL_FROM_NAME", "SANKALP'26")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "verified@example.org")
    monkeypatch.setenv("EMAIL_REPLY_TO", "replies@example.org")
    monkeypatch.delenv("INTEGRATION_PROXY_URL", raising=False)
    monkeypatch.delenv("EMERGENT_EMAIL_KEY", raising=False)


def _mock_http_client(monkeypatch, handler):
    real_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        emailer.httpx,
        "AsyncClient",
        lambda **kwargs: real_async_client(
            transport=httpx.MockTransport(handler), **kwargs
        ),
    )


def test_send_email_uses_brevo_transactional_api(monkeypatch):
    _configure_brevo(monkeypatch)
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(201, json={"messageId": "<brevo-message-id>"})

    _mock_http_client(monkeypatch, handler)
    receipt = asyncio.run(emailer.send_email(
        to=RECIPIENT,
        subject="Judge invitation",
        html="<p>Use your activation link.</p>",
    ))

    assert receipt == "<brevo-message-id>"
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "POST"
    assert str(request.url) == "https://api.brevo.com/v3/smtp/email"
    assert request.headers["api-key"] == BREVO_API_KEY
    assert request.read() == (
        b'{"sender":{"name":"SANKALP\'26","email":"verified@example.org"},'
        b'"to":[{"email":"recipient@example.org"}],"subject":"Judge invitation",'
        b'"htmlContent":"<p>Use your activation link.</p>",'
        b'"replyTo":{"email":"replies@example.org"}}'
    )


def test_send_email_returns_none_for_brevo_api_rejection(monkeypatch, caplog):
    _configure_brevo(monkeypatch)

    def handler(_request):
        return httpx.Response(
            401,
            json={"code": "unauthorized", "message": f"Rejected {BREVO_API_KEY} for {RECIPIENT}"},
        )

    _mock_http_client(monkeypatch, handler)
    receipt = asyncio.run(emailer.send_email(
        to=RECIPIENT, subject="Judge invitation", html="<p>Activation</p>"
    ))

    assert receipt is None
    assert "HTTP 401" in caplog.text
    assert BREVO_API_KEY not in caplog.text
    assert RECIPIENT not in caplog.text


def test_send_email_returns_none_on_brevo_timeout(monkeypatch, caplog):
    _configure_brevo(monkeypatch)

    def handler(_request):
        raise httpx.ReadTimeout("simulated timeout")

    _mock_http_client(monkeypatch, handler)
    receipt = asyncio.run(emailer.send_email(
        to=RECIPIENT, subject="Judge invitation", html="<p>Activation</p>"
    ))

    assert receipt is None
    assert "timed out" in caplog.text
    assert BREVO_API_KEY not in caplog.text
    assert RECIPIENT not in caplog.text
