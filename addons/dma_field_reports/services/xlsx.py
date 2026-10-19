"""Read a field-data workbook by header text, not by column letter. Pure Python + openpyxl.

A template may use one header row (Survey123) or two (the DMA operator
templates: a group header such as "Location *" over sub-headers such as
"Province", "District"). Each column gets a header path "group / sub".
"""
import datetime
import io

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

from . import text

MAX_EMPTY_RUN = 50  # stop after this many empty rows (templates are formatted down to row 15,000)


class Column:
    __slots__ = ("index", "letter", "group", "sub", "path", "keys")

    def __init__(self, index, group, sub):
        self.index = index
        self.letter = get_column_letter(index + 1)
        self.group = text.clean(group)
        self.sub = text.clean(sub)
        if self.group and self.sub:
            self.path = f"{self.group} / {self.sub}"
        else:
            self.path = self.group or self.sub
        self.keys = {text.norm(self.path)}
        if self.sub:
            self.keys.add(text.norm(self.sub))
        if self.group and not self.sub:
            self.keys.add(text.norm(self.group))
        self.keys.discard("")

    def __repr__(self):
        return f"<Column {self.letter} {self.path!r}>"


class Sheet:
    """Columns and data rows of one worksheet."""

    def __init__(self, name, columns, rows):
        self.name = name
        self.columns = columns  # [Column]
        self.rows = rows  # [(excel_row_number, [cell values])]

    def find(self, header_aliases):
        """Columns matching any alias, best first: exact path match, then sub-header, then group-only.

        An alias may be 'Group / Sub' or just 'Sub'. Matching ignores case,
        punctuation, '*' and '#' marks, and Arabic spelling variants.
        """
        wanted = [text.norm(a) for a in header_aliases if text.norm(a)]
        exact, loose = [], []
        for col in self.columns:
            if text.norm(col.path) in wanted:
                exact.append(col)
            elif col.keys & set(wanted):
                loose.append(col)
        return exact + loose


def _value(v):
    if isinstance(v, datetime.datetime) and v.time() == datetime.time(0, 0):
        return v.date()
    if isinstance(v, str):
        v = v.strip()
        return v or None
    return v


def read_sheet(data, sheet_name, header_row, header_rows=1, first_data_row=None):
    """Read `sheet_name` from workbook bytes.

    header_row: 1-based row of the first header row. header_rows: 1 or 2.
    first_data_row: defaults to the row after the headers.
    Raises KeyError if the sheet is missing (message lists the sheets found).
    """
    wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    try:
        lookup = {text.norm(n): n for n in wb.sheetnames}
        real = sheet_name if sheet_name in wb.sheetnames else lookup.get(text.norm(sheet_name))
        if not real:
            raise KeyError(f"Sheet '{sheet_name}' not found. The file has: {', '.join(wb.sheetnames)}")
        ws = wb[real]
        first_data_row = first_data_row or header_row + header_rows
        head = [list(r) for r in ws.iter_rows(min_row=header_row, max_row=header_row + header_rows - 1, values_only=True)]
        width = max((len(r) for r in head), default=0)
        top = [(head[0][i] if i < len(head[0]) else None) for i in range(width)]
        sub = [(head[1][i] if header_rows > 1 and i < len(head[1]) else None) for i in range(width)]
        columns, group = [], None
        for i in range(width):
            t, s = text.clean(top[i]), text.clean(sub[i])
            if t:
                # a group header spans the next columns only if it has a sub-header itself
                # ("Location *" over "Province"), not when it is a plain one-column header
                group = t if s else None
            elif s and group:
                t = group  # merged group header continues over its sub-headers
            else:
                group = None
            if t or s:
                columns.append(Column(i, t, s))
        rows, empty_run = [], 0
        for number, values in enumerate(ws.iter_rows(min_row=first_data_row, values_only=True), start=first_data_row):
            values = [_value(v) for v in values[:width]]
            if not any(v not in (None, "") for v in values):
                empty_run += 1
                if empty_run >= MAX_EMPTY_RUN:
                    break
                continue
            empty_run = 0
            rows.append((number, values))
        return Sheet(real, columns, rows)
    finally:
        wb.close()


def sheet_names(data):
    wb = load_workbook(io.BytesIO(data), read_only=True)
    try:
        return list(wb.sheetnames)
    finally:
        wb.close()
