"""SC rows with name codes (own and shared via identical Japanese), wrapped with each
scenario's default names (tl.SC_NAMES; the build leaves them to the runtime wrap): list rows
over the box's line limit.  usage: namewrap.py [src ...]"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import tl  # noqa: E402

def english(src):
    by_jp = {}
    for s in tl.SRCS:
        t = tl.load(s)
        for r in tl.rows(s):
            e = t.get(str(r['id']))
            if e and e[0] != '=':
                by_jp.setdefault(r['jp'], e[0])
    t = tl.load(src)
    out = {}
    for r in tl.rows(src):
        e = t.get(r['id'])
        en = e[0] if e and e[0] != '=' else (None if e else by_jp.get(r['jp']))
        if en:
            out[r['id']] = (en, r, e is not None)
    return out


def main():
    for src in sys.argv[1:] or list(tl.SC_NAMES):
        nm = tl.names(src)
        n = 0
        for rid, (en, r, own) in english(src).items():
            if not tl.NAME_CODES.search(en):
                continue
            width, maxl = tl.layout(src, r)
            shown = tl.wrap(tl.join_soft(en), width, nm).split('\n')
            if len(shown) > maxl:
                n += 1
                print('%s %s%s %d lines' % (src, rid, '' if own else ' (shared)', len(shown)))
                print('   ' + ' | '.join(shown))
        print('#', src, n, 'rows')


if __name__ == '__main__':
    main()
