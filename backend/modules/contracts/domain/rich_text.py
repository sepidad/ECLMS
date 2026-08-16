"""Small, dependency-free HTML boundary for contract rich text."""

from __future__ import annotations

from html import escape
from html.parser import HTMLParser

_ALLOWED = {'p', 'br', 'strong', 'b', 'em', 'i', 'u', 'ul', 'ol', 'li', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'img', 'div', 'span'}
_VOID = {'br', 'img'}


class _Sanitizer(HTMLParser):
  def __init__(self) -> None:
    super().__init__(convert_charrefs=True)
    self.output: list[str] = []
    self.skip_depth = 0

  def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
    tag = tag.lower()
    if tag in {'script', 'style', 'iframe', 'object', 'embed', 'form'}:
      self.skip_depth += 1
      return
    if self.skip_depth or tag not in _ALLOWED:
      return
    safe_attrs: list[str] = []
    for name, value in attrs:
      name = name.lower()
      value = value or ''
      if name.startswith('on'):
        continue
      if name == 'src' and not value.startswith('data:image/'):
        continue
      if name in {'style', 'dir', 'align', 'src', 'alt'}:
        safe_attrs.append(f' {name}="{escape(value, quote=True)}"')
    self.output.append(f'<{tag}{"".join(safe_attrs)}>')

  def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
    self.handle_starttag(tag, attrs)

  def handle_endtag(self, tag: str) -> None:
    tag = tag.lower()
    if tag in {'script', 'style', 'iframe', 'object', 'embed', 'form'} and self.skip_depth:
      self.skip_depth -= 1
      return
    if not self.skip_depth and tag in _ALLOWED and tag not in _VOID:
      self.output.append(f'</{tag}>')

  def handle_data(self, data: str) -> None:
    if not self.skip_depth:
      self.output.append(escape(data))


def sanitize_rich_text(value: str) -> str:
  parser = _Sanitizer()
  parser.feed(value)
  parser.close()
  return ''.join(parser.output)


class _TextOnly(HTMLParser):
  def __init__(self) -> None:
    super().__init__(convert_charrefs=True)
    self.parts: list[str] = []

  def handle_data(self, data: str) -> None:
    self.parts.append(data)

  def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
    if tag in {'br', 'p', 'div', 'li', 'tr'}:
      self.parts.append('\n')
    if tag == 'td':
      self.parts.append('  ')

  def handle_endtag(self, tag: str) -> None:
    if tag in {'p', 'div', 'li', 'tr'}:
      self.parts.append('\n')


def rich_text_to_plain(value: str) -> str:
  parser = _TextOnly()
  parser.feed(value)
  parser.close()
  return '\n'.join(line.rstrip() for line in ''.join(parser.parts).splitlines()).strip()
