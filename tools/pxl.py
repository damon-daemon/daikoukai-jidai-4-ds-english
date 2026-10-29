"""Koei DK4 .pxl images: header u8 bpp (4/8), u8 flag, u16 0, u32 w (in u16 units: stride = 2*w bytes),
u32 h, u32 palette offset (0x14), u32 pixel offset; palette BGR555 (16 or 256), pixels linear,
4bpp low nibble = left pixel."""
import struct

from PIL import Image


def parse(data):
    bpp, flag = data[0], data[1]
    w, h, po, do = struct.unpack_from('<4I', data, 4)
    pw = w * 16 // bpp
    pal = []
    for i in range((do - po) // 2):
        c = struct.unpack_from('<H', data, po + 2 * i)[0]
        pal.append(((c & 31) * 255 // 31, (c >> 5 & 31) * 255 // 31, (c >> 10 & 31) * 255 // 31))
    px = data[do:do + w * 2 * h]
    if bpp == 4:
        idx = bytearray()
        for b in px:
            idx += bytes((b & 15, b >> 4))
    else:
        idx = bytes(px)
    return dict(bpp=bpp, flag=flag, w=pw, h=h, pal=pal, idx=bytes(idx), extra=len(data) - do - w * 2 * h)


def to_image(p, pal=0):
    if p['bpp'] == 16:
        im = Image.new('RGB', (p['w'], p['h']))
        im.putdata([((c & 31) * 255 // 31, (c >> 5 & 31) * 255 // 31, (c >> 10 & 31) * 255 // 31)
                    for c in struct.unpack('<%dH' % (p['w'] * p['h']), p['idx'][:p['w'] * p['h'] * 2])])
        return im
    n = 1 << p['bpp']
    im = Image.new('P', (p['w'], p['h']))
    flat = []
    for c in p['pal'][pal * n:(pal + 1) * n]:
        flat += c
    im.putpalette(flat + [0] * (768 - len(flat)))
    im.putdata(p['idx'][:p['w'] * p['h']])
    return im


def pal555(data, off, n):
    out = []
    for i in range(n):
        c = struct.unpack_from('<H', data, off + 2 * i)[0]
        out.append(((c & 31) * 255 // 31, (c >> 5 & 31) * 255 // 31, (c >> 10 & 31) * 255 // 31))
    return out


def ilnk(data):
    n = struct.unpack_from('<I', data, 4)[0]
    o = struct.unpack_from('<%dI' % (n + 1), data, 8)
    return [data[o[i]:o[i + 1]] for i in range(n)]


def parse_blocks(e):
    """GRP archive entry type 0x10: u32 0x10, u32 fmt (8 = 4bpp, 9 = 8bpp), u32 12 + palette bytes,
    u16 ?, u16 ?, u16 colors, u16 blocks; palette; blocks: u32 size, u16 x, u16 y, u16 w (u16 units),
    u16 h, linear pixels."""
    typ, fmt, po = struct.unpack_from('<3I', e, 0)
    a, b, ncol, nblk = struct.unpack_from('<4H', e, 12)
    bpp = 4 if fmt == 8 else 8
    pal = pal555(e, 20, (po - 12) // 2)
    p = 8 + po
    blocks = []
    for _ in range(nblk):
        size, x, y, w, h = struct.unpack_from('<I4H', e, p)
        raw = e[p + 12:p + 12 + w * 2 * h]
        if bpp == 4:
            idx = bytearray()
            for v in raw:
                idx += bytes((v & 15, v >> 4))
        else:
            idx = raw
        blocks.append(dict(bpp=bpp, w=w * 16 // bpp, h=h, x=x, y=y, idx=bytes(idx), pal=pal, off=p))
        p += size
    return dict(typ=typ, fmt=fmt, a=a, b=b, ncol=ncol, blocks=blocks, end=p, size=len(e))
