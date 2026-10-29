"""Japanese strings in arm9 (names, UI, format strings): export, check, apply.

The pool 0x02119000..0x02170340 (footer button labels at 0x0211b4e4, the rest from 0x0212f000) holds ~2500 NUL-terminated SJIS strings; nearly every one is the
target of a pointer word (literal pools, pointer tables) somewhere in arm9 or its overlay, so the
strings are found by scanning for words pointing into the pool (tools/dev/arm9survey.py: the
unreferenced remainder is byte noise).

  export:  .venv/bin/python tools/arm9str.py export [clean.nds]  -> script/arm9.json
           rows {addr, jp, cap, refs: [[section, addr], ...]}; cap = bytes available
           without the NUL (own bytes + NUL padding up to the next string or 4-byte boundary)
  check:   .venv/bin/python tools/arm9str.py check     translated count, strings over their slot,
           strings wider (px) than the Japanese
  todo:    .venv/bin/python tools/arm9str.py todo [N]  untranslated rows grouped by the pointer
           table that references them -> work/arm9_todo/NN.txt (~N lines per chunk, default 500)
  glossary: .venv/bin/python tools/arm9str.py glossary  -> work/glossary.tsv (JP<TAB>EN, unique)
  apply(code): writes tl/arm9.txt into an ndspy MainCodeFile. A string that fits is written in
           place; a longer one moves into space freed in the pool (or extra spans passed in) and
           its pointers are updated.

tl/arm9.txt (English only): `ADDR<TAB>English` per line, `\\n` = newline, `#` = comment.
An untranslated string takes the translation of an identical Japanese string elsewhere in the pool.
"""
import json
import os
import struct
import sys

import ndspy.rom

sys.path.insert(0, os.path.dirname(__file__))
from extract import decode, encode  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LO, HI = 0x02119000, 0x02170340       # 0x02119000.. = footer button labels (S10)
JSON = os.path.join(ROOT, 'script', 'arm9.json')
TL = os.path.join(ROOT, 'tl', 'arm9.txt')


def _sjis_text(b):
    i, wide = 0, False
    while i < len(b):
        c = b[i]
        if c == 0x0a or 0x20 <= c < 0x7f or 0xa1 <= c <= 0xdf:
            i += 1
        elif (0x81 <= c <= 0x9f or 0xe0 <= c <= 0xfc) and i + 1 < len(b) and 0x40 <= b[i + 1] <= 0xfc and b[i + 1] != 0x7f:
            i, wide = i + 2, True
        else:
            return False
    return wide


def export(rom_path):
    rom = ndspy.rom.NintendoDSRom.fromFile(rom_path)
    arm9 = rom.loadArm9()
    main = arm9.sections[0]
    base, blob = main.ramAddress, bytes(main.data)
    refs = {}

    def scan(name, data, start):
        for i in range(0, len(data) - 3, 4):
            v = struct.unpack_from('<I', data, i)[0]
            if LO <= v < HI:
                refs.setdefault(v, []).append([name, start + i])
    for i, s in enumerate(arm9.sections):
        scan('arm9' if i == 0 else 'arm9.%x' % s.ramAddress, bytes(s.data), s.ramAddress)
    for k, ov in rom.loadArm9Overlays().items():
        scan('ov%d' % k, ov.data, ov.ramAddress)
    starts = sorted(refs)
    rows = []
    for n, a in enumerate(starts):
        o = a - base
        e = blob.index(b'\0', o)
        if not _sjis_text(blob[o:e]):
            continue
        nxt = starts[n + 1] - base if n + 1 < len(starts) else len(blob)
        k = e
        while k < nxt and blob[k] == 0:
            k += 1
        # NUL padding is ours only up to the next referenced string; otherwise only up to the
        # 4-byte boundary (what follows may be a struct field that happens to be 0)
        end = k if k == nxt else min(k, (e + 4) & ~3)
        rows.append({'addr': '%08X' % a, 'jp': decode(blob[o:e]), 'cap': end - o - 1, 'refs': refs[a]})
    os.makedirs(os.path.dirname(JSON), exist_ok=True)
    json.dump(rows, open(JSON, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print('%d strings -> %s' % (len(rows), JSON))


def load_tl(path=TL):
    out = {}
    if not os.path.exists(path):
        return out
    for n, line in enumerate(open(path, encoding='utf-8'), 1):
        line = line.rstrip('\n')
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        if '\t' not in line:
            raise ValueError('%s:%d: missing tab' % (path, n))
        k, v = line.split('\t', 1)
        out[int(k, 16)] = v.replace('\\n', '\n')
    return out


def translations():
    """{addr: English} incl. the identical-Japanese fallback."""
    tl = load_tl()
    rows = json.load(open(JSON, encoding='utf-8'))
    by_jp = {}
    for r in rows:
        a = int(r['addr'], 16)
        if a in tl:
            by_jp.setdefault(r['jp'], tl[a])
    out = {}
    for r in rows:
        a = int(r['addr'], 16)
        if a in tl or r['jp'] in by_jp:
            out[a] = tl.get(a, by_jp.get(r['jp']))
    return out


# Sea mode help panels, drawn by the overlay renderer (patch_arm9.apply_modehelp): 2 chars per
# 12 px cell into a strip whose cells each mode's BG map shows at fixed places, made to fit the
# Japanese (seen in melonDS with numbered cells): title row = cells 0.. from x 56, body rows =
# (first cell, visible cells). tl: "Title\nBody" (title centred), or body only.
_INFO = (13, [(16, 16), (32, 18), (56, 16)])
_SEARCH = (13, [(16, 16), (32, 18), (56, 16), (72, 18), (96, 18), (120, 18), (144, 5)])
_WAR = (16, [(16, 20), (40, 16), (56, 20), (80, 20), (104, 20)])
MODEHELP = {0x02147540: _SEARCH, 0x0215F72C: _SEARCH, 0x02147674: _WAR, 0x0215F870: _WAR,
            0x02147778: _INFO, 0x02147828: _INFO,
            0x02147F34: (0, [(0, 8), (8, 8)])}       # "no one to fight" bubble, bottom screen


def modehelp_layout(s, spec):
    title_cells, rows = spec
    paras = s.split('\n')
    out = [' '] * (2 * (rows[-1][0] + rows[-1][1]))
    if title_cells:
        out[:2 * title_cells] = paras.pop(0).center(2 * title_cells)
    words = ' '.join(paras).split(' ')
    for start, n in rows:
        cur = ''
        while words and len((cur + ' ' + words[0]).strip()) <= 2 * n:
            cur = (cur + ' ' + words.pop(0)).strip()
        out[2 * start:2 * start + len(cur)] = cur
    assert not words and len(out) % 2 == 0, (s, words)
    # fill every mapped cell (cells left undrawn keep stale pixels); whole pairs only, since
    # an odd tail would swallow the NUL
    return ''.join(out)


def plan():
    """[(addr, bytes, cap, refs, jp)] for every translated string."""
    tl = translations()
    out = []
    for r in json.load(open(JSON, encoding='utf-8')):
        a = int(r['addr'], 16)
        if a in tl:
            en = modehelp_layout(tl[a], MODEHELP[a]) if a in MODEHELP else tl[a]
            out.append((a, encode(en), r['cap'], r['refs'], r['jp']))
    return out


def jp_width(s):
    """Pixel width of the Japanese as the stock engine draws it (1-byte chars 6 px)."""
    return max(sum(6 if ord(ch) < 0x80 or 0xff61 <= ord(ch) <= 0xff9f else 12 for ch in line)
               for line in s.split('\n'))


def en_width(s):
    import font
    return max(font.width(line) for line in s.split('\n'))


def apply(code, extra=()):
    """Write tl/arm9.txt into code. extra: additional free [lo, hi) spans (e.g. a new section).
    Returns (#in place, #moved, free spans left)."""
    from patch_arm9 import Arm9
    a9 = Arm9(code)
    items = plan()
    fits = [it for it in items if len(it[1]) <= it[2]]
    moves = [it for it in items if len(it[1]) > it[2]]
    for a, b, cap, refs, jp in fits:
        a9.write(a, b + b'\0' * (cap + 1 - len(b)))
    spans = [(a + len(b) + 1, a + cap + 1) for a, b, cap, refs, jp in fits if cap > len(b)]
    spans += [(a, a + cap + 1) for a, b, cap, refs, jp in moves]
    free = []
    for lo, hi in sorted(spans):
        if free and free[-1][1] == lo:
            free[-1][1] = hi
        else:
            free.append([lo, hi])
    free += [list(g) for g in extra]
    for a, b, cap, refs, jp in sorted(moves, key=lambda it: -len(it[1])):
        need = len(b) + 1
        cand = [g for g in free if g[1] - g[0] >= need]
        if not cand:
            raise ValueError('%08X %r: no free space for %d bytes' % (a, jp, need))
        g = min(cand, key=lambda g: g[1] - g[0])
        dst = g[0]
        g[0] += need
        a9.write(dst, b + b'\0')
        for sec, p in refs:
            if sec.startswith('ov'):
                raise ValueError('%08X %r: moved but referenced from an overlay' % (a, jp))
            assert struct.unpack('<I', a9.read(p, 4))[0] == a
            a9.write(p, struct.pack('<I', dst))
    for g in free:
        if LO <= g[0] < HI:
            a9.write(g[0], b'\0' * (g[1] - g[0]))     # no stale Japanese left behind
    return len(fits), len(moves), [g for g in free if g[1] > g[0]]


def check():
    items = plan()
    rows = json.load(open(JSON, encoding='utf-8'))
    over = [(a, jp, len(b), cap) for a, b, cap, refs, jp in items if len(b) > cap]
    print('%d/%d translated, %d over slot (%d B extra)' % (
        len(items), len(rows), len(over), sum(n - cap for _, _, n, cap in over)))
    for a, jp, n, cap in over:
        print('  %08X %d>%d %s' % (a, n, cap, jp.replace('\n', '\\n')))
    tl = translations()
    wide = [(a, jp, en_width(tl[a]), jp_width(jp)) for a, b, cap, refs, jp in items
            if '%' not in jp and en_width(tl[a]) > jp_width(jp)]
    print('%d wider than the Japanese (px; may be fine, check the screen)' % len(wide))
    for a, jp, w, jw in wide:
        print('  %08X %d>%d %s = %s' % (a, w, jw, jp.replace('\n', '\\n'), tl[a].replace('\n', '\\n')))


def _groups(rows):
    """rows grouped by pointer table: runs of reference addresses <= 0x40 apart, in table order."""
    refs = sorted((p, r['addr']) for r in rows for sec, p in r['refs'][:1])
    groups, prev = [], None
    for p, a in refs:
        if prev is None or p - prev > 0x40:
            groups.append([])
        groups[-1].append(a)
        prev = p
    return groups


def todo(n=500):
    rows = json.load(open(JSON, encoding='utf-8'))
    by = {r['addr']: r for r in rows}
    tl = translations()
    out_dir = os.path.join(ROOT, 'work', 'arm9_todo')
    os.makedirs(out_dir, exist_ok=True)
    for f in os.listdir(out_dir):
        os.remove(os.path.join(out_dir, f))
    chunks, cur, seen = [], [], set()
    for g in _groups(rows):
        lines = []
        for a in g:
            if int(a, 16) in tl or a in seen:
                continue
            seen.add(a)
            r = by[a]
            lines.append('%s\t%d\t%s' % (a, jp_width(r['jp']), r['jp'].replace('\n', '\\n')))
        if not lines:
            continue
        if cur and len(cur) + len(lines) > n:
            chunks.append(cur)
            cur = []
        cur.append('# --- table @%s (%d) ---' % ('%08X' % by[g[0]]['refs'][0][1], len(g)))
        cur += lines
    if cur:
        chunks.append(cur)
    for i, c in enumerate(chunks):
        open(os.path.join(out_dir, '%02d.txt' % i), 'w', encoding='utf-8').write('\n'.join(c) + '\n')
    print('%d chunks, %d rows -> %s' % (len(chunks), sum(1 for c in chunks for l in c if l[0] != '#'), out_dir))


def glossary():
    rows = json.load(open(JSON, encoding='utf-8'))
    tl = translations()
    seen, out = set(), []
    for r in rows:
        a = int(r['addr'], 16)
        if a in tl and r['jp'] not in seen and '%' not in r['jp'] and '\n' not in r['jp']:
            seen.add(r['jp'])
            out.append('%s\t%s' % (r['jp'], tl[a]))
    path = os.path.join(ROOT, 'work', 'glossary.tsv')
    open(path, 'w', encoding='utf-8').write('\n'.join(out) + '\n')
    print('%d entries -> %s' % (len(out), path))


if __name__ == '__main__':
    if sys.argv[1] == 'export':
        export(sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'daikoukai_jidai_4.nds'))
    elif sys.argv[1] == 'check':
        check()
    elif sys.argv[1] == 'todo':
        todo(int(sys.argv[2]) if len(sys.argv) > 2 else 500)
    elif sys.argv[1] == 'glossary':
        glossary()
