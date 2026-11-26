"""URL validation with basic SSRF protection.

The bot feeds user-supplied URLs to yt-dlp running on the host, so links
pointing at the bot host itself, loopback or private network ranges must be
rejected before any network request is made.
"""
import ipaddress
from urllib.parse import urlparse


class URLValidationError(ValueError):
    """Raised when a user-supplied URL is not acceptable."""


def _is_private_host(host: str) -> bool:
    host = host.strip("[]").lower()
    if host in {"localhost", "localhost.localdomain"}:
        return True
    if host.endswith(".local") or host.endswith(".internal"):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return not ip.is_global or ip.is_loopback or ip.is_link_local or ip.is_reserved


def validate_url(url: str) -> str:
    """Validate a user-supplied media URL and return it normalized.

    Raises URLValidationError with a user-presentable reason.
    """
    if not url or len(url) > 2048:
        raise URLValidationError("пустая или слишком длинная ссылка")
    if any(ch in url for ch in "\r\n\t"):
        raise URLValidationError("недопустимые символы в ссылке")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise URLValidationError("поддерживаются только http(s)-ссылки")
    if not parsed.hostname:
        raise URLValidationError("в ссылке нет имени хоста")
    if _is_private_host(parsed.hostname):
        raise URLValidationError("ссылки на внутренние адреса запрещены")
    return url
