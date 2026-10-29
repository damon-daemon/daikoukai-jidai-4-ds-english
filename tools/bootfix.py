"""ARM9 boot race fix (makes the game boot in melonDS).

ARM9 bss (0x02170340..0x02387a20) overlaps the ARM7 binary's crt0 at 0x02380000. The ARM9 crt0
zeroes its bss while the ARM7 crt0 is still copying its second autoload chunk
(0x0238fd1c -> 0x027e0000, 0x174b4 B) from code running at 0x02380000. On hardware the ARM7 wins
easily; in melonDS the ARM9 wins, wipes the ARM7 copy loop and the ARM7 dies in the undefined
handler (ARM9 then spins forever on IPC sync: white screens).

Fix: before its autoload/bss clear, the ARM9 polls a code word near the end of ARM7 chunk 2 in main
RAM (invalidating the dcache line each time) until the ARM7 has copied it. The stub is appended to
the end of arm9 (it lies in bss, so it's wiped right after it has run). No-op on hardware.
The wait gives up after TIMEOUT polls: with 16 MB main RAM (DSi mode, e.g. nds-bootstrap on a
3DS) 0x023f6dd8 is not a mirror of 0x027f6dd8, the word never shows up and an endless wait
hangs on white screens.

usage: bootfix.py in.nds out.nds   (standalone test ROM)
"""
import struct
import sys

from keystone import Ks, KS_ARCH_ARM, KS_MODE_ARM

ARM9_BASE = 0x02000000
CALL_AUTOLOAD = 0x02000888       # crt0: bl 0x020009e0 (autoload), right before the bss clear
AUTOLOAD = 0x020009e0
POLL_ADDR = 0x023f6dd8           # ARM7 chunk 2 (0x027f6dd8: last loop of its last function), via
                                 # the 4 MB main RAM mirror: the SDK MPU makes 0x027e0000+ no-access
POLL_WORD = 0x1affffd4           # bne 0x027f6d30
TIMEOUT = 0x100000               # polls (~0.3 s), then boot anyway


def bl(src, dst):
    return struct.pack('<I', 0xeb000000 | (((dst - src - 8) >> 2) & 0xffffff))


def apply(arm9):
    """Return arm9 bytes with the boot wait appended and hooked in."""
    arm9 = bytearray(arm9)
    o = CALL_AUTOLOAD - ARM9_BASE
    assert arm9[o:o + 4] == bl(CALL_AUTOLOAD, AUTOLOAD), 'unexpected crt0 (already patched?)'
    while len(arm9) % 4:
        arm9.append(0)
    stub = ARM9_BASE + len(arm9)
    code, _ = Ks(KS_ARCH_ARM, KS_MODE_ARM).asm(f"""
        ldr r0, ={POLL_ADDR:#x}
        ldr r1, ={POLL_WORD:#x}
        mov r3, #{TIMEOUT:#x}
    wait:
        subs r3, r3, #1
        beq done
        mcr p15, 0, r0, c7, c6, 1
        ldr r2, [r0]
        cmp r2, r1
        bne wait
    done:
        b {AUTOLOAD:#x}
    """, stub)
    arm9 += bytes(code)
    arm9[o:o + 4] = bl(CALL_AUTOLOAD, stub)
    return bytes(arm9)


if __name__ == '__main__':
    import ndspy.rom
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    rom.arm9 = apply(rom.arm9)
    rom.saveToFile(sys.argv[2])
