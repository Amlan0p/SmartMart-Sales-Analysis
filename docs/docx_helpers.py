"""
docx_helpers.py

Formatting helpers for the SmartMart project documentation (python-docx).
Keeps all typography / layout decisions in one place so the content modules
only describe *what* to say.

Requires: pip install python-docx
"""

from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Emu, Pt, RGBColor

# Brand palette sampled from the Cronus Consultants logo
BLUE = RGBColor(0x36, 0x69, 0xAB)
NAVY = RGBColor(0x1B, 0x3A, 0x5C)
GREEN = RGBColor(0x4E, 0x8A, 0x34)       # darker shade of logo green for text contrast
GREY = RGBColor(0x5F, 0x6B, 0x7A)
BLUE_HEX, GREEN_HEX, LIGHT_BLUE_HEX, LIGHT_GREY_HEX, CODE_BG_HEX = "3669AB", "69A147", "EAF1F8", "F3F5F8", "F6F8FA"

MAX_CODE_LINES = 12
BODY_FONT = "Carlito"        # metric-compatible with Calibri; Word falls back to Calibri
CODE_FONT = "Courier New"
PAGE_WIDTH_CM = 21.0
MARGIN_CM = 2.0
TEXT_WIDTH_CM = PAGE_WIDTH_CM - 2 * MARGIN_CM   # 16.6 cm


# --------------------------------------------------------------------------
# Low-level XML helpers
# --------------------------------------------------------------------------
def _set_cell_shading(cell, hex_fill: str) -> None:
    properties = cell._tc.get_or_add_tcPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:val"), "clear")
    shading.set(qn("w:color"), "auto")
    shading.set(qn("w:fill"), hex_fill)
    properties.append(shading)


def _set_cell_borders(cell, color: str = "D0D7DE", size: int = 4, sides=("top", "left", "bottom", "right")) -> None:
    properties = cell._tc.get_or_add_tcPr()
    borders = OxmlElement("w:tcBorders")
    for side in sides:
        element = OxmlElement(f"w:{side}")
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), str(size))
        element.set(qn("w:color"), color)
        borders.append(element)
    properties.append(borders)


def _set_cell_margins(cell, top=60, bottom=60, left=100, right=100) -> None:
    properties = cell._tc.get_or_add_tcPr()
    margins = OxmlElement("w:tcMar")
    for name, value in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        node = OxmlElement(f"w:{name}")
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")
        margins.append(node)
    properties.append(margins)


def _fix_table_widths(table, widths_cm: list[float]) -> None:
    """Apply widths to the table grid AND every cell, with a fixed layout, so
    Word and LibreOffice both honour them."""
    table.autofit = False
    properties = table._tbl.tblPr
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    properties.append(layout)
    for index, width in enumerate(widths_cm):
        table.columns[index].width = Cm(width)
        for cell in table.columns[index].cells:
            cell.width = Cm(width)


def _keep_table_together(table) -> None:
    """Keep all rows on one page (keep-with-next on every row but the last)."""
    # Only short tables stay whole; longer ones split across pages (header row repeats).
    rows = table.rows[:-1] if len(table.rows) <= 9 else table.rows[:2]
    for row in rows:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.keep_with_next = True


def _keep_row_together(row) -> None:
    properties = row._tr.get_or_add_trPr()
    node = OxmlElement("w:cantSplit")
    properties.append(node)


def _repeat_header_row(row) -> None:
    properties = row._tr.get_or_add_trPr()
    node = OxmlElement("w:tblHeader")
    properties.append(node)


def _paragraph_border(paragraph, side: str, color: str, size: int = 8, space: int = 4) -> None:
    properties = paragraph._p.get_or_add_pPr()
    borders = properties.find(qn("w:pBdr"))
    if borders is None:
        borders = OxmlElement("w:pBdr")
        properties.append(borders)
    element = OxmlElement(f"w:{side}")
    element.set(qn("w:val"), "single")
    element.set(qn("w:sz"), str(size))
    element.set(qn("w:space"), str(space))
    element.set(qn("w:color"), color)
    borders.append(element)


def _add_field(paragraph, instruction: str, placeholder: str = "1") -> None:
    """Insert a complex field (PAGE, NUMPAGES ...) with a cached result."""
    def run_with(child):
        run = paragraph.add_run()
        run._r.append(child)
        return run

    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = f" {instruction} "
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run_with(begin)
    run_with(instr)
    run_with(separate)
    paragraph.add_run(placeholder)
    run_with(end)


def _style_font(style, name: str, size: float, bold=False, italic=False, color: RGBColor | None = None) -> None:
    style.font.name = name
    style.font.size = Pt(size)
    style.font.bold = bold
    style.font.italic = italic
    if color is not None:
        style.font.color.rgb = color
    rpr = style.element.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.append(fonts)
    for attribute in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        fonts.set(qn(attribute), name)


# --------------------------------------------------------------------------
# Document set-up
# --------------------------------------------------------------------------
def new_document(logo_path: Path, project_title: str, footer_left: str) -> Document:
    """Create an A4 document with styles, branded header (logo top-left on
    EVERY page, including the cover) and a footer with page numbers."""
    document = Document()
    section = document.sections[0]
    section.orientation = WD_ORIENT.PORTRAIT
    section.page_width, section.page_height = Cm(21.0), Cm(29.7)
    section.left_margin = section.right_margin = Cm(MARGIN_CM)
    section.top_margin, section.bottom_margin = Cm(2.7), Cm(2.1)
    section.header_distance, section.footer_distance = Cm(0.9), Cm(1.0)

    styles = document.styles
    normal = styles["Normal"]
    _style_font(normal, BODY_FONT, 10.5)
    normal.paragraph_format.space_after = Pt(5)
    normal.paragraph_format.line_spacing = 1.08

    heading1 = styles["Heading 1"]
    _style_font(heading1, BODY_FONT, 19, bold=True, color=BLUE)
    heading1.paragraph_format.space_before = Pt(16)
    heading1.paragraph_format.space_after = Pt(8)
    heading1.paragraph_format.keep_with_next = True
    heading1.paragraph_format.page_break_before = False

    heading2 = styles["Heading 2"]
    _style_font(heading2, BODY_FONT, 13.5, bold=True, color=GREEN)
    heading2.paragraph_format.space_before = Pt(9)
    heading2.paragraph_format.space_after = Pt(4)
    heading2.paragraph_format.keep_with_next = True

    heading3 = styles["Heading 3"]
    _style_font(heading3, BODY_FONT, 11.5, bold=True, color=NAVY)
    heading3.paragraph_format.space_before = Pt(7)
    heading3.paragraph_format.space_after = Pt(3)
    heading3.paragraph_format.keep_with_next = True

    for name in ("List Bullet", "List Number"):
        _style_font(styles[name], BODY_FONT, 10.5)
        styles[name].paragraph_format.space_after = Pt(2)

    _build_header(section, logo_path, project_title)
    _build_footer(section, footer_left)
    return document


def _build_header(section, logo_path: Path, project_title: str) -> None:
    header = section.header
    header.is_linked_to_previous = False
    paragraph = header.paragraphs[0]
    paragraph.style = "Normal"
    paragraph.paragraph_format.tab_stops.add_tab_stop(Cm(TEXT_WIDTH_CM), WD_TAB_ALIGNMENT.RIGHT)
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.add_run().add_picture(str(logo_path), width=Cm(3.6))
    run = paragraph.add_run("\t" + project_title)
    run.font.size = Pt(9.5)
    run.font.color.rgb = GREY
    run.font.name = BODY_FONT
    _paragraph_border(paragraph, "bottom", GREEN_HEX, size=10, space=6)


def _build_footer(section, footer_left: str) -> None:
    footer = section.footer
    footer.is_linked_to_previous = False
    paragraph = footer.paragraphs[0]
    paragraph.style = "Normal"
    paragraph.paragraph_format.tab_stops.add_tab_stop(Cm(TEXT_WIDTH_CM), WD_TAB_ALIGNMENT.RIGHT)
    paragraph.paragraph_format.space_after = Pt(0)
    _paragraph_border(paragraph, "top", BLUE_HEX, size=6, space=6)
    left = paragraph.add_run(footer_left + "\tPage ")
    left.font.size = Pt(9)
    left.font.color.rgb = GREY
    _add_field(paragraph, "PAGE")
    mid = paragraph.add_run(" of ")
    mid.font.size = Pt(9)
    mid.font.color.rgb = GREY
    _add_field(paragraph, "NUMPAGES")
    for run in paragraph.runs:
        run.font.size = Pt(9)
        run.font.color.rgb = GREY



SKIP_HEADINGS: set[str] = set()      # compact edition: sections dropped from the report (see build_documentation.py)
_SKIPPING = [False]


class _Nothing:
    """Stand-in returned for a skipped heading so callers can still set attributes on it."""
    def __setattr__(self, name, value):
        pass

    def __getattr__(self, name):
        return self


def _skippable(function):
    def wrapper(*args, **kwargs):
        if _SKIPPING[0]:
            return None
        return function(*args, **kwargs)
    wrapper.__name__ = function.__name__
    wrapper.__doc__ = function.__doc__
    return wrapper

# --------------------------------------------------------------------------
# Content helpers
# --------------------------------------------------------------------------
def add_heading(document, text: str, level: int = 1):
    _SKIPPING[0] = text in SKIP_HEADINGS
    if _SKIPPING[0]:
        return _Nothing()
    return document.add_heading(text, level=level)


@_skippable
def add_paragraph(document, text: str = "", bold_prefix: str | None = None, italic=False,
                  align=None, size: float | None = None, color: RGBColor | None = None,
                  space_after: float | None = None, keep_with_next=False):
    paragraph = document.add_paragraph()
    if bold_prefix:
        run = paragraph.add_run(bold_prefix)
        run.bold = True
    _add_inline(paragraph, text, italic=italic, size=size, color=color)
    if align is not None:
        paragraph.alignment = align
    if space_after is not None:
        paragraph.paragraph_format.space_after = Pt(space_after)
    paragraph.paragraph_format.keep_with_next = keep_with_next
    return paragraph


def _add_inline(paragraph, text: str, italic=False, size=None, color=None) -> None:
    """Support **bold** and `code` inline markup."""
    for token in re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", text):
        if not token:
            continue
        if token.startswith("**") and token.endswith("**"):
            run = paragraph.add_run(token[2:-2])
            run.bold = True
        elif token.startswith("`") and token.endswith("`"):
            run = paragraph.add_run(token[1:-1])
            run.font.name = CODE_FONT
            run.font.size = Pt(9.5 if size is None else size - 1)
            rpr = run._r.get_or_add_rPr()
            shading = OxmlElement("w:shd")
            shading.set(qn("w:val"), "clear")
            shading.set(qn("w:color"), "auto")
            shading.set(qn("w:fill"), "EEF2F6")
            rpr.append(shading)
            continue
        else:
            run = paragraph.add_run(token)
        run.italic = italic
        if size is not None:
            run.font.size = Pt(size)
        if color is not None:
            run.font.color.rgb = color


@_skippable
def add_bullets(document, items: list[str], numbered: bool = False) -> None:
    style = "List Number" if numbered else "List Bullet"
    for item in items:
        paragraph = document.add_paragraph(style=style)
        if "::" in item:
            head, tail = item.split("::", 1)
            run = paragraph.add_run(head.strip())
            run.bold = True
            paragraph.add_run(" \u2013 ")
            _add_inline(paragraph, tail.strip())
        else:
            _add_inline(paragraph, item)
    document.paragraphs[-1].paragraph_format.space_after = Pt(8)


@_skippable
def add_table(document, headers: list[str], rows: list[list], col_widths_cm: list[float],
              align: list[str] | None = None, font_size: float = 9, caption: str | None = None,
              zebra: bool = True, bold_last_row: bool = False, row_pad: int = 30):
    """Add a formatted table. ``align`` per column: 'l', 'r' or 'c'."""
    if caption:
        add_caption(document, caption, keep_with_next=True)
    table = document.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    align = align or ["l"] * len(headers)
    mapping = {"l": WD_ALIGN_PARAGRAPH.LEFT, "r": WD_ALIGN_PARAGRAPH.RIGHT, "c": WD_ALIGN_PARAGRAPH.CENTER}

    def fill(cell, text, bold=False, color=None, alignment="l"):
        cell.text = ""
        paragraph = cell.paragraphs[0]
        paragraph.paragraph_format.space_after = Pt(0)
        paragraph.paragraph_format.line_spacing = 1.05
        paragraph.alignment = mapping[alignment]
        run = paragraph.add_run(str(text))
        run.font.size = Pt(font_size)
        run.bold = bold
        if color is not None:
            run.font.color.rgb = color
        _set_cell_margins(cell, top=row_pad, bottom=row_pad)

    header_row = table.rows[0]
    _repeat_header_row(header_row)
    _keep_row_together(header_row)
    for index, header in enumerate(headers):
        cell = header_row.cells[index]
        fill(cell, header, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF), alignment="c" if align[index] != "l" else "l")
        _set_cell_shading(cell, BLUE_HEX)
        _set_cell_borders(cell, color=BLUE_HEX)
    for row_index, values in enumerate(rows):
        row = table.add_row()
        _keep_row_together(row)
        is_last = bold_last_row and row_index == len(rows) - 1
        for index, value in enumerate(values):
            cell = row.cells[index]
            fill(cell, value, bold=is_last, alignment=align[index])
            _set_cell_borders(cell)
            if is_last:
                _set_cell_shading(cell, "DCEBD2")
            elif zebra and row_index % 2 == 1:
                _set_cell_shading(cell, LIGHT_GREY_HEX)
    _fix_table_widths(table, col_widths_cm)
    if len(table.rows) <= 14:
        _keep_table_together(table)
    spacer = document.add_paragraph()
    spacer.paragraph_format.space_after = Pt(4)
    spacer.paragraph_format.line_spacing = 0.6
    return table


@_skippable
def add_caption(document, text: str, keep_with_next: bool = False):
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(4)
    paragraph.paragraph_format.space_after = Pt(6)
    paragraph.paragraph_format.keep_with_next = keep_with_next
    label, _, rest = text.partition(":")
    run = paragraph.add_run(label + ":")
    run.bold = True
    run.font.size = Pt(10)
    run.font.color.rgb = NAVY
    run2 = paragraph.add_run(rest)
    run2.italic = True
    run2.font.size = Pt(10)
    run2.font.color.rgb = GREY
    return paragraph


@_skippable
def add_figure(document, image_path: Path, caption: str, width_cm: float = 14.5, max_height_cm: float = 8.5, compact: bool = True):
    if compact:
        width_cm, max_height_cm = min(width_cm, 12.0), min(max_height_cm, 5.4)
    """Insert a picture centred, with the caption kept on the same page."""
    from PIL import Image

    with Image.open(image_path) as image:
        ratio = image.height / image.width
    width = width_cm
    if width * ratio > max_height_cm:
        width = max_height_cm / ratio
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.keep_with_next = True
    paragraph.paragraph_format.space_after = Pt(2)
    paragraph.add_run().add_picture(str(image_path), width=Cm(width))
    add_caption(document, caption)


@_skippable
def add_code(document, filename: str, code: str, note: str | None = None, font_size: float = 8):
    """Syntax-neutral code block in a single, non-splitting shaded cell with a
    file-name tab above it. ``code`` must be verbatim project source."""
    label = document.add_paragraph()
    label.paragraph_format.keep_with_next = True
    label.paragraph_format.space_after = Pt(2)
    label.paragraph_format.space_before = Pt(4)
    run = label.add_run("\u25B8 " + filename)
    run.bold = True
    run.font.size = Pt(9.5)
    run.font.color.rgb = BLUE
    if note:
        extra = label.add_run("   " + note)
        extra.italic = True
        extra.font.size = Pt(9)
        extra.font.color.rgb = GREY

    table = document.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    cell = table.rows[0].cells[0]
    _fix_table_widths(table, [TEXT_WIDTH_CM])
    _keep_row_together(table.rows[0])
    _set_cell_shading(cell, CODE_BG_HEX)
    _set_cell_borders(cell, color="C9D1D9")
    _set_cell_margins(cell, top=50, bottom=50, left=120, right=120)
    left_bar = OxmlElement("w:left")
    left_bar.set(qn("w:val"), "single")
    left_bar.set(qn("w:sz"), "24")
    left_bar.set(qn("w:color"), BLUE_HEX)
    cell._tc.tcPr.find(qn("w:tcBorders")).replace(cell._tc.tcPr.find(qn("w:tcBorders")).find(qn("w:left")), left_bar)

    lines = code.rstrip("\n").split("\n")
    if len(lines) > MAX_CODE_LINES:                      # compact edition: show the opening of long listings
        lines = lines[:MAX_CODE_LINES] + ["    ... (continues in the source file)"]
    font_size = min(font_size, 7.5)
    cell.text = ""
    first = True
    for line in lines:
        paragraph = cell.paragraphs[0] if first else cell.add_paragraph()
        first = False
        paragraph.paragraph_format.space_after = Pt(0)
        paragraph.paragraph_format.line_spacing = 1.0
        paragraph.paragraph_format.keep_with_next = len(lines) <= 12   # long listings may split across pages
        expanded = line.replace("\t", "    ")
        leading = len(expanded) - len(expanded.lstrip(" "))
        run = paragraph.add_run("\u00A0" * leading + expanded.lstrip(" "))
        run.font.name = CODE_FONT
        run.font.size = Pt(font_size)
        run.font.color.rgb = RGBColor(0x24, 0x29, 0x2F)
        rpr = run._r.get_or_add_rPr()
        fonts = rpr.find(qn("w:rFonts"))
        if fonts is None:
            fonts = OxmlElement("w:rFonts")
            rpr.append(fonts)
        for attribute in ("w:ascii", "w:hAnsi", "w:cs"):
            fonts.set(qn(attribute), CODE_FONT)
    spacer = document.add_paragraph()
    spacer.paragraph_format.space_after = Pt(4)
    spacer.paragraph_format.line_spacing = 0.6


@_skippable
def add_callout(document, title: str, text: str, fill_hex: str = LIGHT_BLUE_HEX, bar_hex: str = BLUE_HEX):
    """Shaded call-out box (single cell) for key notes and warnings."""
    table = document.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    cell = table.rows[0].cells[0]
    _fix_table_widths(table, [TEXT_WIDTH_CM])
    _keep_row_together(table.rows[0])
    _set_cell_shading(cell, fill_hex)
    _set_cell_borders(cell, color=fill_hex)
    _set_cell_margins(cell, top=60, bottom=60, left=140, right=140)
    bar = OxmlElement("w:left")
    bar.set(qn("w:val"), "single")
    bar.set(qn("w:sz"), "30")
    bar.set(qn("w:color"), bar_hex)
    borders = cell._tc.tcPr.find(qn("w:tcBorders"))
    borders.replace(borders.find(qn("w:left")), bar)
    cell.text = ""
    head = cell.paragraphs[0]
    head.paragraph_format.space_after = Pt(2)
    head.paragraph_format.keep_with_next = True
    run = head.add_run(title)
    run.bold = True
    run.font.size = Pt(10)
    run.font.color.rgb = NAVY
    body = cell.add_paragraph()
    body.paragraph_format.space_after = Pt(0)
    _add_inline(body, text, size=10)
    spacer = document.add_paragraph()
    spacer.paragraph_format.space_after = Pt(4)
    spacer.paragraph_format.line_spacing = 0.6


@_skippable
def add_placeholder_box(document, title: str, instructions: str, height_cm: float = 7.0):
    """Clearly-marked empty frame for a Power BI screenshot that does not yet
    exist. Never styled to look like a real screenshot."""
    table = document.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    row = table.rows[0]
    _keep_row_together(row)
    row.height = Cm(height_cm)
    cell = row.cells[0]
    _fix_table_widths(table, [TEXT_WIDTH_CM - 1.0])
    _set_cell_shading(cell, "FFF8E5")
    _set_cell_borders(cell, color="E0A030", size=12)
    cell.text = ""
    from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT

    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    first = cell.paragraphs[0]
    first.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = first.add_run("POWER BI SCREENSHOT PLACEHOLDER")
    run.bold = True
    run.font.size = Pt(11)
    run.font.color.rgb = RGBColor(0x9A, 0x62, 0x00)
    second = cell.add_paragraph()
    second.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = second.add_run(title)
    run.bold = True
    run.font.size = Pt(10.5)
    third = cell.add_paragraph()
    third.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = third.add_run(instructions)
    run.italic = True
    run.font.size = Pt(9.5)
    run.font.color.rgb = GREY
    spacer = document.add_paragraph()
    spacer.paragraph_format.space_after = Pt(2)
    spacer.paragraph_format.line_spacing = 0.6


def add_toc_entries(document, entries: list[tuple[int, str, int | str]], font_size: float = 10.5) -> None:
    """Table-of-contents as a real TOC field whose cached result is filled with
    ``entries`` = [(level, text, page)]. Word can refresh it (right-click >
    Update Field); the PDF shows the cached page numbers measured from the
    rendered layout."""
    first = True
    for position, (level, text, page) in enumerate(entries):
        paragraph = document.add_paragraph()
        paragraph.paragraph_format.tab_stops.add_tab_stop(Cm(TEXT_WIDTH_CM), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
        paragraph.paragraph_format.space_after = Pt(2.5 if level > 1 else 2)
        paragraph.paragraph_format.space_before = Pt(5 if level == 1 else 0)
        paragraph.paragraph_format.line_spacing = 1.0
        paragraph.paragraph_format.left_indent = Cm(0 if level == 1 else 0.7)
        if first:
            begin = OxmlElement("w:fldChar")
            begin.set(qn("w:fldCharType"), "begin")
            instr = OxmlElement("w:instrText")
            instr.set(qn("xml:space"), "preserve")
            instr.text = ' TOC \\o "1-1" \\h \\z \\u '
            separate = OxmlElement("w:fldChar")
            separate.set(qn("w:fldCharType"), "separate")
            for node in (begin, instr, separate):
                run = paragraph.add_run()
                run._r.append(node)
            first = False
        run = paragraph.add_run(f"{text}\t{page}")
        run.font.size = Pt(font_size)
        run.bold = level == 1
        if level == 1:
            run.font.color.rgb = NAVY
        if position == len(entries) - 1:
            end = OxmlElement("w:fldChar")
            end.set(qn("w:fldCharType"), "end")
            last_run = paragraph.add_run()
            last_run._r.append(end)


def add_page_break(document) -> None:
    from docx.enum.text import WD_BREAK

    document.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def add_team_signature_table(document, members: list[tuple[str, Path]], title: str = "Project team") -> None:
    """Cover-page table: one column per team member, a row with the printed name and a row with the handwritten signature."""
    from docx.enum.table import WD_ALIGN_VERTICAL

    caption = document.add_paragraph()
    caption.paragraph_format.space_after = Pt(3)
    caption.paragraph_format.keep_with_next = True
    run = caption.add_run(title)
    run.bold = True
    run.font.size = Pt(10.5)
    run.font.color.rgb = NAVY
    table = document.add_table(rows=2, cols=len(members))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    width = TEXT_WIDTH_CM / len(members)
    for index, (name, image) in enumerate(members):
        name_cell, sign_cell = table.rows[0].cells[index], table.rows[1].cells[index]
        name_cell.text = ""
        paragraph = name_cell.paragraphs[0]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.space_after = Pt(0)
        paragraph.paragraph_format.line_spacing = 1.0
        run = paragraph.add_run(name)
        run.bold = True
        run.font.size = Pt(8.5)
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        _set_cell_shading(name_cell, BLUE_HEX)
        _set_cell_borders(name_cell, color=BLUE_HEX)
        _set_cell_margins(name_cell, top=60, bottom=60, left=40, right=40)
        name_cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        sign_cell.text = ""
        paragraph = sign_cell.paragraphs[0]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.space_after = Pt(0)
        from PIL import Image
        with Image.open(image) as picture:
            ratio = picture.height / picture.width
        picture_width = min(width - 0.6, 1.3 / ratio)
        paragraph.add_run().add_picture(str(image), width=Cm(picture_width))
        _set_cell_borders(sign_cell)
        _set_cell_margins(sign_cell, top=80, bottom=80, left=40, right=40)
        sign_cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    _fix_table_widths(table, [width] * len(members))
    _keep_row_together(table.rows[0])
    _keep_row_together(table.rows[1])
    spacer = document.add_paragraph()
    spacer.paragraph_format.space_after = Pt(2)
    spacer.paragraph_format.line_spacing = 0.6
