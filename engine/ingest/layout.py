"""
layout.py - word boxes -> reading-ordered rows with column boundaries.

Ported from the ITR Extractor sibling project unchanged: bank statement tables
have the same "plain text extraction destroys column alignment" problem as
T-account financial statements - a wrapped narration or a tight column gap
makes PyMuPDF's page.get_text() (or Tesseract's image_to_string) weld one
column's text onto the next row's. Both the digital path (PyMuPDF word boxes)
and the scanned path (Tesseract word boxes, added in Phase 3) feed the same
reconstruction here: cluster words into visual rows by y-centre, order each
row left to right, and insert a TAB wherever a horizontal gap is wide enough
to be a column boundary rather than a word space.
"""

import statistics

# A gap this fraction of the page width or wider is a column boundary, not a
# word space.
_COL_GAP_FRAC = 0.035

# Row band tolerance as a fraction of the median word height.
_ROW_TOL_FRAC = 0.6

COL_SEP = "\t"


def rows_with_cells(words, page_width: float) -> list:
    """
    `words` is an iterable of (x0, y0, x1, y1, text). Returns
    [(row_y, [(x0, x1, cell_text), ...]), ...] ordered top to bottom, cells left
    to right, where a cell is a run of words with no column-width gap inside it.
    """
    words = [w for w in words if str(w[4]).strip()]
    if not words:
        return []

    heights = [w[3] - w[1] for w in words if w[3] > w[1]]
    med_h   = statistics.median(heights) if heights else 12
    tol     = (med_h or 12) * _ROW_TOL_FRAC
    gap_min = page_width * _COL_GAP_FRAC

    words.sort(key=lambda w: (w[1], w[0]))

    # rows: [running_mean_y, count, [(x0, x1, text), ...]]
    rows = []
    for x0, y0, x1, _y1, txt in words:
        for row in rows:
            if abs(y0 - row[0]) <= tol:
                row[0] = (row[0] * row[1] + y0) / (row[1] + 1)
                row[1] += 1
                row[2].append((x0, x1, str(txt).strip()))
                break
        else:
            rows.append([y0, 1, [(x0, x1, str(txt).strip())]])

    rows.sort(key=lambda r: r[0])

    out = []
    for mean_y, _n, items in rows:
        items.sort(key=lambda it: it[0])
        cells, cur_x0, cur_x1, parts, prev_end = [], None, None, [], None
        for x0, x1, txt in items:
            if prev_end is not None and (x0 - prev_end) >= gap_min:
                cells.append((cur_x0, cur_x1, " ".join(parts)))
                parts, cur_x0 = [], None
            if cur_x0 is None:
                cur_x0 = x0
            cur_x1 = x1
            parts.append(txt)
            prev_end = x1
        if parts:
            cells.append((cur_x0, cur_x1, " ".join(parts)))
        out.append((mean_y, cells))
    return out


def rows_from_words(words, page_width: float) -> list:
    """[(row_y, row_text), ...] with COL_SEP marking column boundaries."""
    return [(y, COL_SEP.join(t for _a, _b, t in cells))
            for y, cells in rows_with_cells(words, page_width)]


def split_columns(row_text: str) -> list:
    """Row text -> its column cells, empty cells dropped."""
    return [c.strip() for c in row_text.split(COL_SEP) if c.strip()]


def words_from_page(page) -> list:
    """PyMuPDF page -> (x0, y0, x1, y1, text) tuples. Digital-PDF path."""
    return [(w[0], w[1], w[2], w[3], w[4]) for w in page.get_text("words")]


def words_from_tesseract(data: dict, min_conf: float = 30) -> list:
    """pytesseract image_to_data DICT -> (x0, y0, x1, y1, text) tuples."""
    words = []
    for i in range(len(data["text"])):
        txt = data["text"][i].strip()
        if not txt:
            continue
        try:
            conf = float(data["conf"][i])
        except (ValueError, TypeError):
            conf = -1
        if conf < min_conf:
            continue
        x, y = data["left"][i], data["top"][i]
        words.append((x, y, x + data["width"][i], y + data["height"][i], txt))
    return words
