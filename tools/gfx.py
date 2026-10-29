"""Graphic text edits applied at build time: English labels drawn over the ROM's .pxl art.

A label edit names a box (x, y, w, h) in image pixels. The Japanese ink inside it (pixels far
from the box's median brightness) is erased by refilling each pixel from the nearest clean pixel
of the same row (keeps gradients and texture), then the English is drawn centred with the
in-game VWF glyphs (font.py) in the original ink colour. Colours always come from the image's
own palette, so nothing of the original art is stored here.
"""
import os
import struct
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(__file__))
import boldfont  # noqa: E402
import font  # noqa: E402
import pxl  # noqa: E402


class Img:
    """A .pxl file (4/8 bpp), or block 0 of a GRP archive entry (type 0x10, block=True), as a
    mutable index array."""

    def __init__(self, data, block=False):
        self.data = bytearray(data)
        if block:
            b = pxl.parse_blocks(data)['blocks'][0]
            self.bpp, self.w, self.h, self.pal, idx = b['bpp'], b['w'], b['h'], b['pal'], b['idx']
            self.off = b['off'] + 12
        else:
            p = pxl.parse(data)
            self.bpp, self.w, self.h, self.pal, idx = p['bpp'], p['w'], p['h'], p['pal'], p['idx']
            self.off = struct.unpack_from('<I', data, 16)[0]
        self.px = bytearray(idx[:self.w * self.h])

    def get(self, x, y):
        return self.px[y * self.w + x]

    def put(self, x, y, v):
        self.px[y * self.w + x] = v

    def lum(self, v):
        r, g, b = self.pal[v]
        return 0.3 * r + 0.59 * g + 0.11 * b

    def save(self):
        out = self.data
        if self.bpp == 8:
            out[self.off:self.off + len(self.px)] = self.px
        else:
            out[self.off:self.off + len(self.px) // 2] = bytes(
                self.px[i] | self.px[i + 1] << 4 for i in range(0, len(self.px), 2))
        return bytes(out)


_W = None


# 7-row capitals for labels in 8 px rows (__frame cargo/ship buttons); own drawing
TINY = {c: g.split() for c, g in dict(
    A='.##. #..# #..# #### #..# #..# #..#', C='.### #... #... #... #... #... .###',
    D='###. #..# #..# #..# #..# #..# ###.', E='#### #... #... ###. #... #... ####',
    G='.### #... #... #.## #..# #..# .###', H='#..# #..# #..# #### #..# #..# #..#',
    I='### .#. .#. .#. .#. .#. ###', K='#..# #.#. ##.. #... ##.. #.#. #..#',
    L='#... #... #... #... #... #... ####', N='#..# ##.# ##.# #.## #.## #..# #..#',
    O='.##. #..# #..# #..# #..# #..# .##.', P='###. #..# #..# ###. #... #... #...',
    R='###. #..# #..# ###. #.#. #..# #..#', S='.### #... #... .##. ...# ...# ###.').items()}


def text_mask(text, bold=False, tiny=False):
    """Rows (list of bool lists, 11 tall) of text drawn with the VWF font, or with the bold
    capitals of boldfont.py (bold=True; text is upper-cased), or the 7-row TINY capitals."""
    if bold or tiny:
        gs = [[[c == '#' for c in r] for r in TINY[ch]] if tiny else boldfont.GLYPHS[ch]
              for ch in text.upper()]
        w = sum(len(g[0]) for g in gs) + len(gs) - 1
        m = [[False] * w for _ in range(11)]
        x = 0
        for g in gs:
            for y, r in enumerate(g):
                for i, v in enumerate(r):
                    m[y][x + i] = v
            x += len(g[0]) + 1
        return m
    global _W
    if _W is None:
        _W = font.table()[1]
    cols = []
    for ch in text:
        adv = _W[ord(ch)]
        if ch == ' ':
            cols += [[False] * font.ROWS] * adv
            continue
        rows = font.glyph_rows(ch)
        if ch not in font.FIXED:        # as table(): narrow glyphs are shifted to column 0
            rows = font._trim(rows)[0]
        for x in range(adv):
            cols.append([x < len(r) and r[x] == '#' for r in rows])
    while cols and not any(cols[-1]):
        cols.pop()
    return [[c[y] for c in cols] for y in range(font.ROWS)]


def erase(img, box, dark=True, thresh=22, grow=1, both=False):
    """Remove the ink inside box; returns the ink mask (before growing) and the ink colours."""
    x0, y0, w, h = box
    vals = [img.get(x, y) for y in range(y0, y0 + h) for x in range(x0, x0 + w)]
    med = sorted(img.lum(v) for v in vals)[len(vals) // 2]
    ink = {(x, y) for y in range(y0, y0 + h) for x in range(x0, x0 + w)
           if (abs(med - img.lum(img.get(x, y))) if both else
               med - img.lum(img.get(x, y)) if dark else img.lum(img.get(x, y)) - med) > thresh}
    colours = Counter(img.get(x, y) for x, y in ink)
    mask = set(ink)
    for _ in range(grow):
        mask |= {(x + dx, y + dy) for x, y in mask for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                 if x0 <= x + dx < x0 + w and y0 <= y + dy < y0 + h}
    # fill layer by layer from clean neighbours (same row first, so gradients and texture carry)
    while mask:
        done = {}
        for x, y in mask:
            for nb in ((x - 1, y), (x + 1, y), (x - 2, y), (x + 2, y), (x, y - 1), (x, y + 1)):
                if nb not in mask and x0 <= nb[0] < x0 + w and y0 <= nb[1] < y0 + h:
                    done[(x, y)] = img.get(*nb)
                    break
        if not done:
            break
        for (x, y), v in done.items():
            img.put(x, y, v)
        mask -= set(done)
    return ink, colours


def label(img, box, text, dark=True, thresh=22, align='c', dx=0, dy=0, ink=None, shadow=None,
          rows=font.ROWS, bold=False, grad=False, outline=None, both=False, clear=None, tiny=False):
    """Replace the text in box with text (centred unless align='l'); only the first `rows`
    glyph rows are drawn (descenders may reach below the box). grad: ink colour per row taken
    from the original's rows; outline: a palette index, or 'auto' (the colour around the old ink);
    clear: fill the box with this index instead of rebuilding it (masks)."""
    x0, y0, w, h = box
    before = {(x, y): img.get(x, y) for y in range(y0, y0 + h) for x in range(x0, x0 + w)}
    old, colours = erase(img, box, dark, thresh, both=both)
    if clear is not None:
        for y in range(y0, y0 + h):
            for x in range(x0, x0 + w):
                img.put(x, y, clear)
    key = (lambda v: img.lum(v)) if dark else (lambda v: -img.lum(v))
    colours = Counter({v: n for v, n in colours.items() if both is False or key(v) < key(
        sorted(colours, key=key)[len(colours) // 2])})
    if ink is None:
        # the most common ink colour among the strongest third of the ink pixels
        strong = sorted(colours, key=key)[:max(1, len(colours) // 3)]
        ink = max(strong, key=lambda v: colours[v])
    inks = [ink]
    if grad and old:
        inks = []
        for y in range(min(y for _, y in old), max(y for _, y in old) + 1):
            c = Counter(before[p] for p in old if p[1] == y)
            if c:
                inks.append(min(c.most_common(3), key=lambda kv: key(kv[0]))[0])
    if shadow == 'dark':
        shadow = min(range(len(img.pal)), key=img.lum)
    if outline == 'auto':
        ring = Counter(before[(x + ddx, y + ddy)] for x, y in old for ddx in (-1, 0, 1) for ddy in (-1, 0, 1)
                       if (x + ddx, y + ddy) in before and (x + ddx, y + ddy) not in old)
        outline = ring.most_common(1)[0][0]
    if not text:
        return img
    m = text_mask(text, bold, tiny)
    tw = len(m[0])
    cap = 7 if tiny else 11 if bold else 9                      # ink rows of a capital
    if tw > w:
        raise ValueError('%r is %d px wide, box %d' % (text, tw, w))
    ox = x0 + (w - tw) // 2 if align == 'c' else x0 + 1
    oy = y0 + (h - cap) // 2
    if old:
        top, bot = min(y for _, y in old), max(y for _, y in old)
        oy = top + (bot - top + 1 - cap) // 2
    ox, oy = ox + dx, oy + dy
    on = {(x, y) for y in range(min(rows, len(m))) for x in range(tw) if m[y][x]}
    if outline is not None:
        for x, y in {(x + a, y + b) for x, y in on for a in (-1, 0, 1) for b in (-1, 0, 1)} - on:
            img.put(ox + x, oy + y, outline)
    for x, y in on:
        if shadow is not None and (x + 1, y + 1) not in on:
            img.put(ox + x + 1, oy + y + 1, shadow)
    for x, y in on:
        img.put(ox + x, oy + y, inks[min(len(inks) - 1, y * len(inks) // cap)])
    return img


def widen(img, box, new_w, cap=4, shadow=1):
    """Stretch a plate (outer box) to new_w px: end caps kept, middle columns repeated; the
    plate's shadow column/row moves with it. Overwrites the background to its right."""
    x0, y0, w, h = box
    cols = [[img.get(x0 + x, y0 + y) for y in range(h + shadow)] for x in range(w + shadow)]
    mid = cols[cap:w - cap]
    new = cols[:cap] + [mid[i % len(mid)] for i in range(new_w - 2 * cap)] + cols[w - cap:]
    for x, col in enumerate(new):
        for y, v in enumerate(col):
            img.put(x0 + x, y0 + y, v)


def edit(img, e):
    box, text, opt = e
    opt = dict(opt)
    if opt.pop('plate', True):
        if 'widen' in opt:
            widen(img, box, opt['widen'])
            box = (box[0], box[1], opt.pop('widen'), box[3])
        box = (box[0] + 1, box[1] + 1, box[2] - 2, box[3] - 2)
    label(img, box, text, **opt)


# --- edits -------------------------------------------------------------------------------
# file -> [(box, text, opts)]. Default: box = a stone plate's outer box (tools/dev/plates.py),
# the label goes inside its 1 px bevel; widen=W stretches the plate first. plate=False: raw box.
def rows(x, y0, step, w, h, texts, **o):
    return [((x, y0 + i * step, w, h), t, o) for i, t in enumerate(texts) if t]


# character select: 5 dark 44x12 cells, white text in rows 1-9 (no room for descenders)
CHARSELECT = rows(4, 1, 12, 36, 9, ['Given', 'Middle', 'Surname', 'Faction', 'Birthday'],
                  plate=False, dark=False, rows=10)

# character select: the plate labels are a mask below the picture (white 255, shadow 1 at +1,+1)
CS_MASK = rows(0, 235, 16, 54, 14, ['Given Name', 'Middle Name', 'Family Name', 'Faction', 'Birthday'],
               plate=False, dark=False, clear=0, ink=255, shadow=1)
# UI atlases (also combined in GRP/CMMNIMG.DK4 entry 5: __marker left, __frame right); white text
W = dict(plate=False, dark=False)
WT = dict(W, tiny=True)
MARKER = rows(6, 3, 24, 52, 18, ['System', 'Crew Setup', 'Deck Screen', 'Info', 'Route Map', 'Items'], **W) + \
    rows(65, 2, 16, 45, 12, ['Redo', 'OK', 'Cancel', 'Finances', 'Delegate', 'Port Call', 'Attack', 'Patrol',
                             'Orders'], **W) + \
    [((113, 1, 30, 13), 'Sale', W), ((113, 17, 30, 13), 'Local', W), ((113, 33, 30, 13), 'Cargo', W),
     ((113, 49, 30, 11), 'Sell', W), ((113, 61, 30, 12), 'Buy', W),
     ((186, 1, 60, 14), 'Temp Hold', W), ((174, 65, 42, 14), 'Gifts', W), ((174, 81, 42, 14), 'Spoils', W),
     ((235, 98, 11, 11), 'M', dict(W, bold=True)), ((243, 113, 11, 12), 'F', dict(W, bold=True))]
FRAME = [((192, 1, 31, 12), 'Type', W), ((184, 16, 29, 13), 'Price', W), ((126, 16, 36, 13), 'Month', W),
         ((4, 122, 32, 12), 'Equip', W), ((4, 138, 32, 12), 'Advice', W),
         ((44, 162, 40, 12), 'Crew', W), ((92, 162, 40, 12), 'Flagship', W), ((140, 162, 40, 12), 'Minimum', W),
         ((44, 178, 40, 12), 'Even Out', W), ((92, 178, 40, 12), 'Resupply', W), ((140, 194, 40, 12), 'Done', W),
         ((4, 194, 32, 12), 'Yes', W), ((44, 194, 32, 12), 'No', W), ((4, 210, 32, 12), 'Remove', W),
         ((44, 210, 32, 12), 'Use', W),
         ((104, 114, 9, 11), '/', W), ((128, 114, 9, 11), '', W),
         ((208, 32, 48, 8), 'Cargo', WT), ((208, 40, 30, 8), 'Ship', WT), ((238, 40, 18, 8), 'End', WT),
         ((183, 48, 21, 8), 'Rank', WT), ((205, 48, 46, 8), 'Cancel', WT)]       # date "1月 1日" -> "1/ 1"
DSOBJ = rows(7, 5, 32, 50, 13, ['System', 'Crew Setup', 'Deck', 'Info', 'Route Map', 'Items'], ink=15, **W) + \
    rows(0, 192, 16, 12, 13, ['E', 'S', 'W', 'N', '/'], ink=15, outline=1, **W) + \
    [((0, 272, 12, 13), '', dict(W, clear=0))]            # date "1月 8日" -> "1/ 8"
BAR = dict(plate=False, dark=False, both=True, thresh=40, align='l', shadow='dark')
TITLE = dict(plate=False, dark=False, bold=True, grad=True, outline='auto')
RACE = dict(plate=False, dark=False, bold=True, clear=0, ink=15, outline=1, thresh=10, both=True)
PRESS = [((2, 2, 152, 20), 'Press a button!', dict(plate=False, dark=False, bold=True, outline=0, thresh=45, both=True))]

EDITS = {
    '_pxl/chihofleetinfo.pxl': [((84, 76, 40, 16), 'Level', {})] +
    rows(8, 100, 20, 40, 16, ['Income', 'Costs', 'Invest', 'Duty']),
    '_pxl/fleetinfo.pxl': [((84, 76, 40, 16), 'Level', {})],
    '_pxl/forceinfo.pxl': [((84, 76, 40, 16), 'Level', {})] +
    rows(8, 104, 20, 40, 16, ['Gold', '', 'Base', 'Goodwill']) + [((8, 124, 40, 16), 'Influence', dict(widen=44))],
    '_pxl/saveloadinfo.pxl': [((96, 40, 40, 16), 'Level', {}), ((96, 64, 40, 16), 'Influence', dict(widen=44))],
    '_pxl/personinfo.pxl': rows(8, 104, 20, 40, 16, ['Health', 'Mood', 'Level', 'HP']),
    '_pxl/dividecrewinfo.pxl': [((8, 19, 80, 16), 'Fleet Sailors', {}), ((134, 19, 80, 16), 'Unassigned', {}),
                                ((8, 41, 80, 16), 'Days of Supply', {}), ((8, 109, 56, 16), 'Marine Qtrs', {}),
                                ((86, 109, 32, 16), 'Guns', {}), ((8, 131, 56, 16), 'Fore & Aft', {}),
                                ((134, 131, 56, 16), 'Square Sail', {})],
    '_pxl/shipinfo.pxl': [((8, 44, 16, 16), 'Water', dict(widen=32)), ((70, 44, 32, 16), 'Food', {}),
                          ((134, 44, 32, 16), 'Sailors', dict(widen=40)), ((8, 64, 56, 16), 'Supply Hold', {}),
                          ((134, 64, 32, 16), 'Cargo', {}), ((8, 84, 56, 16), 'Fore & Aft', {}),
                          ((134, 84, 56, 16), 'Square Sail', {}), ((8, 104, 56, 16), 'Marine Qtrs', {}),
                          ((134, 104, 56, 16), 'Battery', {}), ((8, 124, 32, 16), 'Guns', {}),
                          ((8, 144, 40, 16), 'Durability', dict(widen=48))],
    '_pxl/towninfo.pxl': [((8, 20, 40, 16), 'Type', {}), ((136, 20, 40, 16), 'Growth', {}),
                          ((8, 40, 40, 16), 'Status', {}), ((136, 40, 40, 16), 'Arms', {}),
                          ((1, 61, 126, 16), 'Share', {}), ((129, 61, 126, 16), 'Specialties', {})],
    '_pxl/goldsearoutediscovery.pxl': rows(8, 16, 0, 40, 16, ['Goods']) + [((8, 52, 40, 16), 'Profit', {}),
                                                                           ((8, 80, 40, 16), 'Reward', {})],
    '_pxl/goldsearoutelog.pxl': [((1, 0, 166, 16), 'Goods', {}), ((169, 0, 42, 16), 'Profit', {}),
                                 ((213, 0, 42, 16), 'Reward', {})],
    'GRP/DSOBJ.DK4': DSOBJ,
    '_pxl/__marker.pxl': MARKER,
    '_pxl/__frame.pxl': FRAME,
    '_pxl/charselect.pxl': CS_MASK,
    '_pxl/haifuhin.pxl': [((2, 1, 70, 14), 'Gifts', dict(BAR, dx=3))],
    '_pxl/senrihin.pxl': [((2, 1, 70, 14), 'Spoils', dict(BAR, dx=3))],
    '_pxl/tempcargo.pxl': [((0, 1, 72, 14), 'Temp Hold', BAR)],
    '_pxl/slackimg12.pxl': CHARSELECT,
    'GRP/SLACKIMG.DK4#12': CHARSELECT,
    '_pxl/title/title02.pxl': [((0, 0, 256, 14), 'Press START', TITLE),
                               ((0, 14, 256, 15), 'or touch the screen', TITLE)],
    '_pxl/title/title06.pxl': [((0, 0, 256, 14), 'Press A or touch', TITLE),
                               ((0, 14, 256, 15), 'the screen to skip', TITLE)],
    '_pxl/slackimg20.pxl': PRESS,
    'GRP/SLACKIMG.DK4#20': PRESS,
    '_pxl/kakutei.pxl': [((4, 3, 40, 14), 'OK', dict(plate=False, dark=False, bold=True))],
    'GRP/DSOBJR.DK4': [((0, 0, 192, 16), 'Press START or', RACE), ((0, 16, 192, 16), 'touch the lower screen', RACE)],
    '_pxl/online/Online00.pxl': [((147, 144, 14, 13), '', dict(plate=False)),          # Windows(R)版
                                 ((56, 157, 144, 11), 'Details at the official site below', dict(plate=False))],
    '_pxl/goldsearoutelog2.pxl': [((1, 0, 166, 16), 'Goods', {}), ((169, 0, 86, 16), 'Total Reward', {})],
}


# "Introducing Online" slides (title -> Extras): bottom-screen paragraph overlays, white (15)
# text with a black (1) outline on transparent 0, left edge x 39, 14 px line pitch, centred on y 89.
ONLINE = {
    50: ["Become the captain of a sailing ship", "and set out across the endless", "ocean of an online world!"],
    51: ["Team up with other players,", "or overcome it all on your own.", "Every meeting and every hardship", "makes a story of its own!"],
    52: ["Search for ports and trade goods,", "or hunt down pirates all day long.", "You decide what to do.", "You can even get a bounty on your head!"],
    53: ["Open up new waters to sail", "and set off on more adventures.", "Head out now onto a sea", "full of thrills and spectacle!"],
    54: ["There are about 50 occupations.", "Gain experience to change jobs.", "Grow your character as you like!"],
    55: ["- Adventure -", "Countless mysteries lie hidden", "in this vast world...", "Seek out ruins and treasures and", "chase great discoveries!"],
    56: ["- Trade -", "Hundreds of trade goods to deal in.", "Buy and sell to move the market!", "Found something rare? Open a", "bazaar and start doing business!"],
    57: ["- Battle -", "Use cannon fire and boarding to", "protect adventurers and merchants!", "Players can even team up", "as a pirate crew, of course!!"],
    58: ["On your travels, many meetings", "with event characters await.", "Each nation you can join", "has a story of its own!"],
    59: ["Your actions shape the world!", "In great naval wars for national", "pride, your vote may decide", "which port comes under attack!"],
    60: ["Call out to players you meet", "and form a fleet together.", "Use your members' skills to", "solve riddles or fight pirates."],
    61: ["Ships come in all types and sizes.", "Customize materials, guns,", "number of sails, crests and more", "to your heart's content!"],
    62: ["The Pyramids, the Leaning Tower", "of Pisa: ruins and cities built", "in 3D. The stage for adventure", "stretches out endlessly before you!"],
}


def paragraph(img, lines, x=40, cy=89, pitch=14, ink=15, outline=1):
    img.px[:] = bytes(len(img.px))
    y0 = cy - (pitch * len(lines) - 1) // 2 + 1
    for i, line in enumerate(lines):
        m = text_mask(line)
        on = {(x + dx, y0 + i * pitch + dy) for dy in range(len(m)) for dx in range(len(m[0])) if m[dy][dx]}
        for p in {(px + a, py + b) for px, py in on for a, b in ((-1, 0), (1, 0), (0, -1), (0, 1))} - on:
            img.put(*p, outline)
        for p in on:
            img.put(*p, ink)


class TileImg(Img):
    """Raw 4bpp OBJ tiles (1D mapping) seen as one image: objects (first tile, w, h in tiles)
    stacked top to bottom, or placed at (first tile, w, h, x, y) in pixels. No palette in the
    file: index = brightness (grey ramp)."""

    def __init__(self, data, objs):
        self.data, self.objs, self.bpp = bytearray(data), objs, 4
        pos, y0 = [], 0
        for o in objs:
            pos.append(o if len(o) == 5 else (*o, 0, y0))
            y0 += o[2] * 8 if len(o) == 3 else 0
        self.w = max(x + w * 8 for _, w, _, x, _ in pos)
        self.h = max(y + h * 8 for _, _, h, _, y in pos)
        self.pal = [(v * 17,) * 3 for v in range(16)]
        self.map = {}
        for t0, tw, th, x0, y0 in pos:
            for k in range(tw * th):
                for i in range(64):
                    self.map[(x0 + (k % tw) * 8 + i % 8, y0 + (k // tw) * 8 + i // 8)] = ((t0 + k) * 32 + i // 2, i & 1)
        self.px = bytearray(self.w * self.h)
        for (x, y), (o, hi) in self.map.items():
            b = self.data[o]
            self.px[y * self.w + x] = b >> 4 if hi else b & 15

    def save(self):
        for (x, y), (o, hi) in self.map.items():
            v = self.px[y * self.w + x]
            self.data[o] = (self.data[o] & 0x0f) | v << 4 if hi else (self.data[o] & 0xf0) | v
        return bytes(self.data)


# raw OBJ tile files: name -> objects (first tile, w, h) making the virtual image
TILED = {'GRP/DSOBJ.DK4': [(32 * k, 8, 4) for k in range(6)] +          # sea command buttons 64x32
                          [(368 + 4 * k, 2, 2) for k in range(6)],       # 東南西北月日 16x16 at y 192..
         # race start prompt: two lines of three 64x16 objects (interleaved tiles)
         'GRP/DSOBJR.DK4': [(185 + 16 * k, 8, 2, 64 * (k // 2), 16 * (k % 2)) for k in range(6)]}


def load(rom, name):
    """(Img, write(Img)) for 'path.pxl', 'GRP/X.DK4#entry' or a TILED file."""
    if name in TILED:
        return TileImg(rom.getFileByName(name), TILED[name]), lambda img: rom.setFileByName(name, img.save())
    if '#' in name:
        path, i = name.split('#')
        entries = pxl.ilnk(rom.getFileByName(path))
        i = int(i)

        def write(img):
            entries[i] = img.save()
            rom.setFileByName(path, ilnk_build(entries))
        return Img(entries[i], block=True), write
    return Img(rom.getFileByName(name)), lambda img: rom.setFileByName(name, img.save())


def ilnk_build(entries):
    import cs
    return cs.build_ilnk(entries)


# GRP copies made of edited .pxl files: archive entry -> [(pxl, x offset)] (4bpp type 0x12 entries)
COPIES = {('GRP/CMMNIMG.DK4', 5): [('_pxl/__marker.pxl', 0), ('_pxl/__frame.pxl', 256)]}


def copy_to_grp(rom):
    for (path, i), parts in COPIES.items():
        entries = pxl.ilnk(rom.getFileByName(path))
        e = bytearray(entries[i])
        assert e[0] == 0x12
        w2, h = struct.unpack_from('<HH', e, 16)
        stride = w2 * 2
        for name, x0 in parts:
            img = Img(rom.getFileByName(name))
            assert img.bpp == 4 and img.h == h
            for y in range(h):
                row = img.px[y * img.w:(y + 1) * img.w]
                e[20 + y * stride + x0 // 2:20 + y * stride + (x0 + img.w) // 2] = bytes(
                    row[k] | row[k + 1] << 4 for k in range(0, img.w, 2))
        entries[i] = bytes(e)
        rom.setFileByName(path, ilnk_build(entries))


def apply(rom, edits=None):
    n = 0
    for name, items in (edits or EDITS).items():
        img, write = load(rom, name)
        for e in items:
            edit(img, e)
            n += 1
        write(img)
    if edits is None:
        for k, lines in ONLINE.items():
            img, write = load(rom, '_pxl/online/Online%02d.pxl' % k)
            paragraph(img, lines)
            write(img)
            n += 1
    copy_to_grp(rom)
    return n
