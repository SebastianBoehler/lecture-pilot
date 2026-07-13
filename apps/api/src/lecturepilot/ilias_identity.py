from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse


@dataclass(frozen=True)
class IliasIdentity:
    display_name: str | None
    email: str | None


class _InputParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.values: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() != "input":
            return
        values = {key.casefold(): value or "" for key, value in attrs}
        field = (values.get("id") or values.get("name") or "").casefold()
        if field in {"usr_firstname", "usr_lastname", "usr_email"}:
            self.values.setdefault(field, values.get("value", ""))


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() != "a":
            return
        href = next((value for key, value in attrs if key.casefold() == "href"), None)
        if href:
            self.hrefs.append(href)


def parse_ilias_identity_profile(html: str) -> IliasIdentity:
    parser = _InputParser()
    parser.feed(html)
    first_name = _bounded_text(parser.values.get("usr_firstname"), max_length=100)
    last_name = _bounded_text(parser.values.get("usr_lastname"), max_length=100)
    display_name = _bounded_text(" ".join(part for part in (first_name, last_name) if part), 200)
    return IliasIdentity(
        display_name=display_name,
        email=_email(parser.values.get("usr_email")),
    )


def fetch_ilias_identity(ilias_client: Any, *, root_url: str) -> IliasIdentity:
    root = ilias_client.session.get(
        root_url,
        timeout=ilias_client.timeout_seconds,
        allow_redirects=True,
    )
    root.raise_for_status()
    profile_url = _profile_url(root.text, root.url)
    if profile_url is None:
        raise ValueError("Authenticated ILIAS profile link was missing.")
    profile = ilias_client.session.get(
        profile_url,
        timeout=ilias_client.timeout_seconds,
        allow_redirects=True,
    )
    profile.raise_for_status()
    identity = parse_ilias_identity_profile(profile.text)
    if identity.display_name is None and identity.email is None:
        raise ValueError("Authenticated ILIAS identity fields were missing.")
    return identity


def _profile_url(html: str, base_url: str) -> str | None:
    parser = _LinkParser()
    parser.feed(html)
    base = urlparse(base_url)
    for href in parser.hrefs:
        candidate = urljoin(base_url, href)
        parsed = urlparse(candidate)
        if parsed.scheme != "https" or parsed.netloc != base.netloc:
            continue
        query = {
            key.casefold(): [value.casefold() for value in values]
            for key, values in parse_qs(parsed.query).items()
        }
        if query.get("baseclass") not in (["ildashboardgui"], ["ilpersonaldesktopgui"]):
            continue
        if query.get("cmd") == ["jumptoprofile"]:
            return candidate
    return None


def _bounded_text(value: str | None, max_length: int) -> str | None:
    cleaned = " ".join((value or "").split())
    return cleaned if cleaned and len(cleaned) <= max_length else None


def _email(value: str | None) -> str | None:
    cleaned = (value or "").strip().casefold()
    if len(cleaned) > 320 or re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", cleaned) is None:
        return None
    return cleaned
