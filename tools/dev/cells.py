"""cells.py: labels drawn into text-texture cell tables (patch_arm9.CELLS) vs their cell width.

Finds `ldr r3, =TABLE` + vfunc call (cell table setup) and, after it, each layout call
(bl 0x020d5404) whose x/y come from [tbl, #0xc + 0x1c*i] with r1 = a pointer-referenced
arm9 string. Prints table, cell, cell w, English width, text; '!!' = wider than the cell."""
import json, os, struct, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM
import font, patch_arm9

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
LAYOUT = 0x020d5404
DRAWS = ('#0x20d5404', '#0x20d4d34', '#0x20d52a0')

def main():
    import ndspy.rom
    rom = ndspy.rom.NintendoDSRom.fromFile(os.path.join(ROOT, 'daikoukai_jidai_4.nds'))
    code = rom.loadArm9()
    a = patch_arm9.Arm9(code)
    main = code.sections[0]
    data, base = bytes(main.data), main.ramAddress
    en = {}
    for l in open(os.path.join(ROOT, 'tl', 'arm9.txt'), encoding='utf-8'):
        if '\t' in l:
            k, v = l.rstrip('\n').split('\t', 1)
            en[int(k, 16)] = v.replace('\\n', '\n')
    jp = {int(e['addr'], 16): e['jp'] for e in json.load(open(os.path.join(ROOT, 'script', 'arm9.json')))}
    md = Cs(CS_ARCH_ARM, CS_MODE_ARM); md.detail = False
    ins = []
    for off in range(0, 0x119000 - 0, 4):
        i = next(md.disasm(data[off:off + 4], base + off), None)
        ins.append(i)
    def lit(i):
        if i and i.mnemonic == 'ldr' and '[pc, #' in i.op_str:
            d = int(i.op_str.split('#')[1].rstrip(']'), 16)
            o = i.address + 8 + d - base
            return i.op_str.split(',')[0], struct.unpack_from('<I', data, o)[0]
    def table_ok(t, n):
        o = t - base
        if not (0 <= o < len(data) - 28 * n) or not 1 <= n <= 200:
            return False
        for k in range(n):
            f, x, y, tx, ty, w, h = struct.unpack_from('<7i', data, o + 28 * k)
            if f not in (1, -1) or not (-64 < x < 300 and -64 < y < 200 and 0 <= tx < 256 and 0 <= ty < 256
                                         and 4 <= w <= 256 and h in (11, 12, 13, 14, 16, 24)):
                return False
        return True
    cur = None
    for idx, i in enumerate(ins):
        if i is None:
            continue
        l = lit(i)
        if l and table_ok(l[1], 2):
            n = 0
            while table_ok(l[1], n + 1):
                n += 1
            cur = (l[1], n, i.address)
        if cur and i.mnemonic == 'bl' and i.op_str in DRAWS and i.address - cur[2] < 0x1800:
            s = k = None
            for j in range(idx - 10, idx):
                p = ins[j]
                lp = lit(p)
                if lp and lp[0] == 'r1':
                    s = lp[1]
                elif p and p.mnemonic == 'ldr' and ', #' in p.op_str and p.op_str.startswith('r') and '[sp' not in p.op_str and '[pc' not in p.op_str:
                    v = int(p.op_str.split('#')[1].rstrip(']'), 16)
                    if (v - 0xc) % 0x1c == 0:
                        k = (v - 0xc) // 0x1c
            if s in jp and k is not None and k < cur[1]:
                t = cur[0]
                cell = struct.unpack_from('<7i', data, t - base + 28 * k)
                cells = patch_arm9.CELLS.get(t, {})
                if k in cells:
                    cell = cells[k][1]
                txt = en.get(s, jp[s])
                w = font.width(txt) - 1 if s in en else None
                flag = '!!' if w is not None and w > cell[5] else '  '
                print(f'{flag} {t:#x}#{k:<3} w{cell[5]:<4} en{w!s:<5} {s:#x} {jp[s]} = {txt!r}')

main()
