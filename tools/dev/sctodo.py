"""Split an SC source's todo rows into worker files on event boundaries.

usage: sctodo.py sc1 [todo_rows_per_chunk=300] [--force]  -> work/sc_todo/sc1_NN.txt
Todo = untranslated rows whose Japanese has no translation anywhere (tl.show --todo).
Files are written once per source (chunk numbers must not change while workers run);
--force rewrites them. With existing files it just prints the remaining todo per chunk.
"""
import contextlib
import glob
import io
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import tl  # noqa: E402

args = [a for a in sys.argv[1:] if a != '--force']
src = args[0]
size = int(args[1]) if len(args) > 1 else 300
out = os.path.join(tl.ROOT, 'work', 'sc_todo')
os.makedirs(out, exist_ok=True)
rs = tl.rows(src)
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    tl.show(src, 0, len(rs), todo=True)
todo = set(re.findall(r'^@(\S+)', buf.getvalue(), re.M))
existing = sorted(glob.glob(os.path.join(out, src + '_*.txt')))
if existing and '--force' not in sys.argv:
    for path in existing:
        ids = re.findall(r'^@(\S+)', open(path, encoding='utf-8').read(), re.M)
        print('%s  rows %4d  todo %d' % (os.path.basename(path), len(ids), sum(i in todo for i in ids)))
    sys.exit()
for path in existing:
    os.remove(path)
idx = {r['id']: i for i, r in enumerate(rs)}
chunks, cur, n, ev = [], [], 0, None
for r in rs:
    if r['id'] not in todo:
        continue
    e = r['id'][:3]
    if e != ev and n >= size:
        chunks.append(cur); cur, n = [], 0
    ev = e
    cur.append(r['id']); n += 1
if cur:
    chunks.append(cur)
blocks = {}
for m in re.finditer(r'^@(\S+).*\n(?:  .*\n)*', buf.getvalue(), re.M):
    blocks[m.group(1)] = m.group(0)
by_jp = {}                       # English of covered rows, shown as context
for s in tl.SRCS:
    t = tl.load(s)
    for r in tl.rows(s):
        e = t.get(str(r['id']))
        if e and e[0] != '=':
            by_jp.setdefault(r['jp'], e[0])
for k, c in enumerate(chunks):
    path = os.path.join(out, '%s_%02d.txt' % (src, k))
    evs = set(i[:3] for i in c)
    text = []
    for r in rs:
        if r['id'][:3] not in evs:
            continue
        if r['id'] in blocks and r['id'] in c:
            text.append(blocks[r['id']])
        elif r['jp'] in by_jp:
            text.append('(done) %s: %s\n' % (tl.speaker(r['spk'], r['id']), by_jp[r['jp']]))
    open(path, 'w', encoding='utf-8').write(''.join(text))
    print('%s  todo %4d  events %s-%s' % (os.path.basename(path), len(c), c[0][:3], c[-1][:3]))
