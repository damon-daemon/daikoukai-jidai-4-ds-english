"""Check the clean ROM and generate script/ from it (needed by tl.py and build.py).

usage: .venv/bin/python tools/setup.py [clean.nds]
  script/sc0-3.json, mesfile.json, help.json (extract.py) and script/arm9.json (arm9str.py export)
"""
import hashlib
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MD5 = '1bed97424d9f9f50401d80a0afdd0444'


def main():
    rom = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'daikoukai_jidai_4.nds')
    md5 = hashlib.md5(open(rom, 'rb').read()).hexdigest()
    if md5 != MD5:
        sys.exit('%s: MD5 %s, expected %s (unmodified Japanese ROM, game code ADKJ)' % (rom, md5, MD5))
    tools = os.path.dirname(os.path.abspath(__file__))
    for cmd in (['extract.py', rom], ['arm9str.py', 'export', rom]):
        subprocess.run([sys.executable, os.path.join(tools, cmd[0])] + cmd[1:], check=True)


if __name__ == '__main__':
    main()
