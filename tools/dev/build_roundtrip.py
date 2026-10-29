"""Re-extract text from a built ROM and compare with script/*.json (codes mapped back).
With an empty tl/ every row must match.  usage: build_roundtrip.py [built.nds]"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import ndspy.rom  # noqa: E402
import extract  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1] if len(sys.argv) > 1 else
                                       os.path.join(ROOT, 'build', 'daikoukai_jidai_4_en.nds'))
got = {'sc%d' % i: extract.sc_rows(bytes(rom.getFileByName('data/SC%d.DK4' % i))) for i in range(4)}
got['mesfile'] = extract.mes_rows(bytes(rom.getFileByName('COMMON/MESFILE.DK4')), bytes(rom.arm9))
got['help'] = extract.help_rows(bytes(rom.getFileByName('COMMON/HELP.DK4')))
for k, rows in got.items():
    ref = json.load(open(os.path.join(ROOT, 'script', k + '.json'), encoding='utf-8'))
    fix = (lambda s: s) if k == 'help' else (lambda s: s.replace('<$0E>', 'F').replace('<$0F>', 'I'))
    bad = [(a, b) for a, b in zip(ref, rows) if a['id'] != b['id'] or a['jp'] != fix(b['jp'])]
    print('%-8s %5d rows, %d differ' % (k, len(rows), len(bad) + abs(len(ref) - len(rows))))
    for a, b in bad[:3]:
        print('   ', a['id'], repr(a['jp'][:60]), '->', repr(b['jp'][:60]))
