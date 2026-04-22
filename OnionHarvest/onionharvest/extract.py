from __future__ import annotations

from html import unescape
from html.parser import HTMLParser
from typing import Any


class _FieldParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_title = False
        self._non_visible_depth = 0
        self.title_parts: list[str] = []
        self.description: str | None = None
        self.links_count = 0
        self.visible_text_parts: list[str] = []

    _NON_VISIBLE_TAGS = {"script", "style", "noscript", "template", "head"}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attr_map = {k.lower(): (v or "") for k, v in attrs}
        if tag in self._NON_VISIBLE_TAGS:
            self._non_visible_depth += 1
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            if attr_map.get("name", "").lower() == "description" and not self.description:
                content = attr_map.get("content", "").strip()
                if content:
                    self.description = content
        elif tag == "a":
            self.links_count += 1

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self._in_title = False
        if tag in self._NON_VISIBLE_TAGS and self._non_visible_depth > 0:
            self._non_visible_depth -= 1

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if not text:
            return
        if self._in_title:
            self.title_parts.append(text)
            self.visible_text_parts.append(text)
            return
        if self._non_visible_depth > 0:
            return
        self.visible_text_parts.append(text)


def extract_structured_fields(html: str) -> dict[str, Any]:
    """Extract a small, predictable set of fields from HTML."""
    parser = _FieldParser()
    parser.feed(html)

    title = " ".join(parser.title_parts).strip() or None
    plain_text = " ".join(parser.visible_text_parts).strip()
    preview = unescape(plain_text)[:280] if plain_text else None

    return {
        "title": title,
        "description": parser.description,
        "links_count": parser.links_count,
        "text_preview": preview,
    }
