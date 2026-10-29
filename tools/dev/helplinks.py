"""Review HELP link labels: print every {label:<$NN>} with the target page's English title,
and pages whose title line differs from work/help_titles.tsv.  usage: helplinks.py"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import tl  # noqa: E402

titles = {}
for line in open(os.path.join(tl.ROOT, 'work', 'help_titles.tsv'), encoding='utf-8'):
    if not line.startswith('#'):
        i, _, _, en = line.rstrip('\n').split('\t')
        titles[int(i)] = en
for rid, (en, path, ln) in sorted(tl.load('help').items(), key=lambda x: int(x[0])):
    if en.split('\\n')[0] != titles[int(rid)]:
        print('@%s title %r != %r' % (rid, en.split('\\n')[0], titles[int(rid)]))
    for m in re.finditer(r'\{([^:}]*):<\$([0-9A-F]{2})>\}', en):
        print('@%-4s %-28s -> %s' % (rid, m.group(1), titles.get(int(m.group(2), 16), '?')))
