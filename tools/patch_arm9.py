"""ARM9 patches: variable-width half-width (ASCII) font for English text.

Engine (notes/text_formats.md "Text engine"):
- String drawer 0x020d1604 draws SJIS via the ITCM blitter (+12 px) and 1-byte chars via
  0x020d16b4 (6 columns x 11 rows from the half-width font 0x02125a60, +6 px).
- Layout 0x020d5404 advances its pen by the cell width (6) per 1-byte char; the text-box draw
  vfunc 0x020d4da8 pairs 1-byte chars into one 12 px cell.
- Widths of strings for centring/right-aligning: strlen * 6 at ~30 sites.

Patches:
- New glyphs (tools/font.py) over the stock half-width font, same format.
- Code + width table in the ITCM gap 0x01ff9b20..0x01ffa000 (the ITCM autoload section grows).
- Drawer and layout advance by the char's width; autowrap tests the char's real width and
  wraps 1-byte text at word boundaries (the stock one breaks anywhere).
- Text-box pairing off: 1-byte chars are drawn one by one at their own pen position.
- strlen also stores the string's pixel width (LASTW); the `mul` of each strlen*6 (or *12/2)
  site loads LASTW instead.
- Inline codes F?/I? (names, pronoun) move to control bytes 0x0e/0x0f (tl.CODE_F/CODE_I) so
  English F and I are plain letters; the build converts the codes in all MESFILE/SC text.
- Icon subclass: control bytes 0x1c/0x1d draw the L/R button icons (stock: "L1"/"R1" pairs,
  which no longer exist without pairing).
"""
import os
import hashlib, struct
import sys

from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM
from keystone import Ks, KS_ARCH_ARM, KS_MODE_ARM

sys.path.insert(0, os.path.dirname(__file__))
import font  # noqa: E402
import tl  # noqa: E402

ITCM = 0x01ff8000
ITCM_GAP_END = 0x01ffa000           # overlay 0 starts here
HW_FONT = 0x02125a60                # 94 x 11 B, chars 0x21-0x7E
STRLEN = 0x020ced28
DRAW_ADVANCE = 0x020d169c           # add r5, r5, #6        (char at [r7])
PAIR_BRANCHES = (0x020d4dc8, 0x020d4dd0)   # blo/bhi to the pairing path
LAYOUT_ADVANCE = 0x020d57e4         # ldr r2, [sp, #0x34]   (cell w; char at [sb-1])
WRAP_CHECK = 0x020d55f0             # add r0, r0, r7        (pen + 2 cells; char at [sb])
ICON_ASCII = 0x020ac118             # cmp ip, #0x4c ... "L1"/"R1" -> r4 = 4/5
ICON_DONE = 0x020ac144
HELP_LOOP = 0x0207ce9c              # HELP page renderer loop (42-column grid, pairs 1-byte chars)
HELP_END = 0x0207d050
HELP_LINK = 0x0207cbe4              # add link rect (obj, col, len, row; [sp] = target page)
LAYOUT = 0x020d5404
HELP_W = 252                        # 42 half-width columns
# ASCII-only format strings (not exported by arm9str) that need a space in English
FMT_PATCHES = {
    0x02135250: (b'%s%s\0', b'%s %s\0'),     # fleet label: owner + "Fleet 1" (cap 8)
    0x0215a46c: (b'%10s\0', b'%s\0'),         # amount dialog label (60 px), left-aligned
}
# small code patches. number -> string 0x020abf50 writes full-width digits (0x82, 0x4f + d)
# backwards: ASCII instead
CODE_PATCHES = {
    0x020abf9c: ('add r1, r5, #0x4f', 'add r1, r5, #0x30'),
    0x020abfa0: ('strb r1, [r0, #-1]', 'strb r1, [r0, #-1]!'),
    0x020abfac: ('strb lr, [r0, #-2]!', 'mov r0, r0'),
    # trade screen: the town name is drawn twice into one opaque cell, first centred with
    # 3 * char count (wrong for VWF, its first letter peeks out: "LLisbon"); keep the second
    0x020c135c: ('bl 0x20d5404', 'mov r0, r0'),
    # amount dialog (invest / contract): 残金 x 36 right-aligns it under the 60 px label
    0x020c6618: ('mov r0, #0x24', 'mov r0, #0'),
}
GUN_TYPES = 0x0213c192              # 6 x (u8 id, u8 power, char name[17]); inline, no pointers
# Refit cannon picker row: a 144 px line buffer shown as two 72 px rows. Stock: one
# "%-12s威力%s" (name padded to 12 bytes = 72 px) + 長射程 at x 108. Rewritten in place:
# name at x 0, then "Pwr %d" (arm9 0x02133140) at x 72, "Range+" (long range) at x 108 (a sprite seam: text crossing it gets a gap).
GUN_ROW = (0x02019988, 0x020199ec)
GUN_ROW_FMT, GUN_ROW_LONG = 0x02019a38, 0x02019a3c   # literal pool slots (string pointers)
GUN_ROW_SHA1 = '7447f4be6cbe62a6'                # stock bytes of GUN_ROW (sha1 prefix)
GUN_NAMES = ['Saker', 'Culverin', 'Pedrero', 'Cannon', 'Heavy Cannon', 'Carronade']
SHIPINFO_XY = (0x0211a210, 0x02150704)   # 2 copies of s16 (x, y) value positions, ship info panel
SHIPINFO_X = {3: (30, 46), 5: (166, 180), 13: (54, 62)}   # Water, Sailors, Durability: plates widened (gfx.py)
CATEGORY_NAME = 0x020c5ba0          # goods category id -> name (table 0x0211b444)
PLATE_CALL = 0x020be800             # prices screen: bl CATEGORY_NAME for the 36 px plates
PLATE_SHORT = {1: 'Season.', 9: 'Finery'}   # Seasoning, Fine Goods
# Text-texture cell tables: some screens draw their labels into one texture and show it through
# cells of 7 x s32 (flag, screen x, screen y, tex x, tex y, w, h); labels are drawn at (tex x,
# tex y) and cut to w, which fits the Japanese. Widened labels move to free texture space.
CELLS = {
    0x02159a64: {   # trade screen, top (256x96 texture, 46 cells)
        2: ((1, 16, 70, 136, 0, 36, 12), (1, 16, 70, 180, 60, 42, 12)),       # Expenses
        34: ((1, 16, 166, 120, 60, 24, 12), (1, 16, 166, 222, 60, 32, 12)),   # Status
        36: ((1, 116, 2, 0, 72, 24, 12), (1, 115, 2, 204, 72, 28, 12)),       # Trade (header)
        37: ((1, 54, 18, 24, 72, 24, 12), (1, 50, 18, 200, 48, 40, 12)),      # Balance (header)
        38: ((1, 170, 18, 48, 72, 48, 12), (1, 184, 18, 48, 72, 48, 12)),     # Ship (header)
    },
}
CODE_F = 0x0205397c                 # inline-code expander: cmp r1, #0x46 ('F' + I/A/O/U = name)
CODE_I = 0x02053a44                 #                       cmp r1, #0x49 ('I' + x = pronoun)

STOCK = {
    DRAW_ADVANCE: 'add r5, r5, #6',
    PAIR_BRANCHES[0]: 'blo 0x020d4e90',
    PAIR_BRANCHES[1]: 'bhi 0x020d4e90',
    LAYOUT_ADVANCE: 'ldr r2, [sp, #0x34]',
    WRAP_CHECK: 'add r0, r0, r7',
    STRLEN: 'ldrsb r1, [r0], #1',
    ICON_ASCII: 'cmp ip, #0x4c',
    HELP_LOOP: 'ldrb r0, [sl]',
    CODE_F: 'cmp r1, #0x46',
    CODE_I: 'cmp r1, #0x49',
}

_ks = Ks(KS_ARCH_ARM, KS_MODE_ARM)
_cs = Cs(CS_ARCH_ARM, CS_MODE_ARM)
_cs.detail = True


def asm(src, addr):
    return bytes(_ks.asm(src, addr)[0])


class Arm9:
    def __init__(self, code):
        self.code = code

    def _sec(self, addr, n):
        for s in self.code.sections:
            if s.ramAddress <= addr and addr + n <= s.ramAddress + len(s.data):
                return s
        raise KeyError(hex(addr))

    def read(self, addr, n):
        s = self._sec(addr, n)
        o = addr - s.ramAddress
        return bytes(s.data[o:o + n])

    def write(self, addr, data):
        s = self._sec(addr, len(data))
        o = addr - s.ramAddress
        if not isinstance(s.data, bytearray):
            s.data = bytearray(s.data)
        s.data[o:o + len(data)] = data

    def grow(self, ram, end):
        """Extend the section starting at ram (zero-filled) so it covers up to end."""
        s = [s for s in self.code.sections if s.ramAddress == ram][0]
        assert s.bssSize == 0
        s.data = bytearray(s.data) + bytes(end - ram - len(s.data))
        return ram + len(s.data)


def strlen_mul_sites(a):
    """(mul addr, dest reg, factor) for each `bl strlen` followed by mul with #3/#6/#0xc or cell w."""
    main = a.code.sections[0]
    data = bytes(main.data)
    sites = []
    for k in range(0, len(data) - 4, 4):
        w = struct.unpack_from('<I', data, k)[0]
        if w >> 24 != 0xeb:
            continue
        off = w & 0xffffff
        off -= (off & 0x800000) << 1
        if main.ramAddress + k + 8 + off * 4 != STRLEN:
            continue
        addr = main.ramAddress + k
        lenregs, halfregs, consts = {'r0'}, set(), {}
        for i in _cs.disasm(data[k + 4:k + 0x1c], addr + 4):
            ops = [x.strip() for x in i.op_str.split(',')]
            if i.mnemonic == 'mov' and ops[1] in lenregs:
                lenregs.add(ops[0])
            elif i.mnemonic == 'lsr' and ops[1] in lenregs and ops[2] == '#1':
                halfregs.add(ops[0])                # (len >> 1) * 12: footer buttons 0x020ca7a4
            elif i.mnemonic == 'mov' and ops[1].startswith('#'):
                consts[ops[0]] = int(ops[1][1:], 0)
            elif i.mnemonic == 'ldr' and addr == 0x020d52f8 and ops[0] == 'r1':
                consts['r1'] = 6                    # cell width from the font (centred layout)
            elif i.mnemonic == 'mul':
                d, x, y = ops
                if x in consts and y in lenregs:
                    x, y = y, x
                if x in lenregs and consts.get(y) in (6, 12):
                    sites.append((i.address, d, consts[y] // 6))
                elif x in lenregs and consts.get(y) == 3:
                    sites.append((i.address, d, -1))    # -1: len * 3 = half width (centring)
                elif {x, y} & halfregs and 12 in (consts.get(x), consts.get(y)):
                    sites.append((i.address, d, 0))     # 0: width rounded up to even (4bpp strip)
                break
            elif i.mnemonic.startswith('b') and i.mnemonic not in ('beq', 'bne'):
                break
    return sites


def apply(code):
    a = Arm9(code)
    for addr, src in STOCK.items():
        assert a.read(addr, 4) == asm(src, addr), f'unexpected arm9 at {addr:#x}'

    glyphs, widths = font.table()
    a.write(HW_FONT, glyphs)

    base = ITCM + len(a._sec(ITCM, 1).data)
    a.grow(ITCM, ITCM_GAP_END)
    widths_at = base
    lastw = base + 0x80
    t = lastw + 4
    blobs = {}

    def put(src):
        nonlocal t
        b = asm(src, t)
        blobs[t] = b
        at, t = t, t + len(b)
        return at

    # width lookup inline: r = width of byte in r (r < 0x80), else 6; scratch s
    def wid(r, s):
        return f'''
            ldr   {s}, ={widths_at:#x}
            cmp   {r}, #0x80
            ldrblo {r}, [{s}, {r}]
            movhs {r}, #6'''

    # strlen: r0 = length; LASTW = pixel width. Clobbers only r0-r2 like the stock one.
    strlen_w = t
    put(f'''
        push  {{r3, r4, lr}}
        ldr   r4, ={widths_at:#x}
        mov   r1, r0
        mov   r2, #0
    next:
        ldrb  r3, [r1], #1
        cmp   r3, #0
        beq   done
        cmp   r3, #0x81
        blo   one
        cmp   r3, #0xfc
        bhi   one
        ldrb  r3, [r1], #1
        cmp   r3, #0
        subeq r1, r1, #1
        add   r2, r2, #12
        b     next
    one:
        cmp   r3, #0x80
        movhs r3, #6
        ldrblo r3, [r4, r3]
        add   r2, r2, r3
        b     next
    done:
        ldr   r4, ={lastw:#x}
        str   r2, [r4]
        sub   r0, r1, r0
        sub   r0, r0, #1
        pop   {{r3, r4, pc}}
    ''')
    a.write(STRLEN, asm(f'b {strlen_w:#x}', STRLEN))

    # drawer: x += width(char)
    h = put(f'ldrb r0, [r7]\n{wid("r0", "r1")}\nadd r5, r5, r0\nbx lr')
    a.write(DRAW_ADVANCE, asm(f'bl {h:#x}', DRAW_ADVANCE))

    # layout (horizontal, 1-byte char): pen += width(char) when the cell is 6 px
    h = put(f'''
        ldr   r2, [sp, #0x34]
        cmp   r2, #6
        bxne  lr
        ldrb  r2, [sb, #-1]
        {wid("r2", "r0")}
        bx    lr''')
    a.write(LAYOUT_ADVANCE, asm(f'bl {h:#x}', LAYOUT_ADVANCE))

    # autowrap: wrap if right <= pen + (SJIS ? 12 : width - 1); r1 (right edge) is live.
    # Word wrap for 1-byte text: at the first letter after a space (not at line start) the
    # whole word is measured; a space itself never wraps (it may hang past the edge).
    h = put(f'''
        cmp   r7, #12
        bne   stock
        ldrb  r2, [sb]
        cmp   r2, #0x81
        blo   one
        cmp   r2, #0xfc
        bls   stock
    one:
        cmp   r2, #0x20
        bxeq  lr
        {'b single0' if os.environ.get('NOWW') else ''}
        push  {{r3, r4}}
        ldr   r3, [sl, #4]
        cmp   r0, r3
        ble   single
        ldrb  r3, [sb, #-1]
        cmp   r3, #0x20
        bne   single
        mov   r3, sb
        mov   r4, #0
    word:
        ldrb  r2, [r3], #1
        cmp   r2, #0x21
        blo   wdone
        cmp   r2, #0x80
        bhs   wdone
        {wid("r2", "ip")}
        add   r4, r4, r2
        b     word
    wdone:
        add   r0, r0, r4
        sub   r0, r0, #1
        pop   {{r3, r4}}
        bx    lr
    single:
        pop   {{r3, r4}}
    single0:
        ldrb  r2, [sb]
        {wid("r2", "ip")}
        add   r0, r0, r2
        sub   r0, r0, #1
        bx    lr
    stock:
        add   r0, r0, r7
        bx    lr''')
    a.write(WRAP_CHECK, asm(f'bl {h:#x}', WRAP_CHECK))

    # HELP renderer (0x0207ce1c): the stock loop lays text on a 42-column grid and draws
    # 1-byte chars in pairs (an odd run eats the NUL). New loop, same frame and registers:
    # sb = x px, r8 = row, sl = text, r4 = buf (sp+0x38), fp = body colour; layout obj at
    # sp+0x78 (pen x +0x9c, y +0xa0, colour +0xa8). Words wrap whole; spaces at a line
    # start are dropped; links {label:X} keep the stock rect call with col = x / 6.
    # Subroutines push lr, so their sp offsets are +4.
    help_loop = put(f'''
        add   r4, sp, #0x38
        mov   fp, #0xf
        mov   r0, #0xc
        str   r0, [sp, #8]
    next:
        ldrb  r0, [sl]
        cmp   r0, #0
        beq   end
        cmp   r0, #0xa
        beq   nlchar
        cmp   r0, #0x7b
        beq   link
        cmp   r0, #0x81
        blo   ascii
        cmp   r0, #0xfc
        bhi   ascii
        mov   r6, #12
        bl    fit
        ldrb  r0, [sl], #1
        strb  r0, [r4]
        ldrb  r0, [sl], #1
        strb  r0, [r4, #1]
        mov   r7, #2
        bl    drawbuf
        b     next
    ascii:
        cmp   r0, #0x20
        bne   word
        add   sl, sl, #1
        cmp   sb, #0
        beq   next
        ldr   r1, ={widths_at:#x}
        ldrb  r1, [r1, #0x20]
        add   sb, sb, r1
        b     next
    word:
        mov   r7, #0
        mov   r6, #0
        ldr   r2, ={widths_at:#x}
    wl:
        ldrb  r0, [sl, r7]
        cmp   r0, #0x21
        blo   wend
        cmp   r0, #0x80
        bhs   wend
        cmp   r0, #0x7b
        beq   wend
        ldrb  r1, [r2, r0]
        add   r6, r6, r1
        strb  r0, [r4, r7]
        add   r7, r7, #1
        cmp   r7, #60
        blo   wl
    wend:
        bl    fit
        add   sl, sl, r7
        bl    drawbuf
        b     next
    nlchar:
        add   sl, sl, #1
        str   fp, [sp, #0xa8]
        bl    newline
        b     next
    link:
        add   sl, sl, #1
        mov   r7, #0
        mov   r6, #0
        ldr   r2, ={widths_at:#x}
    ll:
        ldrb  r0, [sl, r7]
        cmp   r0, #0
        cmpne r0, #0x3a
        beq   lend
        strb  r0, [r4, r7]
        add   r7, r7, #1
        cmp   r0, #0x80
        ldrblo r1, [r2, r0]
        addlo r6, r6, r1
        blo   ll
        ldrb  r0, [sl, r7]
        strb  r0, [r4, r7]
        add   r7, r7, #1
        add   r6, r6, #12
        b     ll
    lend:
        bl    fit
        add   r0, sl, r7
        ldrb  r0, [r0, #1]
        str   r0, [sp]
        add   sl, sl, r7
        add   sl, sl, #3
        ldr   r0, =0xaab
        mul   r1, sb, r0
        lsr   r1, r1, #14
        add   r2, r6, #5
        mul   r2, r0, r2
        lsr   r2, r2, #14
        mov   r3, r8
        ldr   r0, [sp, #4]
        bl    {HELP_LINK:#x}
        ldr   r0, [sp, #8]
        str   r0, [sp, #0xa8]
        bl    drawbuf
        str   fp, [sp, #0xa8]
        b     next
    end:
        b     {HELP_END:#x}
    fit:
        cmp   sb, #0
        bxeq  lr
        add   r0, sb, r6
        cmp   r0, #{HELP_W}
        bxle  lr
    newline:
        mov   sb, #0
        add   r8, r8, #1
        bx    lr
    drawbuf:
        push  {{lr}}
        strb  r5, [r4, r7]
        mov   r0, #12
        mul   r1, r8, r0
        str   r1, [sp, #0xa4]
        str   sb, [sp, #0xa0]
        add   r0, sp, #0x7c
        mov   r1, r4
        bl    {LAYOUT:#x}
        add   sb, sb, r6
        pop   {{pc}}''')
    a.write(HELP_LOOP, asm(f'b {help_loop:#x}', HELP_LOOP))

    for addr in PAIR_BRANCHES:
        a.write(addr, asm('nop', addr))

    a.write(ICON_ASCII, asm(f'''
        cmp   ip, #{font.ICON_L}
        moveq r4, #4
        cmp   ip, #{font.ICON_R}
        moveq r4, #5
        b     {ICON_DONE:#x}''', ICON_ASCII))

    for addr, (old, new) in FMT_PATCHES.items():
        assert a.read(addr, len(old)) == old and len(new) <= (len(old) + 3) & ~3
        a.write(addr, new)

    for addr, (old, new) in CODE_PATCHES.items():
        assert a.read(addr, 4) == asm(old, addr), f'unexpected arm9 at {addr:#x}'
        a.write(addr, asm(new, addr))

    for tab in SHIPINFO_XY:
        for i, (x0, x1) in SHIPINFO_X.items():
            assert struct.unpack('<h', a.read(tab + 4 * i, 2))[0] == x0, f'ship info table? {tab:#x}'
            a.write(tab + 4 * i, struct.pack('<h', x1))

    for tab, cells in CELLS.items():
        for i, (old, new) in cells.items():
            assert struct.unpack('<7i', a.read(tab + 28 * i, 28)) == old, f'cell table? {tab:#x} #{i}'
            a.write(tab + 28 * i, struct.pack('<7i', *new))

    for i, name in enumerate(GUN_NAMES):
        at = GUN_TYPES + 19 * i
        assert a.read(at, 1)[0] == i, f'gun type table moved? {at:#x}'
        a.write(at + 2, name.encode('ascii').ljust(17, b'\0'))

    lo, hi = GUN_ROW
    assert hashlib.sha1(a.read(lo, hi - lo)).hexdigest().startswith(GUN_ROW_SHA1), 'gun row code?'
    src = f'''
        mov   r0, #0
        cmp   r8, #0
        str   r0, [sp, #0x78]
        str   r0, [sp, #0x7c]
        movne r0, #0xc
        moveq r0, #1
        str   r0, [sp, #0x84]
        mov   r1, r4
        add   r0, sp, #0x54
        bl    {LAYOUT:#x}
        mov   r0, #72
        str   r0, [sp, #0x78]
        ldrb  r2, [r4, #0x11]
        ldr   r1, [pc, #{{FMT}}]
        add   r0, sp, #0x54
        bl    0x20d5200
        cmp   sb, #1
        cmpne sb, #5
        bne   {hi:#x}
        ldr   r1, [pc, #{{LONG}}]
        mov   r3, #108
        str   r3, [sp, #0x78]
        add   r0, sp, #0x54
        bl    {LAYOUT:#x}'''
    lines = [l.strip() for l in src.strip().splitlines()]   # one instruction each: pc-relative pool loads
    for k, slot in (('{FMT}', GUN_ROW_FMT), ('{LONG}', GUN_ROW_LONG)):
        n = next(i for i, l in enumerate(lines) if k in l)
        lines[n] = lines[n].replace(k, '%#x' % (slot - (lo + 4 * n + 8)))
    b = asm('\n'.join(lines), lo)
    assert len(b) <= hi - lo, len(b)
    a.write(lo, b + asm('nop', 0) * ((hi - lo - len(b)) // 4))

    a.write(CODE_F, asm(f'cmp r1, #{tl.CODE_F:#x}', CODE_F))
    a.write(CODE_I, asm(f'cmp r1, #{tl.CODE_I:#x}', CODE_I))

    # strlen*6 sites: mul -> bl stub (rd = LASTW, 2*LASTW for *12/2, LASTW rounded up to even for k=0,
    # LASTW/2 for *3)
    stubs = {}
    sites = strlen_mul_sites(a)
    for addr, rd, k in sites:
        if (rd, k) not in stubs:
            stubs[rd, k] = put(f'ldr {rd}, ={lastw:#x}\nldr {rd}, [{rd}]\n'
                               + (f'lsl {rd}, {rd}, #1\n' if k == 2 else '')
                               + (f'lsr {rd}, {rd}, #1\n' if k == -1 else '')
                               + (f'add {rd}, {rd}, #1\nbic {rd}, {rd}, #1\n' if k == 0 else '') + 'bx lr')
        a.write(addr, asm(f'bl {stubs[rd, k]:#x}', addr))

    # prices screen category plates (36 px): short names for the two that don't fit
    shorts = {}
    for cat, name in PLATE_SHORT.items():
        shorts[cat] = t
        blobs[t] = name.encode('ascii') + b'\0'
        t = (t + len(blobs[t]) + 3) & ~3
    stub = put(''.join(f'cmp r0, #{cat}\nldreq r0, ={at:#x}\nbxeq lr\n' for cat, at in shorts.items())
               + f'b {CATEGORY_NAME:#x}')
    assert a.read(PLATE_CALL, 4) == asm(f'bl {CATEGORY_NAME:#x}', PLATE_CALL)
    a.write(PLATE_CALL, asm(f'bl {stub:#x}', PLATE_CALL))
    # culture area line: x = 36 - len(name) * 3 centres "<name>文化圏" in 108 px; the English
    # suffix " Culture Area" is 58 px -> x = 25 - LASTW/2
    assert a.read(0x020be9ec, 4) == asm('rsb r1, r1, #0x24', 0x020be9ec)
    a.write(0x020be9ec, asm('rsb r1, r1, #25', 0x020be9ec))

    # 0x0201a2e8: x = (18 - len) * 3 -> 54 - LASTW/2
    for addr, old, new in ((0x0201a2ec, 'rsb r2, r0, #0x12', f'bl {stubs["r2", -1]:#x}'),
                           (0x0201a2f4, 'mul r0, r2, r0', 'rsb r0, r2, #0x36')):
        assert a.read(addr, 4) == asm(old, addr), f'unexpected arm9 at {addr:#x}'
        a.write(addr, asm(new, addr))

    assert t <= ITCM_GAP_END, f'ITCM gap overflow: {t:#x}'
    a.write(widths_at, widths)
    for at, b in blobs.items():
        a.write(at, b)
    return {'itcm_used': (base, t), 'strlen_sites': sites, 'lastw': lastw, 'widths': widths_at}


# Name-entry keyboard (keys/popups are arm9 strings in tl/arm9.txt). The stock editor assumes
# 2-byte chars; the popups still hand it full-width SJIS (their lists are read 2 bytes at a
# time), so: insert maps full-width to ASCII (unmapped chars are dropped), delete and cursor
# moves step 1 byte, and the cursor x is the VWF width of the text before it.
KBD_INSERT_CALL = 0x020aed2c        # bl 0x020b08d8 (editor insert, r1 = 2-byte char)
KBD_INSERT = 0x020b08d8
KBD_CURX = 0x020b0bcc               # mul r2, r1, r2 (cursor bytes * cell w)
KBD_RANGES = 0x0215fe4c             # 50 x (u16 kanji lo, u16 hi, key*, variants*)
KBD_STOCK = {
    KBD_INSERT_CALL: f'bl {KBD_INSERT:#x}',
    KBD_CURX: 'mul r2, r1, r2',
    0x020b0a70: 'strbge r0, [r2, #-2]',     # delete at end: second byte
    0x020b0a84: 'cmp r1, #2',               # backspace in the middle
    0x020b0a90: 'sub r3, r2, #2',
    0x020b0ab8: 'sub r1, r1, #2',
    0x020b0ad4: 'ldrsb r0, [r2, #1]',       # delete at the start
    0x020b0ae0: 'ldrsb r0, [r2, #2]',
    0x020b0ae4: 'add r3, r2, #2',
    0x020b0b34: 'add r1, r1, #2',           # cursor right / left
    0x020b0b48: 'sub r1, r1, #2',
}
KBD_NEW = {
    0x020b0a70: 'nop',
    0x020b0a84: 'cmp r1, #1',
    0x020b0a90: 'sub r3, r2, #1',
    0x020b0ab8: 'sub r1, r1, #1',
    0x020b0ad4: 'ldrsb r0, [r2]',
    0x020b0ae0: 'ldrsb r0, [r2, #1]',
    0x020b0ae4: 'add r3, r2, #1',
    0x020b0b34: 'add r1, r1, #1',
    0x020b0b48: 'sub r1, r1, #1',
}
KBD_MAP = [(0x824f, '0', 10), (0x8260, 'A', 26), (0x8281, 'a', 26)] + [
    (c, ch, 1) for c, ch in ((0x8140, ' '), (0x8143, ','), (0x8144, '.'), (0x8166, "'"),
                             (0x817c, '-'), (0x8195, '&'), (0x8149, '!'), (0x8148, '?'),
                             (0x817b, '+'), (0x815e, '/'), (0x8196, '*'), (0x8146, ':'))]
KBD_SIZE = 0x100


def apply_kbd(code, at, lastw):
    """Keyboard patch with its code at [at, at + KBD_SIZE) (a grown ITCM span)."""
    a = Arm9(code)
    for addr, src in KBD_STOCK.items():
        assert a.read(addr, 4) == asm(src, addr), f'unexpected arm9 at {addr:#x}'
    for i in range(50):                      # no kanji in the popups
        a.write(KBD_RANGES + 12 * i, b'\0' * 4)
    table = b''.join(struct.pack('<HBB', c, ord(ch), n) for c, ch, n in KBD_MAP) + b'\0' * 4
    insert = at + len(table)
    ins = asm(f'''
        push  {{r4, lr}}
        ldrb  r2, [r1]
        ldrb  r3, [r1, #1]
        orr   r2, r3, r2, lsl #8
        ldr   ip, ={at:#x}
    next:
        ldr   r3, [ip], #4
        cmp   r3, #0
        popeq {{r4, pc}}
        lsl   r4, r3, #16
        sub   r4, r2, r4, lsr #16
        cmp   r4, r3, lsr #24
        bhs   next
        lsr   r3, r3, #16
        and   r3, r3, #0xff
        add   r3, r3, r4
        strb  r3, [r1]
        mov   r3, #0
        strb  r3, [r1, #1]
        pop   {{r4, lr}}
        b     {KBD_INSERT:#x}''', insert)
    curx = insert + len(ins)
    cur = asm(f'''
        push  {{r0, r1, r3, r4, lr}}
        add   r4, r5, #0x7c
        ldrb  r3, [r4, r1]
        mov   r2, #0
        strb  r2, [r4, r1]
        mov   r0, r4
        bl    {STRLEN:#x}
        ldr   r1, [sp, #4]
        strb  r3, [r4, r1]
        ldr   r2, ={lastw:#x}
        ldr   r2, [r2]
        pop   {{r0, r1, r3, r4, pc}}''', curx)
    assert len(table) + len(ins) + len(cur) <= KBD_SIZE
    a.write(at, table + ins + cur)
    a.write(KBD_INSERT_CALL, asm(f'bl {insert:#x}', KBD_INSERT_CALL))
    a.write(KBD_CURX, asm(f'bl {curx:#x}', KBD_CURX))
    for addr, src in KBD_NEW.items():
        a.write(addr, asm(src, addr))


if __name__ == '__main__':
    import ndspy.rom
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    code = rom.loadArm9()
    info = apply(code)
    print('ITCM %#x..%#x' % info['itcm_used'], len(info['strlen_sites']), 'strlen*6 sites')
    for s in info['strlen_sites']:
        print('  %#x %s x%d' % s)


# Centred text (0x020d5340 -> 0x020cf0a8, e.g. town building tags): width = cell w * bytes from
# the measure 0x020cf348, too wide for VWF text ("Shipyard" = 48 px > the 36 px tag: not drawn,
# and all such labels sat left). The measure call also leaves the VWF ink width of the first line
# in LASTW, and the horizontal width uses it when the cell is 6 px.
CENTRE_MEASURE = 0x020cf0dc         # bl 0x020cf348 (r0 = string)
CENTRE_MUL = 0x020cf12c             # mul r2, r1, r0 (r1 = cell w, r0 = bytes)
CENTRE_SIZE = 0xc0


def apply_centre(code, at, lastw, widths):
    """Centred-text width patch with its code at [at, at + CENTRE_SIZE)."""
    a = Arm9(code)
    assert a.read(CENTRE_MEASURE, 4) == asm('bl 0x20cf348', CENTRE_MEASURE)
    assert a.read(CENTRE_MUL, 4) == asm('mul r2, r1, r0', CENTRE_MUL)
    mul = asm(f'''
        cmp   r1, #6
        mulne r2, r1, r0
        bxne  lr
        ldr   r2, ={lastw:#x}
        ldr   r2, [r2]
        bx    lr''', at)
    measure = at + len(mul)
    meas = asm(f'''
        push  {{r0, lr}}
        bl    0x20cf348
        pop   {{r1}}
        push  {{r0}}
        ldr   r2, ={widths:#x}
        mov   ip, #0
    next:
        ldrb  r3, [r1], #1
        cmp   r3, #0
        cmpne r3, #0xa
        beq   done
        cmp   r3, #0x1b
        beq   esc
        cmp   r3, #0x81
        blo   one
        cmp   r3, #0xfc
        bhi   one
        ldrb  r3, [r1], #1
        cmp   r3, #0
        beq   done
        add   ip, ip, #12
        b     next
    esc:
        ldrb  r3, [r1], #1
        cmp   r3, #0x41
        cmpne r3, #0x43
        addeq r1, r1, #1
        b     next
    one:
        cmp   r3, #0x80
        movhs r3, #6
        ldrblo r3, [r2, r3]
        add   ip, ip, r3
        b     next
    done:
        cmp   ip, #0
        subne ip, ip, #1
        ldr   r2, ={lastw:#x}
        str   ip, [r2]
        pop   {{r0, pc}}''', measure)
    assert len(mul) + len(meas) <= CENTRE_SIZE, len(mul) + len(meas)
    a.write(at, mul + meas)
    a.write(CENTRE_MUL, asm(f'bl {at:#x}', CENTRE_MUL))
    a.write(CENTRE_MEASURE, asm(f'bl {measure:#x}', CENTRE_MEASURE))


# Sea mode help panels (Search / Declare War / Info, "no one to fight"): overlay 0 0x01ffb4bc
# draws a string into a 4bpp pixel strip (12 px cell per char, 32x16 px blocks) that the BG map
# folds into 192 px lines; it reads every char as 2 SJIS bytes. Its glyph fetch (bl SJIS_GLYPH)
# goes through MODEHELP_GLYPH: a pair of 1-byte chars becomes one 11 px cell holding two 6 px
# half-width glyphs, so English is laid out as 32-column lines (arm9str.modehelp_layout).
OV0 = 0x01ffa000
OV0_GLYPH_CALL = 0x01ffb540         # bl 0x20d198c (r0 = SJIS code -> 11 u16 rows, bit 7 = px 0)
SJIS_GLYPH = 0x020d198c
MODEHELP_SIZE = 0xa8


def apply_modehelp(code, ov0, at):
    """Mode-help glyph hook at [at, at + MODEHELP_SIZE) in ITCM; ov0 = overlay 0 data (patched)."""
    a = Arm9(code)
    o = OV0_GLYPH_CALL - OV0
    assert ov0[o:o + 4] == asm(f'bl {SJIS_GLYPH:#x}', OV0_GLYPH_CALL)
    buf = at + MODEHELP_SIZE - 0x18     # 11 x u16 rows
    src = asm(f'''
        cmp   r0, #0x8000
        bhs   {SJIS_GLYPH:#x}
        push  {{r4, r5, r6, lr}}
        ldr   r2, ={HW_FONT:#x}
        mov   ip, #11
        lsr   r5, r0, #8
        sub   r5, r5, #0x21
        cmp   r5, #0x5e
        movhs r5, #0
        mlalo r5, r5, ip, r2
        and   r6, r0, #0xff
        sub   r6, r6, #0x21
        cmp   r6, #0x5e
        movhs r6, #0
        mlalo r6, r6, ip, r2
        ldr   r1, ={buf:#x}
        mov   r4, #0
    row:
        cmp   r5, #0
        ldrbne r2, [r5, r4]
        moveq r2, #0
        cmp   r6, #0
        ldrbne r3, [r6, r4]
        moveq r3, #0
        orr   r2, r2, r3, lsr #6
        strb  r2, [r1, r4, lsl #1]
        lsl   r3, r3, #2
        add   r0, r1, r4, lsl #1
        strb  r3, [r0, #1]
        add   r4, r4, #1
        cmp   r4, #11
        blt   row
        mov   r0, r1
        pop   {{r4, r5, r6, pc}}''', at)
    assert len(src) <= buf - at, len(src)
    a.write(at, src)
    ov0[o:o + 4] = asm(f'bl {at:#x}', OV0_GLYPH_CALL)
