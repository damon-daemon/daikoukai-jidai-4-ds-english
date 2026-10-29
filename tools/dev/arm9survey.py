"""Survey SJIS strings in arm9: which are pointer-referenced, which sit in records/arrays.

usage: arm9survey.py [arm9.bin]   (default work/arm9.bin; base 0x02000000, static section only)
"""
import collections
import struct
import sys

BASE, END = 0x02000000, 0x02170340
d = open(sys.argv[1] if len(sys.argv) > 1 else 'work/arm9.bin', 'rb').read()[:END - BASE]


def is_sjis(b):
    i = 0
    while i < len(b):
        c = b[i]
        if c == 0x0a or 0x20 <= c < 0x7f or 0xa1 <= c <= 0xdf:
            i += 1
        elif (0x81 <= c <= 0x9f or 0xe0 <= c <= 0xfc) and i + 1 < len(b) and 0x40 <= b[i + 1] <= 0xfc and b[i + 1] != 0x7f:
            i += 2
        else:
            return False
    return True


# candidate strings: maximal runs ending in NUL containing at least one SJIS double-byte char
strs = []
i = 0x12f000
while i < len(d):
    j = d.find(b'\0', i)
    if j < 0:
        break
    s = d[i:j]
    if s and is_sjis(s) and any(c >= 0x81 for c in s):
        strs.append((BASE + i, s))
    i = j + 1

refs = collections.Counter()
for k in range(0, len(d) - 3, 4):
    v = struct.unpack_from('<I', d, k)[0]
    if 0x0212f000 <= v < END:
        refs[v] += 1

pref = [(a, s) for a, s in strs if refs[a]]
unref = [(a, s) for a, s in strs if not refs[a]]
print(f'{len(strs)} strings, {sum(len(s) for _, s in strs)} B; pointer-referenced {len(pref)} '
      f'({sum(len(s) for _, s in pref)} B); unreferenced {len(unref)} ({sum(len(s) for _, s in unref)} B)')
# group unreferenced strings into runs with a constant stride (record tables)
runs, cur = [], [unref[0]] if unref else []
for prev, nxt in zip(unref, unref[1:]):
    if nxt[0] - prev[0] <= 64:
        cur.append(nxt)
    else:
        runs.append(cur)
        cur = [nxt]
runs.append(cur)
print('\nunreferenced runs (start, count, strides, sample):')
for r in runs:
    if len(r) < 3:
        continue
    strides = collections.Counter(b[0] - a[0] for a, b in zip(r, r[1:])).most_common(2)
    print(f'  {r[0][0]:#x} n={len(r):4d} strides={strides} '
          f'{r[0][1].decode("cp932", "replace")} / {r[-1][1].decode("cp932", "replace")}')
