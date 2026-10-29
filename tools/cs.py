"""CS event-script bytecode (data/SC0-3.DK4 entries), from the arm9 interpreter at 0x0202a510.

Entry: "CS" 00 01, u32 size (bytes after the 8-byte header), then instructions.
Instruction: u16 LE w; group = w>>13, sub = (w>>8)&0x1f, imm = w&0xff. Always 2-aligned.
Lengths (handlers 0x0202a414 / a1d8 / 9aa0 / 99c8 / 9874 / 976c / 93b8):
  g0 sub0      4   end / return (u16 arg)
  g0 sub1-4    4   jump forward by u16 from end of instruction (1 always, 2/3/4 if result==0/1/2)
  g1 sub1/2    6/8 choice menu, 2/3 options: u16 off[k] (rel. +6/+8); option strings follow;
                   length ends after the LAST option's string (so keep options in order)
  g2 sub0      6   message: u16 src (0xffff = inline), u16 (hi byte = speaker); inline -> NUL string, align 2
  g2 sub1     20   variant message (8 variants): u16 off[8] (rel. +20), u16 (hi byte = speaker);
                   strings follow; length ends after the farthest one
  Option/variant lists: w&0xff is a mask, bit 7-i set = item i comes from a string table
  (off[i] is then a table index, 0x0202a154 / 0x0202a30c), else it is inline.
  g2 sub5      6;  g2 sub6 4;  g2 sub8 4 (+4 if u16[1] bit15 clear)
  g4 sub0      4 (+4 if u16[1]==0xffff);  g4 sub1 4
  g5 sub0      4 (+4 if u16[1]==0xffff)
  g6 sub3      4
  everything else 2
"""
import struct

JUMPS = {(0, 1), (0, 2), (0, 3), (0, 4)}


def cstr(d, p):
    e = d.index(b'\0', p)
    return d[p:e]


def align2(n):
    return (n + 1) & ~1


def options(d, p, w, k, base, info, last):
    """Instruction with k option/variant strings at p+base+off[i] (offsets u16 at p+2)."""
    mask = w & 0xff
    offs = [struct.unpack_from('<H', d, p + 2 + 2 * i)[0] for i in range(k)]
    info['mask'], info['offs'], info['base'] = mask, offs, base
    strs, far = [], None
    for i in range(k):
        if mask >> (7 - i) & 1:
            continue
        t = cstr(d, p + base + offs[i])
        strs.append((p + base + offs[i], t))
        if far is None or offs[i] >= far[0] or (last and i == k - 1):
            far = (offs[i], len(t))
    if last:
        assert not mask & 1 << (8 - k), 'last option from table'
    info['strs'] = strs
    return base + (align2(far[0] + far[1] + 1) if far else 0), info


def decode(d, p):
    """Return (length, info) for the instruction at d[p:]. info: dict with kind and fields."""
    w = struct.unpack_from('<H', d, p)[0]
    g, s = w >> 13, (w >> 8) & 0x1f
    u = lambda k: struct.unpack_from('<H', d, p + k)[0]
    info = {'w': w, 'g': g, 's': s}
    if g == 0:
        if s == 0:
            # the final end-of-script instruction may stop at the size limit without its arg
            return (2 if p + 4 > len(d) or d[p + 2:p + 4] == b'' else 4), info
        if s in (1, 2, 3, 4):
            info['jump'] = u(2)
            return 4, info
        return 2, info
    if g == 1 and s in (1, 2):
        k = s + 1
        return options(d, p, w, k, 2 + 2 * k, info, last=True)
    if g == 2:
        if s == 0:
            if u(2) == 0xffff:
                t = cstr(d, p + 6)
                info['strs'] = [(p + 6, t)]
                info['speaker'] = d[p + 5]
                return align2(6 + len(t) + 1), info
            info['ref'] = u(2)
            return 6, info
        if s == 1:
            info['speaker'] = d[p + 0x13]
            return options(d, p, w, 8, 20, info, last=False)
        if s == 5:
            return 6, info
        if s == 6:
            return 4, info
        if s == 8:
            return (4 if u(2) & 0x8000 else 8), info
        return 2, info
    if g == 4:
        if s == 0:
            return (8 if u(2) == 0xffff else 4), info
        if s == 1:
            return 4, info
        return 2, info
    if g == 5 and s == 0:
        return (8 if u(2) == 0xffff else 4), info
    if g == 6 and s == 3:
        return 4, info
    if g == 7:
        raise ValueError('invalid group 7 at %#x: %04x' % (p, w))
    return 2, info


def parse(entry):
    """entry: bytes of one CS entry (with header). Returns list of (pos, len, info)."""
    assert entry[:2] == b'CS' and entry[3] == 1, entry[:4]  # SC3 has version byte 01
    size = struct.unpack_from('<I', entry, 4)[0]
    end = 8 + size
    p, out = 8, []
    while p < end:
        n, info = decode(entry[:end], p)
        out.append((p, n, info))
        p += n
    return out, end


def ilnk(d):
    assert d[:4] == b'ILNK'
    n = struct.unpack_from('<I', d, 4)[0]
    off = struct.unpack_from('<%dI' % (n + 1), d, 8)
    return [d[off[i]:off[i + 1]] for i in range(n)]


def build_ins(entry, p, n, info, new):
    """Re-encode one instruction with its inline strings replaced by `new` (list of bytes, same
    order as info['strs'])."""
    if info['g'] == 2 and info['s'] == 0 and 'strs' in info:
        b = entry[p:p + 6] + new[0] + b'\0'
    elif 'offs' in info:
        base = info['base']
        head = bytearray(entry[p:p + base])
        body, placed, k = b'', {}, 0
        dedupe = info['g'] == 2      # choices: length is taken from the last option, keep order
        for i in range(len(info['offs'])):
            if info['mask'] >> (7 - i) & 1:
                continue
            t = new[k]; k += 1
            if not (dedupe and t in placed):
                placed[t] = len(body)
                body += t + b'\0'
                body += b'\0' * (len(body) & 1)
            struct.pack_into('<H', head, 2 + 2 * i, placed[t])
        b = bytes(head) + body
    else:
        return entry[p:p + n]
    return b + b'\0' * (len(b) & 1)


def rebuild(entry, repl):
    """repl: {instruction pos: [new bytes per inline string]}. Returns the new CS entry with jump
    offsets and the size field fixed; entry padded to 4 like the original ILNK data."""
    ins, end = parse(entry)
    out, newpos = [], {}
    q = 8
    for p, n, info in ins:
        newpos[p] = q
        b = build_ins(entry, p, n, info, repl[p]) if p in repl else entry[p:p + n]
        out.append(b)
        q += len(b)
    newpos[end] = q
    for k, (p, n, info) in enumerate(ins):
        if 'jump' in info:
            tgt = newpos[p + n + info['jump']]
            b = bytearray(out[k])
            rel = tgt - (newpos[p] + 4)
            assert 0 <= rel < 0x10000, rel
            struct.pack_into('<H', b, 2, rel)
            out[k] = bytes(b)
    body = b''.join(out)
    hdr = entry[:4] + struct.pack('<I', len(body))
    data = hdr + body
    return data + b'\0' * (-len(data) % 4)


def build_ilnk(entries):
    n = len(entries)
    hdr = 8 + 4 * (n + 1)
    offs, pos = [], hdr
    for e in entries:
        offs.append(pos); pos += len(e) + (-len(e) % 4)
    offs.append(pos)
    out = b'ILNK' + struct.pack('<I', n) + struct.pack('<%dI' % (n + 1), *offs)
    out += b'\0' * (hdr - len(out))
    for e in entries:
        out += e + b'\0' * (-len(e) % 4)
    return out
