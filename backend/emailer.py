import os
import re
import ipaddress
import logging
import asyncio
import smtplib
import socket
import ssl
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx

logger = logging.getLogger("sankalp.email")


def _configured(value: str) -> bool:
    value = value.strip().lower()
    return bool(value) and not any(marker in value for marker in ("your-", "replace-with", "changeme", "example.com", ".example", "<"))

_SHORTENERS = ("bit.ly", "tinyurl.com", "t.co", "is.gd", "cutt.ly", "goo.gl", "rebrand.ly")
_CRED_ASK = ("reply with your password", "reply with the code", "send your password", "cvv",
             "send us your password", "enter your password below", "confirm your card number",
             "your full card number", "seed phrase", "recovery phrase", "verify your card",
             "social security number", "confirm your bank details")
_HOSTISH = re.compile(r"\b(?:https?://)?((?:[a-z0-9-]+\.)+[a-z]{2,})", re.I)


def _host_ok(host: str) -> bool:
    if not host or "xn--" in host:
        return False
    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        pass
    return not any(host == s or host.endswith("." + s) for s in _SHORTENERS)


def _same_site(shown: str, real: str) -> bool:
    return shown == real or real.endswith("." + shown) or shown.endswith("." + real)


def _is_local_development_http(value: str) -> bool:
    if os.environ.get("APP_ENV", "development").strip().lower() != "development":
        return False
    parsed = urlparse(value)
    return (parsed.scheme == "http" and parsed.hostname in ("localhost", "127.0.0.1")
            and parsed.username is None and parsed.password is None)


class _EmailScan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.urls, self.anchors = set(), [], []
        self._href, self._text = None, []

    def handle_starttag(self, tag, attrs):
        self.tags.add(tag.lower())
        self.urls += [v for k, v in attrs if k.lower() in ("href", "src") and v]
        if tag.lower() == "a":
            self._href = dict((k.lower(), v) for k, v in attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href is not None:
            self.anchors.append((self._href, "".join(self._text)))
            self._href, self._text = None, []


def _assert_safe_email(subject: str, html: str) -> None:
    scan = _EmailScan()
    scan.feed(html)
    if scan.tags & {"form", "input", "textarea", "select"}:
        raise ValueError("G2: email contains a prohibited form or input element")
    body = f"{subject}\n{html}".lower()
    for p in _CRED_ASK:
        if p in body:
            raise ValueError("G2: email contains a prohibited credential request")
    for url in scan.urls:
        low = url.strip().lower()
        if low.startswith(("mailto:", "tel:", "cid:", "#")):
            continue
        parsed = urlparse(low)
        local_http = _is_local_development_http(low)
        if parsed.scheme != "https" and not local_http:
            raise ValueError("G3: every email link and asset must use absolute HTTPS")
        try:
            parsed.port
        except ValueError as exc:
            raise ValueError("G3: email URL has an invalid port") from exc
        host = parsed.hostname or ""
        if parsed.username is not None or parsed.password is not None or (not local_http and not _host_ok(host)):
            raise ValueError("G3: email link host is disallowed or URL contains credentials")
    for href, text in scan.anchors:
        real = urlparse(href.strip().lower()).hostname or ""
        if not real:
            continue
        for m in _HOSTISH.finditer(text):
            if not _same_site(m.group(1).lower(), real):
                raise ValueError("G3: email anchor text host does not match its destination host")


async def send_email(*, to: str, subject: str, html: str):
    """Return a transport receipt on acceptance, or None when delivery cannot be attempted."""
    try:
        _assert_safe_email(subject, html)
    except ValueError as exc:
        logger.error("Email rejected by safety validation: %s", exc)
        return None

    from_name = os.environ.get("EMAIL_FROM_NAME", "").strip()
    if not from_name:
        logger.error("Email delivery is not configured: EMAIL_FROM_NAME is missing")
        return None

    base_url = os.environ.get("INTEGRATION_PROXY_URL", "").strip().rstrip("/")
    email_key = os.environ.get("EMERGENT_EMAIL_KEY", "").strip()
    if _configured(base_url) and _configured(email_key):
        payload = {"to": [to], "subject": subject, "html": html, "from_name": from_name}
        if os.environ.get("EMAIL_REPLY_TO"):
            payload["contact_email"] = os.environ["EMAIL_REPLY_TO"]
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(f"{base_url}/api/v1/email/send",
                                         headers={"X-Email-Key": email_key}, json=payload)
            resp.raise_for_status()
            try:
                response_data = resp.json()
            except ValueError:
                response_data = {}
            return response_data.get("id") or response_data.get("message_id") or "accepted"
        except httpx.HTTPStatusError as exc:
            try:
                code = exc.response.json().get("code", "unknown")
            except (ValueError, AttributeError):
                code = "unknown"
            logger.error("Email provider rejected delivery (HTTP %s, code %s)", exc.response.status_code, code)
            return None
        except httpx.RequestError as exc:
            logger.error("Email provider connection failed (%s)", type(exc).__name__)
            return None
        except Exception as exc:
            logger.error("Email provider delivery failed (%s)", type(exc).__name__)
            return None

    smtp_host = os.environ.get("SMTP_HOST", "").strip()
    smtp_username = os.environ.get("SMTP_USERNAME", "").strip()
    smtp_password = os.environ.get("SMTP_PASSWORD", "")
    smtp_from = os.environ.get("SMTP_FROM_EMAIL", "").strip()
    try:
        smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    except ValueError:
        logger.error("Email delivery is not configured: SMTP_PORT must be an integer")
        return None
    if not all(_configured(value) for value in (smtp_host, smtp_username, smtp_password, smtp_from)):
        logger.error("Email delivery is not configured: provide valid integration settings or SMTP credentials")
        return None

    try:
        receipt = await asyncio.to_thread(
            _send_smtp, to, subject, html, from_name, smtp_host, smtp_port,
            smtp_username, smtp_password, smtp_from, os.environ.get("EMAIL_REPLY_TO", "").strip(),
        )
        return receipt
    except smtplib.SMTPAuthenticationError as exc:
        logger.error("Brevo SMTP authentication rejected the configured credentials (SMTP %s)", exc.smtp_code)
        return None
    except smtplib.SMTPRecipientsRefused as exc:
        codes = sorted({str(item[0]) for item in exc.recipients.values()})
        logger.error("Brevo SMTP refused the recipient (SMTP codes %s)", ",".join(codes) or "unknown")
        return None
    except smtplib.SMTPResponseException as exc:
        logger.error("Brevo SMTP rejected the message (SMTP %s, %s)", exc.smtp_code, type(exc).__name__)
        return None
    except (socket.gaierror, ConnectionRefusedError, TimeoutError, socket.timeout, ssl.SSLError) as exc:
        logger.error("Brevo SMTP connection failed (%s)", type(exc).__name__)
        return None
    except Exception as exc:
        logger.error("SMTP delivery failed (%s)", type(exc).__name__)
        return None


def _send_smtp(to: str, subject: str, html: str, from_name: str, host: str, port: int,
               username: str, password: str, from_address: str, reply_to: str) -> str:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = formataddr((from_name, from_address))
    message["To"] = to
    message["Message-ID"] = make_msgid()
    if reply_to:
        message["Reply-To"] = reply_to
    message.set_content("This message contains an HTML email. Please view it in an HTML-compatible mail client.")
    message.add_alternative(html, subtype="html")

    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=30, context=ssl.create_default_context()) as server:
            server.login(username, password)
            refused = server.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.ehlo()
            server.starttls(context=ssl.create_default_context())
            server.ehlo()
            server.login(username, password)
            refused = server.send_message(message)
    if refused:
        raise smtplib.SMTPRecipientsRefused(refused)
    return message["Message-ID"]


def _wrap(title: str, lines: list, action=None) -> str:
    brand = escape(os.environ["EMAIL_FROM_NAME"])
    body = "".join(f'<p style="margin:0 0 14px;font-size:15px;line-height:1.6;color:#d8d8de">{l}</p>' for l in lines)
    button = ""
    if action:
        label, url = action
        button = (f'<p style="margin:24px 0"><a href="{escape(url, quote=True)}" '
                  'style="display:inline-block;padding:12px 20px;border-radius:999px;background:#ff2d95;'
                  f'color:#fff;text-decoration:none;font-weight:bold">{escape(label)}</a></p>')
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#0a0a0a">'
        '<tr><td align="center" style="padding:32px 16px">'
        '<table role="presentation" width="560" cellpadding="0" cellspacing="0" style="max-width:560px;background:#141418;border:1px solid #2a2a33;border-radius:18px">'
        '<tr><td style="padding:32px;font-family:Arial,Helvetica,sans-serif">'
        f'<p style="margin:0 0 6px;font-size:26px;font-weight:900;letter-spacing:1px;color:#ffffff">SANKALP<span style="color:#ff2d95">\'26</span></p>'
        '<p style="margin:0 0 24px;height:4px;width:120px;background:#007ba7;border-right:60px solid #ff2d95"></p>'
        f'<p style="margin:0 0 18px;font-size:20px;font-weight:bold;color:#ffffff">{escape(title)}</p>'
        f'{body}{button}'
        f'<p style="margin:24px 0 0;font-size:12px;color:#77778a">Sent by {brand} · IEEE AJIET Student Branch, Mangaluru. '
        'We never ask for your password by email. Questions: <a href="mailto:hackathon@ajiet.edu.in" style="color:#00c8ff">hackathon@ajiet.edu.in</a></p>'
        '</td></tr></table></td></tr></table>'
    )


def invitation_email(name: str, team_name: str, activation_url: str, expires_hours: int = 72):
    html = _wrap("Activate your SANKALP'26 account", [
        f"Hi {escape(name)},",
        f"You have been invited to join team <strong>{escape(team_name)}</strong> for SANKALP'26.",
        f"This private activation link expires in {expires_hours} hours and can be used once. Create your own password after opening it.",
        "If you were not expecting this invitation, you can safely ignore this message.",
    ], ("Activate my account", activation_url))
    return f"Activate your SANKALP'26 account — {team_name}", html


def verification_email(name: str, verification_url: str):
    html = _wrap("Verify your email", [
        f"Hi {escape(name)},",
        "Verify your email address to activate your SANKALP'26 team-leader account.",
        "This private link expires in 24 hours and can be used once.",
    ], ("Verify my email", verification_url))
    return "Verify your SANKALP'26 email", html


def password_reset_email(name: str, reset_url: str):
    html = _wrap("Reset your password", [
        f"Hi {escape(name)},",
        "A password reset was requested for your SANKALP'26 account.",
        "This private link expires in one hour and can be used once. If you did not request it, ignore this email.",
    ], ("Choose a new password", reset_url))
    return "Reset your SANKALP'26 password", html


def judge_invitation_email(name: str, activation_url: str):
    html = _wrap("Activate your judge account", [
        f"Hi {escape(name)},",
        "An administrator invited you to the SANKALP'26 judging portal.",
        "Use this single-use link within 72 hours to create your own password. Team access is assigned separately by an administrator.",
    ], ("Activate judge account", activation_url))
    return "Activate your SANKALP'26 judge account", html


def status_email(name: str, title: str, message: str, dashboard_url: str = None):
    action = ("Open participant dashboard", dashboard_url) if dashboard_url else None
    html = _wrap(title, [f"Hi {escape(name)},", escape(message)], action)
    return f"SANKALP'26 — {title}", html


def shortlist_email(team: dict, dashboard_url: str = None):
    lead, tname = escape(team["name"]), escape(team.get("team_name") or "")
    track = escape(team.get("track") or "")
    html = _wrap("Your team has been shortlisted", [
        f"Hi {lead},",
        f"Great news — team <strong style=\"color:#ff2d95\">{tname}</strong> has been shortlisted for SANKALP'26, the national level 24-hour hackathon.",
        f"Challenge: <strong>{track}</strong>",
        "Payment is the next step. Sign in to your dashboard to view the organizer-configured amount, deadline and payment instructions.",
        "See you on 27 &amp; 28 November at A J Institute of Engineering and Technology, Mangaluru.",
    ], ("View payment instructions", dashboard_url) if dashboard_url else None)
    return f"You're shortlisted for SANKALP'26 — {team.get('team_name')}", html


def results_email(team: dict, rank, total: int, score):
    lead, tname = escape(team["name"]), escape(team.get("team_name") or "")
    line = (f"Team <strong style=\"color:#ff2d95\">{tname}</strong> finished <strong>#{rank}</strong> of {total} with an average judge score of <strong>{score}/40</strong>."
            if rank else f"Team <strong>{tname}</strong> did not have a scored submission this time.")
    html = _wrap("SANKALP'26 results are live", [
        f"Hi {lead},",
        "The judges have finished and the final results of SANKALP'26 are now published.",
        line,
        "Sign in to the SANKALP'26 portal to see the full leaderboard. Thank you for building with us — Build. Breakthrough. Belong.",
    ])
    return "SANKALP'26 results are published", html
