"""DOCX and PDF representations of a structured contract version."""

from __future__ import annotations

from io import BytesIO
from typing import Any

from backend.modules.contracts.domain.structure import numbered_structure


STYLE_PROFILE = {
  'body_font': 'Aptos',
  'title_font': 'Aptos Display',
  'body_size': 10.5,
  'article_size': 13,
  'sub_article_size': 11,
  'accent': '1F4E79',
  'note_color': '666666',
}


def _active(version_items: list[dict[str, Any]]) -> dict[str, Any]:
  return next((item for item in version_items if item.get('is_active')), version_items[-1] if version_items else {})


def _structure(version: dict[str, Any]) -> list[dict[str, Any]]:
  structure = version.get('structure')
  if structure:
    return structure
  content = (version.get('content') or '').strip()
  return [{'id': 'legacy', 'title': 'Contract content', 'body': content, 'children': [], 'notes': []}] if content else []


def _add_page_field(paragraph) -> None:
  from docx.oxml import OxmlElement
  from docx.oxml.ns import qn
  run = paragraph.add_run()
  begin = OxmlElement('w:fldChar'); begin.set(qn('w:fldCharType'), 'begin')
  instr = OxmlElement('w:instrText'); instr.set(qn('xml:space'), 'preserve'); instr.text = ' PAGE '
  end = OxmlElement('w:fldChar'); end.set(qn('w:fldCharType'), 'end')
  run._r.extend([begin, instr, end])


def build_docx(*, title: str, reference: str, counterparty: str, version: dict[str, Any]) -> bytes:
  from docx import Document
  from docx.enum.section import WD_SECTION
  from docx.enum.text import WD_ALIGN_PARAGRAPH
  from docx.shared import Inches, Pt, RGBColor

  document = Document()
  section = document.sections[0]
  section.top_margin = Inches(0.8); section.bottom_margin = Inches(0.75)
  section.left_margin = Inches(0.9); section.right_margin = Inches(0.9)
  styles = document.styles
  normal = styles['Normal']; normal.font.name = STYLE_PROFILE['body_font']; normal.font.size = Pt(STYLE_PROFILE['body_size'])
  for style_name, size, color in [('Title', 20, STYLE_PROFILE['accent']), ('Heading 1', STYLE_PROFILE['article_size'], STYLE_PROFILE['accent']), ('Heading 2', STYLE_PROFILE['sub_article_size'], STYLE_PROFILE['accent'])]:
    style = styles[style_name]; style.font.name = STYLE_PROFILE['title_font']; style.font.size = Pt(size); style.font.bold = True; style.font.color.rgb = RGBColor.from_string(color)
  styles['List Bullet'].font.name = STYLE_PROFILE['body_font']; styles['List Bullet'].font.size = Pt(STYLE_PROFILE['body_size'])

  header = section.header.paragraphs[0]
  header.text = 'ECLMS | CONTRACT DOCUMENT'
  header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
  header.runs[0].font.name = STYLE_PROFILE['body_font']; header.runs[0].font.size = Pt(8); header.runs[0].font.color.rgb = RGBColor(100, 116, 139)
  footer = section.footer.paragraphs[0]
  footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
  footer.add_run('Page '); _add_page_field(footer)

  heading = document.add_paragraph(style='Title'); heading.alignment = WD_ALIGN_PARAGRAPH.CENTER; heading.add_run(title)
  meta = document.add_paragraph(); meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
  meta.add_run(f'{reference}  |  {counterparty}').italic = True
  document.add_paragraph()

  numbered, _, _ = numbered_structure(_structure(version))
  def visit(nodes: list[dict[str, Any]], depth: int = 0) -> None:
    for node in nodes:
      style = 'Heading 1' if depth == 0 else 'Heading 2'
      p = document.add_paragraph(style=style)
      p.add_run(f"Article {node['number']} - {node['title']}" if depth == 0 else f"{node['number']} {node['title']}")
      if node.get('body'):
        for paragraph in str(node['body']).split('\n'):
          document.add_paragraph(paragraph)
      for note in node.get('notes', []):
        document.add_paragraph(note, style='List Bullet')
      visit(node.get('children', []), depth + 1)
  visit(numbered)
  out = BytesIO(); document.save(out); return out.getvalue()


def build_pdf(*, title: str, reference: str, counterparty: str, version: dict[str, Any]) -> bytes:
  from reportlab.lib import colors
  from reportlab.lib.enums import TA_CENTER, TA_RIGHT
  from reportlab.lib.pagesizes import LETTER
  from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
  from reportlab.lib.units import inch
  from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, PageBreak, Spacer

  out = BytesIO()
  styles = getSampleStyleSheet()
  body = ParagraphStyle('ContractBody', parent=styles['BodyText'], fontName='Helvetica', fontSize=10, leading=14, spaceAfter=7)
  title_style = ParagraphStyle('ContractTitle', parent=styles['Title'], fontName='Helvetica-Bold', fontSize=19, leading=23, alignment=TA_CENTER, textColor=colors.HexColor('#1F4E79'), spaceAfter=8)
  article = ParagraphStyle('Article', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=13, leading=16, textColor=colors.HexColor('#1F4E79'), spaceBefore=10, spaceAfter=5)
  sub = ParagraphStyle('SubArticle', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=colors.HexColor('#1F4E79'), spaceBefore=7, spaceAfter=4)
  note = ParagraphStyle('Note', parent=body, leftIndent=18, bulletIndent=7, textColor=colors.HexColor('#666666'))

  def furniture(canvas, doc):
    canvas.saveState(); canvas.setFont('Helvetica', 8); canvas.setFillColor(colors.HexColor('#64748B'))
    canvas.drawRightString(LETTER[0] - 0.9 * inch, LETTER[1] - 0.48 * inch, 'ECLMS | CONTRACT DOCUMENT')
    canvas.drawCentredString(LETTER[0] / 2, 0.42 * inch, f'Page {doc.page}')
    canvas.restoreState()

  doc = BaseDocTemplate(out, pagesize=LETTER, leftMargin=0.9 * inch, rightMargin=0.9 * inch, topMargin=0.75 * inch, bottomMargin=0.65 * inch)
  doc.addPageTemplates([PageTemplate(id='contract', frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='normal')], onPage=furniture)])
  story = [Paragraph(title, title_style), Paragraph(f'{reference} | {counterparty}', ParagraphStyle('Meta', parent=body, alignment=TA_CENTER, textColor=colors.HexColor('#64748B'))), Spacer(1, 14)]
  numbered, _, _ = numbered_structure(_structure(version))
  def visit(nodes: list[dict[str, Any]], depth: int = 0):
    for node in nodes:
      story.append(Paragraph(f"Article {node['number']} - {node['title']}" if depth == 0 else f"{node['number']} {node['title']}", article if depth == 0 else sub))
      for paragraph in str(node.get('body') or '').split('\n'):
        if paragraph.strip(): story.append(Paragraph(paragraph.replace('&', '&amp;'), body))
      for note_text in node.get('notes', []): story.append(Paragraph(note_text.replace('&', '&amp;'), note, bulletText='•'))
      visit(node.get('children', []), depth + 1)
  visit(numbered); doc.build(story); return out.getvalue()

