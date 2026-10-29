"""arm9chk.py FILE...: validate ADDR<TAB>English lines (worker output or tl/arm9.txt) against
script/arm9.json: known address, ASCII only, same %-codes, no more lines than the Japanese,
pixel width over 1.5x the Japanese (warning only)."""
import json
import os
import re
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import arm9str  # noqa: E402

CODE = re.compile(r'%[-0-9.]*l?[sdcxu]')
PREWRAPPED = {0x02131F74, 0x02131FC4}
rows = {r['addr']: r for r in json.load(open(arm9str.JSON, encoding='utf-8'))}
errs = warns = n = 0
for path in sys.argv[1:]:
    for ln, line in enumerate(open(path, encoding='utf-8'), 1):
        line = line.rstrip('\n')
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        n += 1
        where = '%s:%d' % (path, ln)
        if '\t' not in line:
            print(where, 'ERROR no tab'); errs += 1; continue
        a, en = line.split('\t', 1)
        a = a.lstrip('@').upper()
        if a not in rows:
            print(where, 'ERROR unknown address', a); errs += 1; continue
        jp = rows[a]['jp']
        en = en.replace('\\n', '\n')
        bad = [c for c in en if not (0x20 <= ord(c) < 0x7f or c == '\n')]
        if bad:
            print(where, 'ERROR non-ASCII', ''.join(bad)); errs += 1
        if CODE.findall(en) != CODE.findall(jp):
            print(where, 'ERROR codes', CODE.findall(jp), '->', CODE.findall(en)); errs += 1
        # mode help is laid out by the build; the Deck guide is pre-wrapped by hand (fixed y per string)
        if en.count('\n') > jp.count('\n') and int(a, 16) not in arm9str.MODEHELP.keys() | PREWRAPPED:
            print(where, 'ERROR more lines than the Japanese (%d)' % (jp.count('\n') + 1)); errs += 1
        if '%' not in jp and not bad:
            w, jw = arm9str.en_width(en), arm9str.jp_width(jp)
            if w > max(jw * 3 // 2, jw + 12):
                print(where, 'LONG %dpx > 1.5 x %dpx: %s' % (w, jw, en.replace('\n', '\\n'))); warns += 1
print('%d lines, %d errors, %d too long (> 1.5x the Japanese width)' % (n, errs, warns))
