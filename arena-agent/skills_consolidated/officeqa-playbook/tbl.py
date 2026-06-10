#!/usr/bin/env python3
"""Treasury Bulletin table extractor (stdlib only).

Usage:
  python3 tbl.py FILE TITLE_REGEX            # show table: unit line, numbered columns, row labels
  python3 tbl.py FILE TITLE_REGEX ROW_REGEX  # also dump matching rows, one "col -> cleaned value" per line

Finds the first table whose preceding ~6 lines match TITLE_REGEX (case-insensitive),
prints the title/unit context, the header with column indices, and for each row
matching ROW_REGEX prints every cell as:  [i] <full column header> = <raw> -> <number|None>
Cleaning: strips commas and footnote markers (1/, 2/, r, p, *, est), '(x)' -> -x,
'-'/'n.a.'/'--' -> None, '*' alone -> 0 (means < 0.5 of unit).
"""
import re
import sys


def clean(cell):
    s = cell.strip()
    if s in ("", "-", "--", "---", "n.a.", "n.a", "nan", "N.A."):
        return None
    if s == "*" or s == "-*":
        return 0.0
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg, s = True, s[1:-1]
    # drop trailing footnote markers: "6,001 1/", "916 9/11", "3,471,122r", "64570 p"
    s = re.sub(r"(\s*\d{1,2}/(\d{1,2})?)+\s*$", "", s)
    s = re.sub(r"\s*[rpe]\.?\s*$", "", s, flags=re.I)
    s = re.sub(r"\s*\((est|prelim)\.?\)\s*$", "", s, flags=re.I)
    s = s.replace(",", "").replace("$", "").strip().rstrip(".")
    if s.startswith("-") and s.count("-") == 1 and s[1:].replace(".", "").isdigit():
        neg, s = True, s[1:]
    try:
        v = float(s)
        return -v if neg else v
    except ValueError:
        pass
    # fall back: leading number followed by footnote-like junk ("916 9/11", "129 2/")
    m = re.match(r"^(-?\d+(?:\.\d+)?)[\s\d/a-z.]*$", s, re.I)
    if m:
        v = float(m.group(1))
        return -v if neg else v
    return None


def find_tables(lines, title_re):
    """Yield (title_context, unit, header_cells, rows) for tables whose context matches."""
    i = 0
    while i < len(lines):
        if lines[i].lstrip().startswith("|"):
            start = i
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                i += 1
            block = lines[start:i]
            ctx = [l.strip() for l in lines[max(0, start - 8):start] if l.strip()]
            ctx_txt = " | ".join(ctx[-6:])
            if re.search(title_re, ctx_txt, re.I):
                unit = next((c for c in reversed(ctx) if re.search(r"\(in .*dollars\)|\(in (thousand|million|billion)", c, re.I)), "")
                header = [h.strip() for h in block[0].strip().strip("|").split("|")]
                rows = []
                for ln in block[1:]:
                    cells = [c.strip() for c in ln.strip().strip("|").split("|")]
                    if cells and set("".join(cells)) <= set("- :"):
                        continue
                    rows.append(cells)
                yield ctx_txt, unit, header, rows
        else:
            i += 1


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    path, title_re = sys.argv[1], sys.argv[2]
    row_re = sys.argv[3] if len(sys.argv) > 3 else None
    lines = open(path, errors="replace").read().splitlines()
    n = 0
    for ctx, unit, header, rows in find_tables(lines, title_re):
        n += 1
        print(f"### TABLE {n} context: {ctx[:300]}")
        print(f"### UNIT: {unit or 'NOT FOUND - check title/footnotes yourself'}")
        for j, h in enumerate(header):
            print(f"  col[{j}] {h}")
        print(f"### {len(rows)} rows; labels:", "; ".join(r[0][:40] for r in rows[:40]))
        if row_re:
            for r in rows:
                if re.search(row_re, r[0], re.I):
                    print(f"--- ROW '{r[0]}'")
                    vals = []
                    for j, c in enumerate(r[1:], 1):
                        v = clean(c)
                        vals.append(v)
                        h = header[j] if j < len(header) else f"?{j}"
                        print(f"  [{j}] {h[:70]} = {c!r} -> {v}")
                    nums = [v for v in vals if v is not None]
                    if len(nums) >= 3 and nums[-1] is not None:
                        body, tot = nums[:-1], nums[-1]
                        if abs(sum(body) - tot) <= max(2.0, 0.005 * abs(tot)):
                            print(f"  CHECK: sum(cols[1..{len(nums)-1}]) = {sum(body):.2f} == last col {tot} (components-total identity HOLDS)")
        if n >= 4:
            break
    if n == 0:
        print("NO TABLE matched. Try a looser TITLE_REGEX, or grep the file's first 80 lines (table of contents).")


if __name__ == "__main__":
    main()
