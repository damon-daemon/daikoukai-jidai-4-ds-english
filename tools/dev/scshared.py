"""List SC1-3 rows that reuse another row's English (identical Japanese) and whose English may
only fit Rafael (male pronouns, boy/kid, Clau...). Override such rows in tl/scN/shared.txt.

usage: scshared.py sc2 [regex]
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import tl  # noqa: E402

src = sys.argv[1]
pat = re.compile(sys.argv[2] if len(sys.argv) > 2 else
                 r"\b(he|him|his|himself|boy|boys|lad|kid|young man|son|sonny|Clau|Claudio|Rafael|"
                 r"Julio|Jenas|Arcadius|Eirene|Christina|Lisbon|Portugal|Portuguese)\b", re.I)
own = tl.load(src)
by_jp = {}
for s in tl.SRCS:
    if s == src:
        continue
    t = tl.load(s)
    for r in tl.rows(s):
        e = t.get(str(r['id']))
        if e and e[0] != '=':
            by_jp.setdefault(r['jp'], (s, r['id'], e[0]))
n = 0
for r in tl.rows(src):
    if r['id'] in own or r['jp'] not in by_jp:
        continue
    s, rid, en = by_jp[r['jp']]
    if pat.search(en):
        n += 1
        print('@%s    # %s, from %s @%s\n  %s\n  %s' % (r['id'], tl.speaker(r['spk'], r['id']), s, rid,
                                                    r['jp'].replace('\n', '\\n'), en))
print('%d rows' % n, file=sys.stderr)
