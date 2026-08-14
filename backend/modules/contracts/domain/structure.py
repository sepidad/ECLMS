"""Structured contract articles, sub-articles, and notes.

Numbers are deliberately derived from list order.  Stored nodes never carry a
hard-coded article number, so inserting a node automatically renumbers the
following siblings when the version is rendered.
"""

from __future__ import annotations

from typing import Any


def _node(node: dict[str, Any]) -> dict[str, Any]:
  return {
    'id': str(node.get('id') or ''),
    'title': str(node.get('title') or '').strip(),
    'body': str(node.get('body') or '').strip(),
    'children': [_node(child) for child in (node.get('children') or []) if isinstance(child, dict)],
    'notes': [str(note).strip() for note in (node.get('notes') or []) if str(note).strip()],
  }


def normalize_structure(value: Any) -> list[dict[str, Any]]:
  if not isinstance(value, list):
    return []
  return [_node(item) for item in value if isinstance(item, dict)]


def _renumber(nodes: list[dict[str, Any]], prefix: str = '') -> tuple[list[dict[str, Any]], int, int]:
  articles = 0
  notes = 0
  result: list[dict[str, Any]] = []
  for index, node in enumerate(nodes, start=1):
    number = f'{prefix}-{index}' if prefix else str(index)
    children, child_articles, child_notes = _renumber(node['children'], number)
    item = {**node, 'number': number, 'children': children}
    item['notes'] = [f'Note {n}: {text}' for n, text in enumerate(node['notes'], start=1)]
    result.append(item)
    articles += 1 + child_articles
    notes += len(node['notes']) + child_notes
  return result, articles, notes


def numbered_structure(value: Any) -> tuple[list[dict[str, Any]], int, int]:
  return _renumber(normalize_structure(value))


def render_structure(value: Any) -> str:
  numbered, _, _ = numbered_structure(value)
  lines: list[str] = []

  def visit(nodes: list[dict[str, Any]], depth: int = 0) -> None:
    for node in nodes:
      lines.append(f"Article {node['number']} - {node['title']}" if depth == 0 else f"{node['number']} {node['title']}")
      if node['body']:
        lines.append(node['body'])
      lines.extend(node['notes'])
      visit(node['children'], depth + 1)

  visit(numbered)
  return '\n\n'.join(lines)
