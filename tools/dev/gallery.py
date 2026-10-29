"""Test ROM: the text slots of one event show chosen rows (any source), in order.
usage: gallery.py n EVENT src:id [src:id ...]  -> build/gallery.nds
Plain one-string messages of event EVENT in data/SC<n>.DK4 (from the en build) take the
rows' English one by one (speakers stay those of EVENT); later slots are left as they are.
SC0 opening = event 44."""
import os
import sys

import ndspy.rom

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import cs  # noqa: E402
import tl  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
n, ev = int(sys.argv[1]), int(sys.argv[2])
want = [a.split(':') for a in sys.argv[3:]]
tables = {}
texts = []
for src, rid in want:
    if src not in tables:
        tables[src] = tl.table(src)
    texts.append(tables[src][rid])
rom = ndspy.rom.NintendoDSRom.fromFile(os.path.join(ROOT, 'build', 'daikoukai_jidai_4_en.nds'))
name = 'data/SC%d.DK4' % n
evs = list(cs.ilnk(rom.getFileByName(name)))
ins, _ = cs.parse(evs[ev])
repl = {}
for p, _, info in ins:
    strs = info.get('strs')
    if strs and 'offs' not in info and len(strs) == 1 and texts:
        repl[p] = [texts.pop(0)]
assert not texts, '%d rows left over: event has too few slots' % len(texts)
evs[ev] = cs.rebuild(evs[ev], repl)
rom.setFileByName(name, cs.build_ilnk(evs))
out = os.path.join(ROOT, 'build', 'gallery.nds')
rom.saveToFile(out)
print(out, len(repl), 'slots')
