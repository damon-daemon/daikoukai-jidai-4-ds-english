"""Test ROM: event DST of data/SC<n>.DK4 replaced by event SRC (plays it where DST would run).
usage: evswap.py n SRC DST [in.nds] [out.nds]   (events in decimal; SC0 opening = 44)"""
import os
import sys

import ndspy.rom

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import cs  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
n, src, dst = (int(x) for x in sys.argv[1:4])
inp = sys.argv[4] if len(sys.argv) > 4 else os.path.join(ROOT, 'build', 'daikoukai_jidai_4_en.nds')
out = sys.argv[5] if len(sys.argv) > 5 else os.path.join(ROOT, 'build', 'evtest.nds')
rom = ndspy.rom.NintendoDSRom.fromFile(inp)
name = 'data/SC%d.DK4' % n
ev = list(cs.ilnk(rom.getFileByName(name)))
ev[dst] = ev[src]
rom.setFileByName(name, cs.build_ilnk(ev))
rom.saveToFile(out)
print(out)
