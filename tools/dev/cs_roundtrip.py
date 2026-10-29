"""Check tools/cs.py against the ROM: every SC event parses to its exact size, jumps land on
instructions, rebuild with unchanged strings is byte-identical, and rebuild with every string
resized still parses with the same strings.  usage: cs_roundtrip.py [clean.nds]"""
import os, sys
import ndspy.rom
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import cs

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1] if len(sys.argv) > 1 else
                                       os.path.join(ROOT, 'daikoukai_jidai_4.nds'))
for f in range(4):
    raw = bytes(rom.getFileByName('data/SC%d.DK4' % f))
    ents = cs.ilnk(raw)
    nstr = same = grown = 0
    for e in ents:
        ins, end = cs.parse(e)
        assert ins[-1][0] + ins[-1][1] == end
        r = {p: [t for _, t in i['strs']] for p, n, i in ins if 'strs' in i}
        nstr += sum(map(len, r.values()))
        same += cs.rebuild(e, r) == e
        g = {p: [t + b'XYZ' * (len(t) % 3) for t in v] for p, v in r.items()}
        ins2, end2 = cs.parse(cs.rebuild(e, g))
        starts = {p for p, n, _ in ins2} | {end2}
        assert all('jump' not in i or p + n + i['jump'] in starts for p, n, i in ins2)
        got = [t for p, n, i in ins2 for _, t in i.get('strs', [])]
        grown += got == [t for p in sorted(g) for t in g[p]] and len(ins2) == len(ins)
    ok = same == grown == len(ents) and cs.build_ilnk(ents) == raw
    print('SC%d %3d events %5d strings  identical %d  resized-ok %d  %s'
          % (f, len(ents), nstr, same, grown, 'OK' if ok else 'FAIL'))
