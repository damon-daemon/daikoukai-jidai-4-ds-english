"""Build the English ROM and the xdelta patch.

  arm9: VWF + code remap (patch_arm9), tl/arm9.txt strings (arm9str), boot fix (bootfix)
  COMMON/MESFILE.DK4: messages repacked into <= 4 KiB blocks, arm9 index tables rewritten
  COMMON/HELP.DK4, data/SC0-3.DK4: rebuilt from tl/ (untranslated text keeps its Japanese,
  with the F/I codes converted)
  graphics: English labels drawn over .pxl images (gfx.EDITS), FLS captions + name cards (fls)

usage: .venv/bin/python tools/build.py [--pseudo] [clean.nds] [out.nds]
  --pseudo  fill untranslated MESFILE/SC text with id-tagged English filler (layout tests)
"""
import os
import struct
import subprocess
import sys

import ndspy.rom

sys.path.insert(0, os.path.dirname(__file__))
import arm9str  # noqa: E402
import bootfix  # noqa: E402
import cs  # noqa: E402
import fls  # noqa: E402
import gfx  # noqa: E402
import patch_arm9  # noqa: E402
import tl  # noqa: E402
from extract import MES_BLOCKS, MES_OFFS, MES_COUNT, mes_tables  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MES_NBLOCKS = 64                    # block table moved to ITCM (MES_TABLE), loop bound patched
MES_BLOCK_MAX = 4092                # block cache slot (stock max is 4092)
OV0_END, ITCM_END = 0x01ffb860, 0x02000000
MES_TABLE = OV0_END                 # 64 x (u16 first id, u16 size); arm9str extra space after it
# block reader (0x020534f4 / search 0x02053628): table pointers and the hard-coded count 41
MES_PATCH = {0x020535d8: ('<I', 0x0214186e, MES_TABLE + 2), 0x0205365c: ('<I', 0x0214186c, MES_TABLE)}
MES_LOOP = {0x0205364c: ('cmp r3, #0x29', 'cmp r3, #%d' % MES_NBLOCKS),
            0x02053654: ('mov r0, #0x28', 'mov r0, #%d' % (MES_NBLOCKS - 1)),
            # reader ctor: cache slot tags start as 0x2a (= no block); block 42 now exists
            0x020536c8: ('mov r1, #0x2a', 'mov r1, #0xff'),
            # vfunc 8 = header cache capacity (42 offsets at obj+0x2230): open copies count+1
            # offsets there unchecked, so >41 blocks overflow it. 0 = no cache (8 B read per load)
            0x020534dc: ('mov r0, #0x2a', 'mov r0, #0')}


def build_sc(raw, table):
    entries, over = [], []
    for ei, e in enumerate(cs.ilnk(raw)):
        ins, _ = cs.parse(e)
        repl = {}
        for p, n, info in ins:
            strs = info.get('strs')
            if not strs:
                continue
            multi = 'offs' in info
            repl[p] = [table['%03d.%04X' % (ei, p) + ('.%d' % vi if multi else '')]
                       for vi in range(len(strs))]
        ne = cs.rebuild(e, repl)
        if len(ne) > tl.EVENT_MAX:
            over.append('event %d: %d B' % (ei, len(ne)))
        entries.append(ne)
    if over:
        raise ValueError('events over %d B: %s' % (tl.EVENT_MAX, ', '.join(over)))
    return cs.build_ilnk(entries)


def build_mesfile(raw, a9, table):
    """Repack messages into blocks; keep the stock partition when every block still fits."""
    first, _, _ = mes_tables(bytes(a9.code.sections[0].data))
    pad = b' ' * int(os.environ.get('MES_PAD', '0'))   # test builds: grow every message
    # the reader's memcpy (0x020cec74) copies words if len % 4 == 0, halfwords if even, without
    # checking alignment: NUL-pad every message to 4 bytes so offsets stay aligned
    msgs = [table[str(m)] + pad + b'\0' for m in range(MES_COUNT)]
    msgs = [b + b'\0' * (-len(b) % 4) for b in msgs]
    bounds = first + [MES_COUNT]
    if os.environ.get('MES_GREEDY') or any(
            sum(map(len, msgs[bounds[i]:bounds[i + 1]])) > 4096 for i in range(len(first))):
        first, size = [0], 0
        for m, b in enumerate(msgs):
            if size + len(b) > MES_BLOCK_MAX:
                first.append(m); size = 0
            size += len(b)
        if len(first) > MES_NBLOCKS:
            raise ValueError('MESFILE needs %d blocks > %d' % (len(first), MES_NBLOCKS))
    bounds = first + [MES_COUNT]
    blocks, offs, sizes = [], [], []
    for i in range(len(first)):
        blk = b''
        for m in range(bounds[i], bounds[i + 1]):
            offs.append(len(blk))
            blk += msgs[m]
        blocks.append(blk); sizes.append(len(blk))
    tbl = []
    for i in range(MES_NBLOCKS):
        tbl += [first[i], sizes[i]] if i < len(first) else [0xffff, 0]
    a9.write(MES_OFFS, struct.pack('<%dH' % MES_COUNT, *offs))
    if len(first) <= 41:            # keep the (now unused) stock table in sync for extract.py
        a9.write(MES_BLOCKS, struct.pack('<82H', *tbl[:82]))
    for addr, (fmt, old, new) in MES_PATCH.items():
        assert a9.read(addr, 4) == struct.pack(fmt, old)
        a9.write(addr, struct.pack(fmt, new))
    for addr, (old, new) in MES_LOOP.items():
        assert a9.read(addr, 4) == patch_arm9.asm(old, addr)
        a9.write(addr, patch_arm9.asm(new, addr))
    # simulate the reader (0x020534f4): block search, length from the next offset or block size
    for m in range(MES_COUNT - 1):
        b = max(i for i in range(len(first)) if first[i] <= m)
        n = offs[m + 1] - offs[m]
        if n < 0:                                  # subs + ldrmi: only when negative
            n = sizes[b] - offs[m]
        assert blocks[b][offs[m]:offs[m] + n] == msgs[m], m
    # the table itself goes to ITCM once that section is grown (main)
    return cs.build_ilnk(blocks), len(first), struct.pack('<%dH' % (2 * MES_NBLOCKS), *tbl)


def build_help(table):
    return cs.build_ilnk([table[str(i)] + b'\0' for i in range(len(table))])


def main():
    args = [x for x in sys.argv[1:] if not x.startswith('--')]
    pseudo = '--pseudo' in sys.argv
    clean = args[0] if args else os.path.join(ROOT, 'daikoukai_jidai_4.nds')
    out = args[1] if len(args) > 1 else os.path.join(
        ROOT, 'build', 'daikoukai_jidai_4_en%s.nds' % ('_pseudo' if pseudo else ''))
    rom = ndspy.rom.NintendoDSRom.fromFile(clean)
    code = rom.loadArm9()
    a9 = patch_arm9.Arm9(code)

    for i in range(4):
        name = 'data/SC%d.DK4' % i
        rom.setFileByName(name, build_sc(rom.getFileByName(name), tl.table('sc%d' % i, pseudo)))
    name = 'COMMON/MESFILE.DK4'
    data, nb, mes_tbl = build_mesfile(rom.getFileByName(name), a9, tl.table('mesfile', pseudo))
    rom.setFileByName(name, data)
    print('MESFILE %d B in %d blocks' % (len(data), nb))
    rom.setFileByName('COMMON/HELP.DK4', build_help(tl.table('help')))
    print('gfx: %d labels' % gfx.apply(rom))
    print('fls: %d captions/cards' % fls.apply(rom))

    info = patch_arm9.apply(code)
    # strings that don't fit the pool go to the free ITCM after overlay 0 (0x01ffa000..0x01ffb860):
    # grow the ITCM autoload section to the end of ITCM (the overlay range in between stays zero
    # and is overwritten when the overlay is loaded at runtime)
    a9.grow(patch_arm9.ITCM, ITCM_END)
    a9.write(MES_TABLE, mes_tbl)
    patch_arm9.apply_kbd(code, ITCM_END - patch_arm9.KBD_SIZE, info['lastw'])
    centre_at = ITCM_END - patch_arm9.KBD_SIZE - patch_arm9.CENTRE_SIZE
    patch_arm9.apply_centre(code, centre_at, info['lastw'], info['widths'])
    modehelp_at = centre_at - patch_arm9.MODEHELP_SIZE
    ov = rom.loadArm9Overlays()[0]
    assert not ov.compressed and ov.ramAddress == patch_arm9.OV0
    ov0 = bytearray(rom.files[ov.fileID])
    patch_arm9.apply_modehelp(code, ov0, modehelp_at)
    rom.files[ov.fileID] = bytes(ov0)
    n_in, n_moved, free = arm9str.apply(code, extra=[(MES_TABLE + len(mes_tbl), modehelp_at)])
    print('arm9: ITCM %#x..%#x, %d strlen sites; strings %d in place, %d moved, %d B pool free' % (
        *info['itcm_used'], len(info['strlen_sites']), n_in, n_moved, sum(b - a for a, b in free)))
    rom.arm9 = bootfix.apply(code.save(compress=False))

    os.makedirs(os.path.dirname(out), exist_ok=True)
    rom.saveToFile(out)
    print('rom', out)
    if not pseudo:
        patch = os.path.splitext(out)[0] + '.xdelta'
        subprocess.run(['xdelta3', '-e', '-f', '-9', '-S', 'djw', '-s', clean, out, patch], check=True)
        print('patch', patch)


if __name__ == '__main__':
    main()
