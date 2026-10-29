# Uncharted Waters IV: Rota Nova (Daikoukai Jidai IV DS) — English Translation

A fan translation of **Daikoukai Jidai IV: Rota Nova** (大航海時代IV ROTA NOVA, Koei, 2006),
the Nintendo DS version of *Uncharted Waters IV*, into English. The DS version was only
released in Japan.

> **This is a full machine translation.** All of the game's text was translated from
> Japanese by an AI model, not by a human translator, and it has not been
> proofread by a fluent Japanese speaker. Expect occasional mistranslations, awkward
> phrasing and inconsistent terms. Corrections are welcome.

This repository contains the English text and the tools that build the patch.
It does **not** contain the game, any of its data, or the Japanese script — you need
your own copy of the game.

## What's translated

- All four scenarios (Rafael, Hodrum, Ril, Maria): story events, dialogue and choices
- System and NPC messages (ports, taverns, guilds, palace, sea), help pages, item
  descriptions
- Menus, commands, names of people, ships, ports, items and goods
- Graphics: menu labels, info panels, sea-screen buttons, the title and character
  select screens, the prologue subtitles and opening name cards, the
  "Introducing Online" slides, redrawn with original English fonts
- A variable-width font, so English text is proportional and readable
- Name entry uses an English letter keyboard

Character names follow the 2021 English release (*Uncharted Waters IV HD*): Rafael
Castor, Hodrum Joachim Bergstrom, Ril Argot, Maria Huamei Li.

**Intentionally not translated:** the title logo.

## Applying the patch (players)

1. Download the release zip from the Releases page. It contains the xdelta patch.
2. You need an unmodified dump of the Japanese game (game code `ADKJ`):

   | | |
   |---|---|
   | Size  | 67,108,864 bytes |
   | CRC32 | `446D516B` |
   | MD5   | `1bed97424d9f9f50401d80a0afdd0444` |
   | SHA-1 | `57000b53914b27e20598fe35d6ed2abbb5905cdd` |

3. Apply it with an xdelta tool, e.g. [Delta Patcher](https://github.com/marco-calautti/DeltaPatcher)
   or the command line:
   ```
   xdelta3 -d -s daikoukai_jidai_4.nds daikoukai_jidai_4_en.xdelta daikoukai_jidai_4_en.nds
   ```

The patched ROM also boots in melonDS. The unpatched Japanese ROM shows a white
screen there; the patch includes a fix for that (it changes nothing on hardware).

## Building from source

Requirements: Python 3.10+, `xdelta3` (optional, for the patch file).

```
python -m venv .venv
.venv/bin/pip install -r requirements.txt
cp /path/to/your/dump.nds daikoukai_jidai_4.nds     # must match the checksums above
.venv/bin/python tools/setup.py                     # checks the ROM, extracts script/ from it
.venv/bin/python tools/build.py                     # writes build/daikoukai_jidai_4_en.nds + .xdelta
```

`tools/setup.py` checks the ROM's MD5 and generates `script/` (the Japanese text,
used to match and validate the English in `tl/`). `script/` and `build/` are never
committed. Edits to `tl/` only need `build.py` again.

## Repository layout

| Path | Contents |
|---|---|
| `tl/sc0` … `tl/sc3` | English for the four scenarios' event scripts, by event and offset (`@EEE.PPPP`) |
| `tl/mesfile/`, `tl/help/` | English system/NPC messages and help pages, by number (`@N`) |
| `tl/arm9.txt` | English for names and UI strings in the game code, by address |
| `tools/build.py` | Builds the patched ROM and the patch |
| `tools/setup.py` | Checks your ROM and creates `script/` (`extract.py`, `arm9str.py export`) |
| `tools/tl.py` | Validates and word-wraps translations (`check`, `show`, `stats`) |
| `tools/cs.py` | Event script (CS bytecode) parser and rebuilder |
| `tools/patch_arm9.py`, `bootfix.py` | Code patches: variable-width font, layout fixes, name entry, melonDS boot fix |
| `tools/arm9str.py` | Relocates translated strings in the game code |
| `tools/gfx.py`, `pxl.py`, `fls.py` | Redraw English labels and captions into the game's graphics at build time |
| `tools/font.py`, `font6x12.py`, `boldfont.py` | Original fonts drawn for this project |
| `notes/` | Format and engine notes |
| `tools/dev/`, `tools/emu/` | Development helpers (previews, measurements, emulator scripts) |

## Known issues

- Sea battle screens (battle interface, win/loss banner, Spoils bar) have not been
  checked on screen yet.
- Indented thought lines in a few story events lose their indent.
- A few small labels (cargo/ship selection buttons) have only been checked in previews.

Tested in melonDS.

Please report bugs, including crashes and mistranslations, as [GitHub issues](https://github.com/damon-daemon/daikoukai-jidai-4-ds-english/issues), with a
screenshot and where it happened.

## Credits

- Translation and hacking: [damon-daemon](https://github.com/damon-daemon)
- Daikoukai Jidai IV Rota Nova © 2006 Koei Tecmo. This is an unofficial fan project,
  not affiliated with or endorsed by Koei Tecmo. Please support the official releases.

## License

The tools, fonts, documentation and English translation text in this repository
are released under the [MIT License](LICENSE). This covers only original work in
this repository: the game itself and all of its content (code, Japanese text,
graphics, audio) are copyright Koei Tecmo and are not included or licensed here.
