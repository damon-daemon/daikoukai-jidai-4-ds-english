def decompress(d):
    """Nintendo LZ77 type 0x10."""
    if d[0] != 0x10: raise ValueError('not LZ10')
    size = d[1] | d[2] << 8 | d[3] << 16
    out = bytearray(); i = 4
    while len(out) < size:
        flags = d[i]; i += 1
        for b in range(8):
            if len(out) >= size: break
            if flags & (0x80 >> b):
                v = d[i] << 8 | d[i + 1]; i += 2
                n = (v >> 12) + 3; disp = (v & 0xFFF) + 1
                for _ in range(n): out.append(out[-disp])
            else:
                out.append(d[i]); i += 1
    return bytes(out)


def compress(d):
    """Nintendo LZ77 type 0x10 (greedy with one-step lazy matching, window 4096, len 3..18)."""
    d = bytes(d)
    n = len(d)
    out = bytearray([0x10, n & 0xFF, n >> 8 & 0xFF, n >> 16 & 0xFF])
    heads = {}

    def best(i):
        bl, bd = 0, 0
        cand = heads.get(d[i:i + 3], ())
        for j in reversed(cand[-64:]):          # bounded chain: long zero runs are common
            if i - j > 0x1000:
                break
            m = 3
            while m < 18 and i + m < n and d[j + m] == d[i + m]:
                m += 1
            if m > bl:
                bl, bd = m, i - j
                if m == 18:
                    break
        return bl, bd

    def add(i):
        if i + 3 <= n:
            heads.setdefault(d[i:i + 3], []).append(i)

    i = 0
    while i < n:
        fpos = len(out); out.append(0)
        flags = 0
        for b in range(8):
            if i >= n:
                break
            bl, bd = best(i) if i + 3 <= n else (0, 0)
            if bl >= 3 and i + 4 <= n:
                add(i)
                nl, _ = best(i + 1) if i + 4 <= n else (0, 0)
                heads[d[i:i + 3]].pop()
                if nl > bl + 1:
                    bl = 0
            if bl >= 3:
                flags |= 0x80 >> b
                v = (bl - 3) << 12 | (bd - 1)
                out += bytes([v >> 8, v & 0xFF])
                for k in range(bl):
                    add(i + k)
                i += bl
            else:
                out.append(d[i]); add(i); i += 1
        out[fpos] = flags
    out += b'\0' * (-len(out) % 4)
    return bytes(out)
