"""Dump the game's Japanese text from the clean ROM into script/*.json (never committed).

script/sc0..sc3.json  event-script strings: id "EEE.PPPP" (event, instruction offset in the
                      CS entry) or "EEE.PPPP.v" (item v of a choice menu or variant message),
                      speaker byte, jp
script/mesfile.json   MESFILE messages: id = message number (arm9 offset table 0x02141910), block
script/help.json      HELP pages: id = entry index

Text is cp932; bytes below 0x20 other than \\n, and HELP link targets ({label:<byte>}),
are shown as <$NN>.

usage: .venv/bin/python tools/extract.py [clean.nds]
"""
import json, os, re, struct, sys
import ndspy.rom

sys.path.insert(0, os.path.dirname(__file__))
import cs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, 'script')
ARM9 = 0x02000000
MES_BLOCKS = 0x0214186c    # 41 × (u16 first id, u16 block size)
MES_OFFS = 0x02141910      # u16 byte offset within its block, per message id
MES_COUNT = 3668
CTRL = re.compile(rb'[\x00-\x09\x0b-\x1f]')


def decode(b):
    return CTRL.sub(lambda m: b'<$%02X>' % m.group()[0], b).decode('cp932')


def encode(s):
    return re.sub(rb'<\$([0-9A-F]{2})>', lambda m: bytes([int(m.group(1), 16)]), s.encode('cp932'))


def sc_rows(raw):
    rows = []
    for ei, e in enumerate(cs.ilnk(raw)):
        for p, n, info in cs.parse(e)[0]:
            strs = info.get('strs', [])
            multi = 'offs' in info     # choice menu or variant message
            for vi, (sp, t) in enumerate(strs):
                rid = '%03d.%04X' % (ei, p) + ('.%d' % vi if multi else '')
                rows.append({'id': rid, 'spk': info.get('speaker'), 'jp': decode(t)})
    return rows


def mes_tables(arm9):
    bt = struct.unpack_from('<82H', arm9, MES_BLOCKS - ARM9)
    offs = struct.unpack_from('<%dH' % MES_COUNT, arm9, MES_OFFS - ARM9)
    return list(bt[0::2]), list(bt[1::2]), offs


def mes_rows(raw, arm9):
    first, size, offs = mes_tables(arm9)
    blocks = cs.ilnk(raw)
    first = first + [MES_COUNT]
    rows = []
    for bi in range(len(blocks)):
        for m in range(first[bi], first[bi + 1]):
            end = offs[m + 1] if m + 1 < first[bi + 1] else size[bi]
            t = blocks[bi][offs[m]:end]
            # NUL then space padding to 4 bytes; adjacent messages may also run on without a NUL
            t = t.split(b'\0')[0]
            rows.append({'id': m, 'block': bi, 'jp': decode(t)})
    return rows


HELP_LINK = re.compile(rb':(.)\}', re.S)   # {label:<target page byte>}


def help_rows(raw):
    rows = []
    for i, e in enumerate(cs.ilnk(raw)):
        t = HELP_LINK.sub(lambda m: b':<$%02X>}' % m.group(1)[0], e.rstrip(b'\0'))
        rows.append({'id': i, 'jp': t.decode('cp932')})
    return rows


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'daikoukai_jidai_4.nds')
    rom = ndspy.rom.NintendoDSRom.fromFile(path)
    arm9 = bytes(rom.arm9)
    os.makedirs(SCRIPT, exist_ok=True)
    out = {'sc%d' % i: sc_rows(bytes(rom.getFileByName('data/SC%d.DK4' % i))) for i in range(4)}
    out['mesfile'] = mes_rows(bytes(rom.getFileByName('COMMON/MESFILE.DK4')), arm9)
    out['help'] = help_rows(bytes(rom.getFileByName('COMMON/HELP.DK4')))
    for name, rows in out.items():
        json.dump(rows, open(os.path.join(SCRIPT, name + '.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        print('%-8s %5d entries' % (name, len(rows)))


if __name__ == '__main__':
    main()
