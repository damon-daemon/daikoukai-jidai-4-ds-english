"""Test ROM for the ARM9 text patches: title menu strings replaced in place by English.

usage: vwftest.py in.nds out.nds
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import ndspy.rom  # noqa: E402
import bootfix  # noqa: E402
import patch_arm9  # noqa: E402

TESTS = {   # arm9 address: English (must fit in the Japanese string's bytes)
    0x021379f0: 'Continue',
    0x02137a08: 'New Game',
    0x021379fc: 'Extras',
    0x02137a14: 'Gallery',
    0x02137a98: 'Race (\x1c)',
    0x0214fddc: 'A Portuguese lad who longs for the sea.\n'
                'A friend talks him into sailing.\n'
                'For new players. gjpqy',
}

rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
code = rom.loadArm9()
info = patch_arm9.apply(code)
a = patch_arm9.Arm9(code)
for addr, en in TESTS.items():
    old = a.read(addr, 256).split(b'\0')[0]
    new = en.encode('ascii')
    assert len(new) <= len(old), en
    a.write(addr, new + bytes(len(old) - len(new)))
rom.arm9 = bootfix.apply(code.save(compress=False))
rom.saveToFile(sys.argv[2])
print('ITCM %#x..%#x' % info['itcm_used'], len(info['strlen_sites']), 'strlen sites')
