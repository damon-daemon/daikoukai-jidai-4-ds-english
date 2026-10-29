"""Flag SC rows whose English length is far off the Japanese (a sign of rows shifted by one).

usage: scshift.py sc0 [ratio=3.5]   prints rows with en/jp char ratio outside [1/r .. r*1.4]
plus runs of >= 2 consecutive outliers in one event (likely shifts).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import tl  # noqa: E402

src = sys.argv[1]
r = float(sys.argv[2]) if len(sys.argv) > 2 else 3.5
t = tl.load(src)
prev = None
for row in tl.rows(src):
    e = t.get(row['id'])
    if not e or e[0] == '=':
        continue
    jp = len(row['jp'].replace('\n', '').replace('　', ''))
    en = len(e[0].replace('\\n', ' ')) / 2.2      # ~2.2 English chars per Japanese char
    if jp < 4 and en < 12:
        continue
    q = (en + 1) / (jp + 1)
    if q > r * 1.4 or q < 1 / r:
        mark = '**' if prev and prev[:3] == row['id'][:3] else '  '
        print('%s%s %4.1f  %s\n      %s' % (mark, row['id'], q, row['jp'].replace('\n', ' '), e[0][:120]))
        prev = row['id']
    else:
        prev = None
