"""Find footer button tables (6 x char*: L R X Y B A, 0 = no button) in arm9 and lay them out
like 0x020ca890 with the English labels: buttons whose x goes negative are not drawn."""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import font  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
B = 0x02000000
ICON, GAP, RIGHT = 12, 8, 0xfd           # 0x0211b5cc, per-button gap, start x


def main():
    a9 = open(os.path.join(ROOT, 'work/arm9.bin'), 'rb').read()
    rows = {int(r['addr'], 16): r for r in json.load(open(os.path.join(ROOT, 'script/arm9.json')))}
    tl = dict(l.rstrip('\n').split('\t', 1) for l in open(os.path.join(ROOT, 'tl/arm9.txt')) if '\t' in l)
    labels = {a for a, r in rows.items() if 0x0211b4e4 <= a <= 0x0211b5ec}   # footer label pool
    for o in range(0, len(a9) - 24, 4):
        ptrs = struct.unpack_from('<6I', a9, o)
        if not any(p in labels for p in ptrs):
            continue
        if not all(p == 0 or p in rows or (B <= p < B + len(a9) and a9[p - B] == 0) for p in ptrs):
            continue
        x, out = RIGHT, []
        for p in reversed(ptrs):
            if p == 0:
                continue
            en = tl.get('%08X' % p, '') if p in rows else ''
            w = font.width(en)
            x -= ICON
            if w:
                x -= ((w + 1) & ~1) + 2
            out.append('%s@%d' % (en or '-', x))
            x -= GAP
        bad = any(int(s.rsplit('@', 1)[1]) < 0 for s in out)
        if bad or '-v' in sys.argv:
            print('%08x %s %s' % (B + o, 'OVER' if bad else 'ok  ', ' | '.join(reversed(out))))


if __name__ == '__main__':
    main()
