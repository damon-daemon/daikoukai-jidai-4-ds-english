"""FLS animation files (FLS/*.fls, m02_03.fls): parse, rebuild, and the English caption edits.

Layout: u32 anim_off, u32 table_off, u32 count, u32 data_base; table = count x 0x18
(u16 type, u16 w, u16 h, u16 flag, u32 pal_off, u32 pal_size, u32 pix_off, u32 pix_size;
offsets from data_base, each blob 0x80-aligned). type 1 = 8bpp picture, type 0 = 4bpp strip
(LZ10 pixels, stored 256 or 128 px wide, w = shown width; the 32-byte "pal" blob is a parameter
block, kept as is). Pixel values are intensity levels: captions use 1 (fill) / 2 (outline),
the opening name cards 7..15 (outline dark .. body white).

Edits (build time, from the ROM's own pixels, nothing of Koei's art is stored here):
  CAPTIONS  prologue speech captions redrawn with the VWF font
  CARDS     opening typewriter name cards re-typed with the HD spellings: letters are cut from
            the stock frames (each frame adds one letter) and re-composed; missing letters
            are built from parts of others (GLYPH_FIX).
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(__file__))
import lz10  # noqa: E402

ROW = struct.Struct('<4H4I')


class Fls:
    def __init__(self, data):
        self.data = data
        self.anim, self.toff, self.count, self.base = struct.unpack_from('<4I', data)
        self.rows = [list(ROW.unpack_from(data, self.toff + ROW.size * i)) for i in range(self.count)]
        b = self.base
        self.blobs = [(data[b + r[4]:b + r[4] + r[5]], data[b + r[6]:b + r[6] + r[7]]) for r in self.rows]

    def strip(self, i):
        """Strip i as rows of pixel values (stored width)."""
        ty, w, h, fl = self.rows[i][:4]
        assert ty == 0
        raw = lz10.decompress(self.blobs[i][1])
        s = len(raw) * 2 // h
        return [[raw[(y * s + x) >> 1] >> 4 * (x & 1) & 15 for x in range(s)] for y in range(h)]

    def set_strip(self, i, px):
        raw = bytes(r[x] | r[x + 1] << 4 for r in px for x in range(0, len(r), 2))
        self.blobs[i] = (self.blobs[i][0], lz10.compress(raw))

    def build(self):
        """Blobs keep their stock offsets (the stock padding is irregular) and later blobs only
        shift when an edited one outgrows its slot."""
        out = bytearray(self.data[:self.base])
        slots = sorted((r[k], i, k) for i, r in enumerate(self.rows) for k in (4, 6) if r[k + 1])
        ends = [o for o, _, _ in slots[1:]] + [len(self.data) - self.base]
        data, shift = bytearray(), 0
        for (off, i, k), end in zip(slots, ends):
            blob = self.blobs[i][k == 6]
            new = max(off + shift, len(data) + (-len(data) % 0x80))
            shift = new - off
            data += b'\0' * (new - len(data))
            if blob == self.data[self.base + off:self.base + off + len(blob)]:
                blob = self.data[self.base + off:self.base + end]   # stock slot incl. its gap bytes
            data += blob
            self.rows[i][k] = new
            self.rows[i][k + 1] = len(self.blobs[i][k == 6])
        end = len(self.data) - self.base + shift
        data += b'\0' * (end - len(data))
        for i, r in enumerate(self.rows):
            ROW.pack_into(out, self.toff + ROW.size * i, *r)
        return bytes(out + data)


# ---- prologue captions -------------------------------------------------------------------
# (file, entry): two lines, centred in the strip's shown width. Fill 1, outline 2 (8-neighbour)
CAPTIONS = {
    ('FLS/M20.fls', 27): ('What is it, Clau?', 'What did you want to show me?'),
    ('FLS/M22.fls', 1): ('Hey, stop it!', "That's too reckless!"),
    ('FLS/M22.fls', 2): ("It's fine, it's fine.", 'Just leave it to me!'),
    ('FLS/M24.fls', 3): ('All right, a ship is coming!!', 'Go tell the captain!!'),
    ('FLS/M24.fls', 4): ('Admiral! A foreign merchant ship!', 'Your orders?'),
}
CAPTION_Y = (2, 18)


def caption(w, h, s, lines):
    import gfx
    px = [[0] * s for _ in range(h)]
    for line, y0 in zip(lines, CAPTION_Y):
        m = gfx.text_mask(line)
        tw = len(m[0])
        if tw + 2 > w:
            raise ValueError('caption too wide (%d > %d): %r' % (tw + 2, w, line))
        x0 = (w - tw) // 2
        for y, row in enumerate(m):
            for x, v in enumerate(row):
                if v:
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            p = px[y0 + y + dy]
                            if not p[x0 + x + dx]:
                                p[x0 + x + dx] = 2
        for y, row in enumerate(m):
            for x, v in enumerate(row):
                if v:
                    px[y0 + y][x0 + x] = 1
    return px


# ---- opening name cards ------------------------------------------------------------------
# Hand-drawn letters missing from the stock cards, in each card's own pixel values
# (Bergstrom card: 7/8 outline, b..f body; Argot/Overijssel card: 6/7/9 outline, b rim, c..e body).
# (bottom row sits on the line's 'base' row given in CARDS)
GLYPHS = {
    'c': ( '''
....77777...
...78888877.
...88bbb8887
..88deeffb87
.88ee88efd87
88dfb888887.
.bffb87777..
.dffb87.....
.efd87......
.efd887777..
.efeb88bd87.
8bfffefd887.
8888888887..
777777777...'''),
    'h': ( '''
..7777.......
.788887......
788db87......
.8dfe8777777.
.8dfd88888887
.8dfe88bffb87
.8dfdbdeffb87
.8dfeebbef887
.8effb8bfe87.
.8ffd88bfd87.
8bff888dfb87.
8dfd888efb87.
8efb888ffb87.
8efb888efb87.
888888888887.
77777777777..'''),
    'K': ( '''
...66666..66666
..6bbbbb66bbbb6
..6bdedb6bbeeb6
..6bdecbbbeeb6.
..6bdebbdeeb6..
..6bdebeedb6...
.9bbedeedb6....
.6bbeeedbb6....
.6bceedeb6.....
.6beebbdeb6....
9bbeebbbdeb6...
6bceb66bbdeb6..
6bdeb6.6bdeeb6.
6bbbb6..6bbbb6.
.6666....6666..'''),
    'R': ( '''
...6666666...
..6bbbbbbbb6.
..6bdeeeedbb6
..6bdebbbdeb6
..6bdeb6bbeb6
..6bdebbdeb6.
.9bbedeedbb6.
.6bbeedbbb6..
.6bcebdeb6...
.6beebbdeb6..
9bbeebbbdeb6.
6bceb66bbdeb6
6bdeb6.6bdeb6
6bbbb6.6bbbb6
.6666...6666.'''),
}

# file -> stock card frames (first, last) with the letters each frame adds, and the new cards:
# (frames, line) where line = list of words; a word is a list of tokens: a stock letter index
# into the card's steps or a GLYPHS key. Frame k of the new card shows the first k+1 letters
# (held on the full name when the new name is shorter). keep_prev: the previous card's last
# frame stays underneath.
CARDS = [
    # Hoodlum Joakim Bergstrom -> Hodrum Joachim Bergstrom (same 22 letters)
    dict(file='FLS/M28.fls', first=25, last=46,
         steps='H o o d l u m J o a k i m B e r g s t r o m'.split(),
         base=16, words=[[0, 1, 3, 15, 5, 6], [7, 8, 9, 'c', 'h', 11, 12], list(range(13, 22))]),
    # Lil Argot -> Ril Argot
    dict(file='FLS/M28.fls', first=49, last=56,
         steps='L i l A r g o t'.split(),
         base=50, words=[['R', 1, 2], [3, 4, 5, 6, 7]]),
    # Camille Overijssel -> Kamil Overijssel (Ril Argot stays on the second line)
    dict(file='FLS/M28.fls', first=57, last=72, keep_prev=True,
         steps='C a m i l l e O v e r ij s s e l'.split(),
         base=20, words=[['K', 1, 2, 3, 4], list(range(7, 16))]),
]
OVERLAP = 3                         # italic letters: next bbox starts 3 px before this one ends


def _letters(f, first, last):
    """Pixels each frame adds: list of {(x, y): v}."""
    frames = [f.strip(i) for i in range(first, last + 1)]
    prev = [[0] * len(frames[0][0]) for _ in frames[0]]
    out = []
    for px in frames:
        out.append({(x, y): px[y][x] for y in range(len(px)) for x in range(len(px[0]))
                    if px[y][x] != prev[y][x]})
        prev = px
    return out


def _glyph(name, base):
    art = GLYPHS[name]
    rows = art.strip('\n').split('\n')
    y0 = base - len(rows) + 1
    return {(x, y0 + y): int(c, 16) for y, r in enumerate(rows) for x, c in enumerate(r) if c != '.'}


def _bbox(g):
    xs = [x for x, _ in g]
    return min(xs), max(xs)


def card(f, c, prev_frame=None):
    letters = _letters(f, c['first'], c['last'])
    lefts = [_bbox(g)[0] for g in letters]
    # place
    x = lefts[c['words'][0][0]] if isinstance(c['words'][0][0], int) else lefts[0]
    placed = []
    for wi, word in enumerate(c['words']):
        if wi:
            # keep the stock distance between the end of the previous word and this word's
            # first stock letter when this word starts with a stock letter in the same place
            first = word[0]
            x += 1 if isinstance(first, str) else max(1, lefts[first] - lefts[first - 1]
                                                       - (_bbox(letters[first - 1])[1]
                                                          - lefts[first - 1] + 1 - OVERLAP))
        for t in word:
            g = letters[t] if isinstance(t, int) else _glyph(t, c['base'])
            l, r = _bbox(g)
            placed.append({(px - l + x, py): v for (px, py), v in g.items()})
            x += r - l + 1 - OVERLAP
    base = None
    if c.get('keep_prev'):
        prev = prev_frame
        base = {(x, y): v for y, row in enumerate(prev) for x, v in enumerate(row) if v}
    frames = []
    st = f.strip(c['first'])
    h, w = len(st), len(st[0])
    for k in range(c['last'] - c['first'] + 1):
        px = [[0] * w for _ in range(h)]
        for g in ([base] if base else []) + placed[:k + 1]:
            for (gx, gy), v in g.items():
                if v > px[gy][gx]:
                    px[gy][gx] = v
        frames.append(px)
    return frames, x


# ---- boot slide "リコエイションゲーム" ----------------------------------------------------------
# logo.fls entries 1-3 are full-screen 4bpp slides (256 px rows, LZ10). Entry 3's katakana is
# replaced by "A RECOEITION GAME" composed from the italic letters of entry 2 ("AN EIJI
# FUKUZAWA PRODUCTION"). Letters are cut in an un-slanted copy of the line (row y shifted by
# round((y - LOGO_Y1) * LOGO_K)), placed side by side there and slanted back, so stock letters
# come back pixel-exact. G = C + O's lower right + bar, M = left half of N + its mirror.
LOGO_Y0, LOGO_Y1, LOGO_K, LOGO_PAD = 88, 104, 0.25, 8
LOGO_CUTS = dict(A=(16, 26), N=(26, 36), E=(43, 51), I=(51, 55), C=(204, 214), T=(214, 223),
                 O=(227, 238), R=(163, 173))
LOGO_TEXT = 'A RECOEITION GAME'
LOGO_SPACE = 7


def _slide(f, i):
    raw = lz10.decompress(f.blobs[i][1])
    return [[raw[y * 128 + (x >> 1)] >> 4 * (x & 1) & 15 for x in range(256)] for y in range(len(raw) // 128)]


def _set_slide(f, i, px):
    f.blobs[i] = (f.blobs[i][0], bytes(r[x] | r[x + 1] << 4 for r in px for x in range(0, 256, 2)))
    f.blobs[i] = (f.blobs[i][0], lz10.compress(f.blobs[i][1]))


def _logo_shift(y):
    return round((y - LOGO_Y1) * LOGO_K) + LOGO_PAD


def _seam(up, x0, r=1):
    """Darkest top-to-bottom path near column x0 (one x per row, steps of at most 1):
    the boundary between two kerned letters."""
    h = len(up)
    xs = range(x0 - r, x0 + r + 1)
    cost = {x: up[0][x] for x in xs}
    back = []
    for y in range(1, h):
        nc, bk = {}, {}
        for x in xs:
            p = min((cost[q] + abs(q - x0) * 0.01, q) for q in (x - 1, x, x + 1) if q in cost)
            nc[x], bk[x] = p[0] + up[y][x], p[1]
        cost = nc
        back.append(bk)
    x = min(xs, key=lambda q: (cost[q], abs(q - x0)))
    path = [x]
    for bk in reversed(back):
        x = bk[x]
        path.append(x)
    return path[::-1]


def _logo_letter(up, a, b):
    """Letter between the seams near columns a and b (seam pixels go to neither side)."""
    sa, sb = _seam(up, a), _seam(up, b)
    return [[v if sa[y] < a - 3 + x < sb[y] else 1 for x, v in enumerate(row[a - 3:b + 3])]
            for y, row in enumerate(up)]


def logo(f):
    src = _slide(f, 2)
    h = LOGO_Y1 - LOGO_Y0
    up = [[1] * 280 for _ in range(h)]
    for y in range(h):
        s = _logo_shift(LOGO_Y0 + y)
        for x in range(256):
            up[y][x + s] = src[LOGO_Y0 + y][x]
    g = {k: _logo_letter(up, a, b) for k, (a, b) in LOGO_CUTS.items()}   # 3 px margins
    adv = {k: b - a for k, (a, b) in LOGO_CUTS.items()}
    # G: C closed on the lower right by O's right side, plus a bar into the middle
    gg = [r[:] for r in g['C']]
    o = g['O']
    for y in range(8, h):
        for x in range(8, 12):
            gg[y][x] = max(gg[y][x], o[y][x + 1])
    for x in range(7, 12):
        gg[8][x] = max(gg[8][x], 15)
        gg[7][x] = max(gg[7][x], 3)
        gg[9][x] = max(gg[9][x], 6)
    g['G'], adv['G'] = gg, adv['C']
    # M: N's left stem + upper diagonal, the diagonal mirrored, N's right stem moved right
    n = g['N']
    m = [[1] * (len(n[0]) + 2) for _ in range(h)]
    for y in range(h):
        for x in range(len(n[0])):
            if x <= 8 and (y < 9 or x < 6):
                m[y][x] = max(m[y][x], n[y][x])
                if 5 <= x <= 8 and 2 < y < 9:
                    m[y][17 - x] = max(m[y][17 - x], n[y][x])
            if x >= 10 or (x == 9 and y < 6):
                m[y][x + 2] = max(m[y][x + 2], n[y][x])
    g['M'] = m
    adv['M'] = adv['N'] + 2
    line = [[1] * 300 for _ in range(h)]
    w = 3
    for ch in LOGO_TEXT:
        if ch == ' ':
            w += LOGO_SPACE
            continue
        for y in range(h):
            for x, v in enumerate(g[ch][y]):
                line[y][w - 3 + x] = max(line[y][w - 3 + x], v)
        w += adv[ch]
    w += 3
    dst = _slide(f, 3)
    for y in range(80, 112):
        dst[y] = [1] * 256
    x0 = (256 - w + round(h * LOGO_K)) // 2 - round(h * LOGO_K)
    for y in range(h):
        s = _logo_shift(LOGO_Y0 + y) - LOGO_PAD
        for x, v in enumerate(line[y]):
            if v > 1:
                dst[LOGO_Y0 + y][x0 + x - s] = v
    _set_slide(f, 3, dst)


def apply(rom):
    files = {}

    def get(name):
        if name not in files:
            files[name] = Fls(rom.getFileByName(name))
        return files[name]

    for (name, i), lines in CAPTIONS.items():
        f = get(name)
        ty, w, h, fl = f.rows[i][:4]
        f.set_strip(i, caption(w, h, len(f.strip(i)[0]), lines))
    last = None
    for c in CARDS:
        f = get(c['file'])
        frames, end = card(f, c, last)
        if end > len(frames[0][0]):
            raise ValueError('card too wide: %d' % end)
        for k, px in enumerate(frames):
            f.set_strip(c['first'] + k, px)
        last = frames[-1]
    logo(get('FLS/logo.fls'))
    for name, f in files.items():
        rom.setFileByName(name, f.build())
    return len(CAPTIONS) + len(CARDS) + 1
