"""English text for MESFILE, HELP and the SC event scripts: load, encode, wrap, check.

tl/<src>/*.txt (src = mesfile, help, sc0..sc3), English only, one block per string:

    @<id>                 id as in script/<src>.json (mesfile/help: number; sc: EEE.PPPP[.v])
    English text; physical lines are joined with spaces and the result is auto-wrapped
    to the source's width. \\n forces a line break. A block containing just '=' keeps
    the Japanese.

Codes (the build moves them off the letters F and I, see patch_arm9.py):
    {FI} player admiral's name   {FA} {FO} {FU} other names (FO = a fleet)
    {IC} speaker's "I" (Japanese 僕/アタシ; for English: avoid, or keep only where it reads as a name)
    %s %d ... printf fields (MESFILE): same ones in the same order
    <$NN> raw byte (HELP link targets: {label:<$NN>})

An untranslated row falls back to the translation of an identical Japanese string anywhere
(SC1-3 share much of SC0), then to the Japanese.

usage:
    tl.py stats                     progress per source
    tl.py check [src]               validate all translated blocks
    tl.py show src [from] [count]   print Japanese rows (todo only with --todo)
"""
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
import font  # noqa: E402
from extract import encode  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRCS = ['mesfile', 'help', 'sc0', 'sc1', 'sc2', 'sc3']
CODE_F, CODE_I = 0x0e, 0x0f          # new code bytes for 'F' / 'I' (patch_arm9.py)
CODES = re.compile(r'\{F[IAOU]\}|\{I.\}|%[-0-9.]*l?[sdcxu]|<\$[0-9A-F]{2}>')
# max line width in px per source. SC dialogue box (melonDS, S4): inner width ~225 px, 4 lines;
# Japanese uses up to 18 full-width chars = 216 px.
WIDTH = {'sc': 216, 'mesfile': 216, 'help': None}
SC_LINES = 4                         # more only where the Japanese has more (box scrolls?)
# MESFILE contexts by id (S6, from the Japanese layout; boxes not all seen in the emulator):
# (first, last, width px or None = no pre-wrap (engine word-wraps), max lines or None = JP's)
MES_RANGES = [
    (104, 107, 132, None),           # character descriptions (6 short lines; maybe unused)
    (137, 343, 228, 4),              # trade goods descriptions (JP lines up to 19 chars)
    (1419, 1796, 132, 2),            # mate speech bubbles (JP max 11 chars x 2 lines)
    (2815, 3032, 228, 4),            # item descriptions: centred per line in ~240 px (engine wrap is wider)
    (3292, 3384, 228, None),         # Uncharted Waters Online ad pages (Extras)
    (3393, 3610, None, 1),           # gallery titles: one line
]
MES_LINES = 4                        # dialogue: up to the most lines any message in the block has
HELP_W, HELP_ROWS, HELP_LINK_ROWS = 252, 12, 10   # patch_arm9 HELP renderer; link rects rows 0-9
# MESFILE ids whose English leaves out trailing %s args (printf ignores extras): the tavern honorific
# (Sir/Miss) after a family name, 'Castor's Sir', reads wrong in English
MES_DROP_ARGS = {871, 872}
HELP_ICONS = '○×△□'                # SJIS button symbols kept in HELP English (as in the Japanese)
SC_SYMBOLS = '○×△□◎▲◇'            # SC: alien-language / garbled speech, kept as in the Japanese
NAME_PX = 60                         # assumed width of a {F?} name / %s
EVENT_MAX = 0x2404                   # whole CS entry: stack buffer in 0x02023e04 (frame 0x241c)


def kind(src):
    return 'sc' if src.startswith('sc') else src


def rows(src):
    return json.load(open(os.path.join(ROOT, 'script', src + '.json'), encoding='utf-8'))


def load(src):
    """{id(str): (english, file, line)} from tl/<src>/*.txt"""
    out = {}
    for path in sorted(glob.glob(os.path.join(ROOT, 'tl', src, '*.txt'))):
        cur = None
        for n, line in enumerate(open(path, encoding='utf-8'), 1):
            line = line.rstrip('\n')
            if line.startswith('@'):
                cur = line[1:].split('#')[0].strip()
                if cur in out:
                    raise ValueError('%s:%d: duplicate @%s' % (path, n, cur))
                out[cur] = ['', path, n]
            elif line.startswith('#') and cur is None:
                continue
            elif cur is not None:
                s = line.strip()
                if s:
                    out[cur][0] += (' ' if out[cur][0] and not out[cur][0].endswith('\\n') else '') + s
    return {k: (v[0], v[1], v[2]) for k, v in out.items()}


def jp_codes(jp):
    """Codes in a Japanese string, in tl notation."""
    out, i = [], 0
    while i < len(jp):
        c = jp[i]
        if c == 'F' and i + 1 < len(jp) and jp[i + 1] in 'IAOU':
            out.append('{F%s}' % jp[i + 1]); i += 2; continue
        if c == 'I' and i + 1 < len(jp):
            out.append('{I%s}' % jp[i + 1]); i += 2; continue
        m = CODES.match(jp, i)
        if m and m.group()[0] in '%<':
            out.append(m.group()); i = m.end(); continue
        i += 1
    return out


def encode_jp(jp):
    """Japanese row text -> game bytes with F/I codes moved to the new code bytes."""
    b = encode(jp)
    out, i = bytearray(), 0
    while i < len(b):
        c = b[i]
        if 0x81 <= c <= 0x9f or 0xe0 <= c <= 0xfc:
            out += b[i:i + 2]; i += 2; continue
        if c == 0x46 and i + 1 < len(b) and b[i + 1] in b'IAOU':
            out.append(CODE_F)
        elif c == 0x49 and i + 1 < len(b):
            out.append(CODE_I)
        else:
            out.append(c)
        i += 1
    return bytes(out)


def encode_en(en):
    """English (tl notation, real newlines) -> game bytes."""
    out = bytearray()
    for part in re.split(r'(\{F[IAOU]\}|\{I.\}|<\$[0-9A-F]{2}>)', en):
        if part.startswith('{F') and len(part) == 4:
            out += bytes([CODE_F, ord(part[2])])
        elif part.startswith('{I') and len(part) == 4:
            out += bytes([CODE_I, ord(part[2])])
        elif part.startswith('<$'):
            out.append(int(part[2:4], 16))
        else:
            out += b''.join(ch.encode('cp932' if ch in HELP_ICONS + SC_SYMBOLS else 'ascii') for ch in part)
    return bytes(out)


# SC name codes as the character-select defaults (FI, FA, FO, FU) for width checks. The build
# leaves rows with name codes to the engine's runtime word wrap (real, possibly renamed names).
SC_NAMES = {
    'sc0': ('Rafael', 'Castor', 'Castor Co.', 'Rafael Castor'),
    'sc1': ('Hodrum', 'Bergstrom', 'Bergstrom Army', 'Hodrum Joachim Bergstrom'),
    'sc2': ('Lil', 'Argot', 'Argot Co.', 'Lil Argot'),
    'sc3': ('Maria', 'Li', 'Li Clan', 'Maria Huamei Li'),
}
NAME_CODES = re.compile(r'\{F[IAOU]\}')


def join_soft(en):
    """Rows with name codes: forced breaks inside a sentence become spaces (workers broke lines
    around names of unknown length; the engine wraps with the real ones). Breaks after
    sentence-final punctuation and blank lines (page breaks) stay."""
    if not NAME_CODES.search(en):
        return en
    parts = en.split('\\n')
    out = parts[0]
    for b in parts[1:]:
        a = out.split('\\n')[-1]
        if a.strip() and b.strip() and not re.search(r'[.!?)"\'~:]$|\.\.\.$', a.rstrip()):
            out += ' ' + b.lstrip()
        else:
            out += '\\n' + b
    return out


def names(src):
    return dict(zip(('{FI}', '{FA}', '{FO}', '{FU}'), SC_NAMES[src])) if src in SC_NAMES else {}


def px(line, nm=None):
    """Width of one line in px (names from nm, else names/%s counted as NAME_PX)."""
    w = 0
    for part in re.split(r'(\{F[IAOU]\}|\{I.\}|%[-0-9.]*l?[sdcxu])', line):
        if not part:
            continue
        if nm and part in nm:
            w += font.width(nm[part])
        elif part[0] in '{%':
            w += NAME_PX
        else:
            w += font.width(part)
    return w


def wrap(text, width, nm=None):
    """Join forced lines (\\n) and greedily wrap each to width px."""
    lines = []
    for para in text.split('\\n'):
        words, cur = para.split(' '), ''
        for w in words:
            t = cur + ' ' + w if cur else w
            if cur and width and px(t, nm) > width:
                lines.append(cur)
                cur = w
            else:
                cur = t
        lines.append(cur)
    return '\n'.join(lines)


_block_lines = {}


def layout(src, r):
    """(wrap width px or None, max lines) for row r of src."""
    jn = r['jp'].count('\n') + 1
    if kind(src) == 'sc':
        if r['spk'] is None and r['id'].count('.') == 2:
            return 204, 1                # choice: menu box fits the widest JP option (204 px; S10)
        return WIDTH['sc'], max(jn, SC_LINES)
    if src == 'help':
        return None, None
    for lo, hi, w, n in MES_RANGES:
        if lo <= r['id'] <= hi:
            return (w, max(jn, n)) if n else (w, None if w is None else jn)
    if not _block_lines:
        for x in rows('mesfile'):
            b = x['block']
            _block_lines[b] = min(MES_LINES, max(_block_lines.get(b, 1), x['jp'].count('\n') + 1))
    return WIDTH['mesfile'], max(jn, _block_lines[r['block']])


def help_rows(en):
    """Simulate the patched HELP renderer: (rows used, last row holding a link)."""
    x = row = 0
    link_row = -1
    for m in re.finditer(r'\\n|\{([^:}]*):<\$[0-9A-F]{2}>\}|[^ \\{]+| ', en):
        t = m.group(0)
        if t == '\\n':
            x, row = 0, row + 1
            continue
        if t == ' ':
            x += font.width(' ') if x else 0
            continue
        w = px(m.group(1) if m.group(1) is not None else t)
        if x and x + w > HELP_W:
            x, row = 0, row + 1
        if m.group(1) is not None:
            link_row = row
        x += w
    return row + (1 if x else 0), link_row


def problems(src, r, en):
    """List of problems with one translated block (raw tl text)."""
    jp = r['jp']
    p = []
    if en == '=':
        return p
    ok = HELP_ICONS if src == 'help' else SC_SYMBOLS if kind(src) == 'sc' else ''
    bad = sorted(set(ch for ch in en.replace('\\n', '') if not (0x20 <= ord(ch) < 0x7f or ch in ok)))
    if bad:
        p.append('non-ASCII: ' + ''.join(bad))
    if re.search(r'L1|R1', en):
        p.append('"L1"/"R1" become button icons')
    a = [c for c in jp_codes(jp) if not c.startswith('{I')]
    b = [c for c in CODES.findall(en) if not c.startswith('{I')]
    if kind(src) == 'mesfile' or src == 'help':
        if a != b and not (r.get('id') in MES_DROP_ARGS and a[:len(b)] == b):
            p.append('codes %s != jp %s' % (b, a))
    elif sorted(a) != sorted(b):
        p.append('codes %s != jp %s' % (b, a))
    width, limit = layout(src, r)
    nm = names(src)
    if kind(src) == 'sc':
        en = join_soft(en)
    if width:
        for line in wrap(en, width, nm).split('\n'):
            if px(line, nm) > width:
                p.append('line too wide (%d px): %s' % (px(line, nm), line))
        n = wrap(en, width, nm).count('\n') + 1
        if n > limit:
            p.append('%d lines > %d' % (n, limit))
    elif src == 'help':
        n, lr = help_rows(en)
        if n > HELP_ROWS:
            p.append('%d rows > %d' % (n, HELP_ROWS))
        if lr >= HELP_LINK_ROWS:
            p.append('link on row %d (only rows 0-%d are touchable)' % (lr, HELP_LINK_ROWS - 1))
    else:
        if '\\n' in en:
            p.append('no \\n here (one line or the game wraps)')
        jpx = sum(12 if ord(c) > 0x7f else 6 for c in jp)
        if limit == 1:
            jpx = max(jpx * 3 // 2, WIDTH['mesfile'])   # one-line labels: up to a dialogue line
        else:
            jpx = jpx * 3 // 2
        if px(en.replace('\\n', ' ')) > jpx:
            p.append('LONG: %d px > %d px' % (px(en), jpx))
    return p


def table(src, pseudo=False):
    """{id: game bytes} for every row of src (translated, shared, or Japanese)."""
    by_jp = {}
    for s in SRCS:
        tl = load(s)
        for r in rows(s):
            e = tl.get(str(r['id']))
            if e and e[0] != '=':
                by_jp.setdefault(r['jp'], (s, e[0]))
    tl = load(src)
    # test builds: TL_KEEP_JP=mesfile:86,87;sc0:001.0004 keeps those rows Japanese
    keep = set()
    for part in os.environ.get('TL_KEEP_JP', '').split(';'):
        if part.startswith(src + ':'):
            keep.update(part[len(src) + 1:].split(','))
    out = {}
    for r in rows(src):
        width = layout(src, r)[0]
        rid = str(r['id'])
        e = tl.get(rid)
        if rid in keep:
            e = ('=',)
        if e and e[0] != '=':
            en = e[0]
        elif not e and r['jp'] in by_jp:
            en = by_jp[r['jp']][1]
        elif pseudo and not e:
            en = pseudo_en(rid, r['jp'])
        else:
            out[rid] = encode(r['jp']) if src == 'help' else encode_jp(r['jp'])   # HELP: no codes
            continue
        if kind(src) == 'sc' and NAME_CODES.search(en):
            en, width = join_soft(en), None   # runtime word wrap with the real names
        en = wrap(en, width)
        if kind(src) == 'sc':
            en = en.replace('%', '%%')        # the engine runs SC text through printf ("100% of" -> octal)
        out[rid] = encode_en(en)
    return out


FILLER = ('the quick brown fox jumps over a lazy dog while sailors drink grog '
          'and the captain plots a course for distant ports ').split()


def pseudo_en(rid, jp):
    """Test text: same line count and roughly the width of the Japanese."""
    out = []
    for n, line in enumerate(jp.split('\n')):
        target = sum(12 if ord(ch) > 0x7f else 6 for ch in line) * 4 // 5
        s = rid if n == 0 else ''
        k = 0
        while True:
            w = FILLER[(len(rid) + n * 7 + k) % len(FILLER)]
            if px((s + ' ' + w).strip()) > target:
                break
            s = (s + ' ' + w).strip(); k += 1
        out.append(s or '.')
    codes = ''.join(c for c in jp_codes(jp) if c[0] in '%{' and not c.startswith('{I'))
    return (codes + ' ' if codes else '') + '\\n'.join(out)


def stats():
    for src in SRCS:
        tl = load(src)
        rs = rows(src)
        done = sum(1 for r in rs if str(r['id']) in tl)
        print('%-8s %5d/%5d' % (src, done, len(rs)))


def check(srcs):
    n = 0
    for src in srcs:
        tl = load(src)
        jp = {str(r['id']): r for r in rows(src)}
        for rid, (en, path, line) in tl.items():
            if rid not in jp:
                print('%s:%d: unknown id %s' % (path, line, rid)); n += 1; continue
            for p in problems(src, jp[rid], en):
                print('%s:%d: @%s %s' % (path, line, rid, p)); n += 1
        if kind(src) == 'sc' and tl:
            import build
            import ndspy.rom
            rom = ndspy.rom.NintendoDSRom.fromFile(os.path.join(ROOT, 'daikoukai_jidai_4.nds'))
            try:
                build.build_sc(rom.getFileByName('data/SC%s.DK4' % src[2]), table(src))
            except ValueError as e:
                print('%s: %s (shorten text in those events)' % (src, e)); n += 1
    print('%d problems' % n)
    return n


SPK_TABLE = 0x02120B80               # arm9 person table, 32 B per entry: given, family, middle name ptrs
VARIANTS = ['polite', 'polite', 'cheerful', 'girl', 'rough', 'old man', 'childish', 'gentleman']
_spk = {}


def speaker(spk, rid):
    """English speaker label for an SC row (for todo files)."""
    if rid.count('.') == 2:
        v = int(rid.split('.')[2])
        if spk is None:
            return 'choice %d' % (v + 1)
        return 'mate, %s' % VARIANTS[v]
    if spk is None or spk == 254:
        return 'no nameplate'
    if not _spk:
        import struct
        import arm9str
        import ndspy.rom
        rom = ndspy.rom.NintendoDSRom.fromFile(os.path.join(ROOT, 'daikoukai_jidai_4.nds'))
        tl, a9 = arm9str.translations(), rom.arm9
        for i in range(256):
            o = SPK_TABLE - 0x02000000 + 32 * i
            ptrs = struct.unpack_from('<2I', a9, o)
            names = [tl.get(x) for x in ptrs if x]
            _spk[i] = (names[0] + (' (%s)' % names[1] if i >= 82 and len(names) > 1 and names[1] else '')
                       if names and names[0] else 'mate')
    return _spk[spk]


def show(src, start=0, count=50, todo=False):
    tl = load(src)
    rs = rows(src)
    covered = set()
    if todo:      # rows whose Japanese already has a translation anywhere get it automatically
        for s in SRCS:
            t = tl if s == src else load(s)
            covered.update(x['jp'] for x in rows(s) if str(x['id']) in t)
    for r in rs[start:start + count]:
        if todo and (str(r['id']) in tl or r['jp'] in covered):
            continue
        w, n = layout(src, r)
        hint = ('%dpx x%d' % (w, n) if w and n != 1 else '%dpx, one line' % w if w else 'one line, no \\n' if n == 1 else 'no \\n, the game wraps'
                ) if src != 'help' else ''
        if kind(src) == 'sc':
            hint = speaker(r['spk'], rid=r['id']) + ', ' + hint
        print('@%s%s' % (r['id'], '    # ' + hint if hint else ''))
        print('  ' + r['jp'].replace('\n', '\\n'))


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'stats':
        stats()
    elif a[0] == 'check':
        sys.exit(1 if check(a[1:] or SRCS) else 0)
    elif a[0] == 'show':
        todo = '--todo' in a
        a = [x for x in a if x != '--todo']
        show(a[1], int(a[2]) if len(a) > 2 else 0, int(a[3]) if len(a) > 3 else 50, todo)
