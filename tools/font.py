"""DK4 half-width font: original 6x11 glyphs for ASCII 0x21-0x7E plus advance widths.

The game's half-width font (arm9 0x02125a60) is 11 rows x 6 px, 1 byte per row, MSB = left,
for chars 0x21-0x7E (space and everything else draw blank). We replace it with font6x12's
glyphs minus their blank top row (caps rows 0-8, descenders 9-10, matching the 11x11 kanji),
plus digits/punctuation drawn here (font6x12 took those from the SGS ROM).

Widths include the 1 px gap; glyphs are left-aligned. Digits are fixed-width so numbers line up.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from font6x12 import GLYPHS as BASE, _g, _trim  # noqa: E402

OWN = {
    '0': _g('.##..', '#..#.', '#..#.', '#..#.', '#..#.', '#..#.', '#..#.', '#..#.', '.##..'),
    '1': _g('..#..', '.##..', '..#..', '..#..', '..#..', '..#..', '..#..', '..#..', '.###.'),
    '2': _g('.##..', '#..#.', '...#.', '...#.', '..#..', '.#...', '#....', '#....', '####.'),
    '3': _g('.##..', '#..#.', '...#.', '...#.', '.##..', '...#.', '...#.', '#..#.', '.##..'),
    '4': _g('...#.', '..##.', '.#.#.', '.#.#.', '#..#.', '####.', '...#.', '...#.', '...#.'),
    '5': _g('####.', '#....', '#....', '###..', '...#.', '...#.', '...#.', '#..#.', '.##..'),
    '6': _g('.##..', '#..#.', '#....', '#....', '###..', '#..#.', '#..#.', '#..#.', '.##..'),
    '7': _g('####.', '...#.', '...#.', '..#..', '..#..', '.#...', '.#...', '.#...', '.#...'),
    '8': _g('.##..', '#..#.', '#..#.', '#..#.', '.##..', '#..#.', '#..#.', '#..#.', '.##..'),
    '9': _g('.##..', '#..#.', '#..#.', '#..#.', '.###.', '...#.', '...#.', '#..#.', '.##..'),
    '-': _g('###..', top=6),
    '+': _g('..#..', '..#..', '#####', '..#..', '..#..', top=4),
    '/': _g('....#', '....#', '...#.', '...#.', '..#..', '.#...', '.#...', '#....', '#....'),
    '(': _g('..#..', '.#...', '.#...', '#....', '#....', '#....', '.#...', '.#...', '..#..'),
    ')': _g('#....', '.#...', '.#...', '..#..', '..#..', '..#..', '.#...', '.#...', '#....'),
    ',': _g('.#...', '.#...', '#....', top=9),
    '.': _g('#....', top=9),
    ':': _g('#....', '.....', '.....', '.....', '#....', top=5),
}
GLYPHS = {**BASE, **OWN}
FIXED = set('0123456789')
DIGIT_WIDTH = 5
SPACE_WIDTH = 3
ROWS = 11
# control bytes the patched icon subclass draws as 12 px button icons (see patch_arm9.py)
ICON_L, ICON_R = 0x1c, 0x1d
ICON_WIDTH = 13
SPACER = 0x1e                           # control code drawn blank; written <$1E> in tl files


def glyph_rows(ch):
    rows = GLYPHS[ch]
    assert rows[0] == '.....', f'{ch!r}: font6x12 row 0 must be blank'
    return rows[1:1 + ROWS]


def table():
    """(glyph bytes for 0x21-0x7E, 94 x 11 B; width bytes for 0x00-0x7F)"""
    glyphs = bytearray()
    widths = bytearray([6] * 0x80)
    for c in range(0x21, 0x7f):
        ch = chr(c)
        rows = glyph_rows(ch)
        if ch in FIXED:
            w = DIGIT_WIDTH
        else:
            rows, w = _trim(rows)
        for r in rows:
            glyphs.append(int((r + '.')[:6].replace('#', '1').replace('.', '0').ljust(8, '0'), 2))
        widths[c] = w
    widths[0x20] = SPACE_WIDTH
    widths[SPACER] = 1                  # blank 1 px: aligns words with fixed sprite columns
    widths[ICON_L] = widths[ICON_R] = ICON_WIDTH
    assert len(glyphs) == 94 * ROWS
    return bytes(glyphs), bytes(widths)


_W = None


def width(s):
    """Pixel width of a str as the patched engine draws it (non-ASCII = full-width 12)."""
    global _W
    if _W is None:
        _W = table()[1]
    w = _W
    return sum(w[ord(ch)] if ord(ch) < 0x80 else 12 for ch in s)


if __name__ == '__main__':
    g, w = table()
    for c in range(0x21, 0x7f):
        print(repr(chr(c)), w[c])
        for r in range(ROWS):
            print('   ', ''.join('#' if g[(c - 0x21) * ROWS + r] & (0x80 >> k) else '.' for k in range(6)))
