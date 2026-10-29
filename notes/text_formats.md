# Text formats (S2, 2026-10-28)

## CS event scripts (data/SC0-3.DK4): `tools/cs.py`, test `tools/dev/cs_roundtrip.py`
Interpreter step: arm9 0x0202a510 (dispatch on u16 >> 13), group handlers
0x0202a414 (g0), a1d8 (g1), 9aa0 (g2), 99c8 (g3), 9874 (g4), 976c (g5), 93b8 (g6).
Instruction = u16 LE: group w>>13, sub (w>>8)&0x1f, imm w&0xff. Length table in cs.py docstring.
- Jumps (g0 sub1-4) are **forward-only u16 relative to the end of the instruction**; no absolute
  offsets anywhere. Rebuild relocates them (cs.rebuild) and is byte-identical on unchanged text.
- Text-bearing ops: g2 sub0 (message, 0xffff = inline string; speaker = byte +5),
  g2 sub1 (8 variants by mate personality, offsets rel +20, speaker byte +0x13),
  g1 sub1/sub2 (2/3-option choice menu, offsets rel +6/+8). Mask bit 7-i = item from a table
  (never happens in SC data; all ~24.6k strings are inline).
- Choice menus: the interpreter takes the length from the LAST option, so options stay in order
  and are never deduplicated. Variants may share one copy (length from the farthest).
- SC3 header is "CS 01 01" (others "CS 00 01"); same format.
- ILNK header is 4-aligned (not 16). cs.build_ilnk is byte-identical.
- testdata/SC*.DK4: older builds (one extra event each), not referenced by arm9. Ignore.
- Event loading: class CEventScriptBuffer, 0x02024134; file table 0x02134580 by scenario index.

## MESFILE (COMMON/MESFILE.DK4): message reader 0x020534f4
- 3668 messages in 41 ILNK blocks. arm9 tables: 0x0214186c = 41 x (u16 first id, u16 block
  size); 0x02141910 = u16 byte offset of each message inside its block (3668 entries, ends at
  0x021435b8 where the path string starts). Length = next offset (or block size) - offset.
- Blocks are cached in two 4 KiB slots (+0x30 + slot<<12): **each block must stay <= 4096 B**.
  Total capacity 41 x 4096 = 168 KB vs 164 KB used now. English will probably need more
  blocks: the block search loop hard-codes 0x29 (0x0205364c) and the tables are packed, so
  relocate the tables to free space if needed.
- Message ids are adjacent; many come in sets of 7 personality variants.

## HELP (COMMON/HELP.DK4)
202 pages, one string each: title\nbody. Links `{label:X}` where X = raw target page byte
(extract shows it as <$NN>).

## Inline codes (expander 0x02053914, 9 callers)
- `F` + I/A/O/U: name variables (FI = player admiral name, FA/FO/FU other names; FO is a fleet).
  `F` + anything else: the F is dropped.
- `I` + any char: inserts the speaker's first-person pronoun (僕 or アタシ), e.g. "IC".
- MESFILE also uses printf `%s`, `%d`-style codes.
- **English needs F and I.** Plan: patch the cmp #0x46 (0x0205397c) and cmp #0x49 (0x02053a44)
  to unused control bytes and convert codes when building (tl format: {FI} {FA} {FO} {FU} {IC}).

## Text engine (S3, 2026-10-28)
- Font load 0x020d1a50: `\GRP\KANJI.FNT` (whole file) -> 0x0225fae8. **22 B/glyph = 11 rows x u16
  (byte0 = left 8 px, MSB left), 3340 glyphs, 11x11 px.** (survey's 24 B was wrong.)
  SJIS -> index: binary search 0x020d19bc over sorted u16 table 0x02125ec4 (3340 codes, only
  0x8140+; no half-width in KANJI.FNT). Glyph ptr 0x020d198c (miss -> glyph 0).
- Half-width font in arm9: **0x02125a60, chars 0x21-0x7E, 11 B/glyph (11 rows, 6 px, MSB left)**.
  Getter 0x020d1820(c, buf). Space/other -> blank.
- String drawer **0x020d1604(ctx, surf, pos*, str, colour)**: lead 0x81-0xFC -> FW blitter
  0x01ff83ac (ITCM) and x += 12; else HW 0x020d16b4 and x += 6 (0x020d169c). HW drawer loops
  6 columns (`cmp #6` at 0x020d1738 16-bit path, 0x020d17f4 4bpp path), 11 rows. FW blitter adds
  a shadow (0x020d1898) when [ctx+0xc]==0; HW chars get none.
  9 callers: 0x020528d8 0x0209d760 0x020d500c 0x020d5060 0x020f3818 0x020facd4 0x020fad0c
  0x020fb09c 0x020fb494.
- Layout **0x020d5404(obj, str)** (253 callers): rect obj+4/8/0xc/0x10 (l,t,r,b), pen +0x24/+0x28,
  vertical flag +0x18, spacing +0x1c/+0x20, autowrap +0x14. Advance: 1-byte = cell w from vfunc
  +0x18 (0x020d57d0..e4), SJIS = 2w. `\n` 0x0a -> newline 0x020d596c. Autowrap breaks mid-word
  when pen+2w >= right (0x020d55e8), kinsoku 0x020d5890/0x020d5824. Char draw = vfunc +0xc
  (0x020d4da8 in the text-box class): 1-byte chars are **paired** into one 12 px cell via
  pending byte obj+0x44 (0x020d4ec4); bypass by NOPing 0x020d4dc8/0x020d4dcc.
  Draw mode obj->[+0x2c]+0x14: 0 -> x = pen/4, 1 -> pen/2 (pen may be sub-pixel units).
- Centred text 0x020d4d34 uses strlen*12/2. ~37 `bl strlen(0x020ced28); mov rX,#6; mul` sites.
- Icon subclass 0x020ac078: SJIS ○×△ etc and ASCII "L1"/"R1" become button icons. Avoid "L1"/"R1"
  in English text.
- Free space: none in arm9 static. ITCM section 0x01ff8000+0x1b20; gap to overlay 0
  (0x01ffa000..0x01ffb860) = 0x4e0 bytes; 18 KB free after 0x01ffb860 (needs a new autoload entry).

## VWF patch (S3 part 2): `tools/patch_arm9.py`, `tools/font.py`, test `tools/dev/vwftest.py`
- Glyphs: font6x12 minus its top row + own digits/punct, written over 0x02125a60 (same format).
  Widths (incl. 1 px gap) 0x00-0x7F table; space 3, digits fixed 5, 0x1c/0x1d (L/R icons) 13.
- Code + table in the ITCM gap (ITCM autoload section grown 0x1b20 -> 0x2000; 0x1e4 B used).
- Hooks: drawer advance 0x020d169c; layout advance 0x020d57e4 (only if cell w == 6, i.e. mode 5,
  the only mode seen: pen = px); autowrap 0x020d55f0 (pen + width - 1); pairing branches
  0x020d4dc8/0x020d4dd0 NOPed; strlen 0x020ced28 -> also stores pixel width in LASTW, and the
  `mul` of 36 strlen*6 sites (and 0x020d4d50 *12/2, 0x020d5304 * cell w) loads LASTW.
  Not handled yet: 0x0208e0f0 ((len + x) * 6), the *3 sites 0x0201a2e8 0x020be808 0x020be9d0.
- Icon subclass 0x020ac118: control bytes 0x1c/0x1d = L/R button icons (stock "L1"/"R1" pairs
  can't work without pairing). Not tested yet (title menu isn't that class).
- Verified in melonDS: title menu (centred) and character-select description (multi-line,
  descenders) render correctly.
- ndspy can't re-load a built arm9 (bootfix stub at the end trips its compression heuristic);
  inspect raw bytes instead.

## Build pipeline (S4): `tools/build.py`, `tools/tl.py`, test `tools/dev/build_roundtrip.py`
- `build.py [--pseudo]`: SC0-3 + MESFILE + HELP rebuilt from tl/ every time (untranslated rows
  keep the Japanese with F/I codes converted), patch_arm9 + arm9str + bootfix, xdelta.
  `--pseudo` fills untranslated SC/MESFILE rows with id-tagged filler (e.g. "044.00AC ...") at
  ~80% of the Japanese width: handy to find which row a screen shows.
- Round trip with empty tl/: re-extracted text identical to script/ (all 6 sources).
- **F/I codes** remapped to 0x0e/0x0f (patch_arm9 CODE_F/CODE_I; only the expander 0x02053914
  reads them, checked all `cmp #0x46/#0x49`). Verified in melonDS: `{FI}` -> player name,
  literal F/I letters render. HELP is not expanded: never convert it (link bytes can be 0x46/0x49).
- **SC event size cap 0x2404 B per CS entry** (only loader: CEventScriptBuffer on the stack of
  0x02023e04, frame 0x241c, data at sp+0x18). Stock max 7964 (SC0 ev 166). At 1.4x text growth
  only SC0 events 64/84/166 overflow; tl.py check reports it -> shorten those events.
- MESFILE: reader 0x020534f4 copies the message (length from the offset table) into obj+0x2030
  and NUL-terminates; tables only used by it -> build keeps the stock partition if every block
  fits 4096 B, else repacks greedily (max 41 blocks, unused table entries first id 0xffff).
  Message 3667's length reads past the table (into the path string): never used, leave it.
- Dialogue box (SC, bottom screen): text x 16..~241, 4 lines, 216 px line verified to fit.
  Speaker nameplate from arm9 names.
- **Opening prologue subtitles** (top screen over the town map, "なんだい、クラウ。見せたいものって？")
  are not text anywhere (no SJIS / glyph index / LZ10 match): probably images -> graphics phase.

## S6: word wrap, HELP renderer, MESFILE contexts
- **Layout autowrap now word-wraps 1-byte text** (patch_arm9 WRAP_CHECK hook): at the first
  letter after a space (pen > left) the whole word (bytes 0x21..0x7f) is measured; a space never
  wraps. Not yet seen on screen (no autowrapped English box reached yet): check with the item
  descriptions (MESFILE 2815-3032) or the arm9 mode-help texts 02147540...
- **HELP renderer** 0x0207ce1c is NOT the layout autowrap: own loop 0x0207ce9c..0x0207d050 on a
  42-column grid (6 px), drawing 1-byte chars in **pairs** (odd ASCII run before \n/{/NUL eats
  the NUL -> runs off the end, game hangs). Replaced (patch_arm9 HELP_LOOP, code in ITCM):
  pixel x, word wrap at 252 px, words drawn whole, leading spaces dropped, links
  `{label:X}` -> 0x0207cbe4(obj, col = x/6, len = ceil(w/6), row, [sp] = X) in colour 0xc.
  Link rects exist for rows 0-9 only (table 0x02119324, 0x1c stride). Title row colour 0xe,
  body 0xf. Verified in melonDS (Select at sea opens HELP page 87 for the Declare War mode).
  Japanese pages use up to 12-13 rows; tl.py check: rows <= 12, links on rows 0-9.
- MESFILE contexts (tl.MES_RANGES, from the Japanese layout, boxes mostly not yet seen):
  dialogue 216 px x up to 4 lines (lines capped by the most any message of the same block
  has); goods descriptions 137-343 228 px x 4; mate bubbles 1419-1796 132 px x 2; item
  descriptions 2815-3032 one line (the game wraps; box TBD); DOL ad 3292-3384 228 px;
  gallery titles 3393-3610 one line. 104-124 are console leftovers (char blurbs, memory card).
- Seen on screen, to fix in arm9 names later: nameplates "Jenas-Passer", "Julio-Elneco" and
  "Dinis-de-Albuquerque" (name parts joined with '-' where the Japanese has ・), and the fleet
  label "AlbuquerqueFleet 1" (no space). The L1/R1 icons in Japanese HELP text show as "L1".
- **MESFILE > 41 blocks** (English needs 48): build.py moves the block table to ITCM
  (MES_TABLE = 0x01ffb860, 64 entries; arm9str extra space starts after it), patches the reader
  literals 0x020535d8/0x0205365c and the search bound 0x0205364c/0x02053654, and two hidden
  limits found by a hang at "To Sea" (Japanese padded to 48 blocks hung too, 40 blocks didn't):
  the cache tags start as 0x2a (= empty) in the ctor 0x020536c8 (-> 0xff), and **vfunc 8
  0x020534dc returns 0x2a = header-cache capacity at obj+0x2230: the archive open 0x020d2018
  copies count+1 offsets there unchecked** (-> 0, no cache; the loader then reads 8 B of
  header per block load). Greedy packing <= 4092 B per block (stock max); the stock partition
  is kept while every block fits 4096. build.py simulates the reader for every message.
- (Solved S11) "stock quirk" at the harbor = memcpy alignment bug: messages are NUL-padded to
  4 bytes now (see notes/graphics.md "S11").
- Test-build switches (env): TL_KEEP_JP=mesfile:86,87;sc0:... keeps rows Japanese,
  MES_PAD=n pads every message, MES_GREEDY=1 forces repacking, NOWW=1 disables word wrap.
- To check on screen (MESFILE): numbers printed as full-width digits ("1 0 0 gold coins"):
  fixed in S11 (formatter 0x020abf50 -> ASCII); %s roles guessed by workers in
  83, 86, 93-95, 288, 820, 871, 1195, 2541-2564 ("%s/%s" fleet), 2801, 3385; `%s%%` (798);
  the item description box (2815-3032, engine word wrap) and mate bubbles (132 px guess);
  port info labels overlap ("Statu", "s Growt", "n Arman").

## S7: HELP translated
- tl/help/00-03.txt (202/202, 4 Sonnet chunks of ~50 pages, reviewed). Page titles fixed in
  work/help_titles.tsv (link labels = target title minus the parenthesis); review aid
  tools/dev/helplinks.py. 契約 (palace menu) is "Contract" (was "Hire" in arm9 02143DF4).
- Page buffer 0x02233040 (loader 0x020d1ef0), next known address 0x02237780: ~18 KB, English
  pages (<= ~600 B) fit.
- Button symbols: HELP English keeps SJIS ○×△□ (tl.HELP_ICONS, encoded cp932); in melonDS
  ○ draws as the A icon, × as B (DS mapping; △/□ presumably X/Y, not seen yet). L1/R1 written
  "L"/"R" in text.
- Seen in melonDS: contents page 82 + page 83 OK. Glitches: an icon after a word overlaps the
  space ("PressⒶ"; icon advance/width vs our renderer), and punctuation right after a link
  wraps alone to the next row (renderer measures the link and the following word separately).
  Not checked: dense pages (@11, @22, @25, @37-39), the table page @133, link at page @38
  <$19> points to Trends (stock Japanese does too).
- Still Japanese on screen (not HELP): loading tip box "艦隊の状態が異常に..." (SC or other
  source?), sea-screen bottom bar 共通/洋上 + date "1月 4日", HELP footer 目次/終了/決定/前/最初
  (probably graphics).

## S10: screen checks, name entry
- Name entry (character select, Y "Change"): stock keyboard = kana grid (arm9 table 0x02155408,
  49 keys incl. 英/記); each key opens a popup listing its variants string (2-byte chars, read
  2 bytes at a time) plus the kanji of a JIS range (table 0x0215FE4C: 50 x (u16 lo, u16 hi,
  key*, variants*); keys matched by strcmp). Editor (obj+0x38: text +0x7c, cursor +0x40 in
  bytes, max +0xa0) assumed 2-byte chars everywhere.
  English: keys are letters A-Y | Z ' - . , 1-9 0 & ! ? + / * Sp (tl/arm9.txt), popups
  "Ａａ" etc., 英 = "Aa" (full alphabet), 記 = "#" (digits/symbols); kanji ranges zeroed;
  patch_arm9.apply_kbd (code at ITCM 0x01ffff00): insert maps full-width -> ASCII (KBD_MAP,
  others dropped), delete/cursor step 1 byte, cursor x = VWF width. Verified in melonDS.
- Test ROMs: tools/dev/evswap.py n SRC DST (event SRC plays in DST's slot; SC0 opening = 44),
  tools/dev/gallery.py n EVENT src:id ... (the event's plain messages show chosen rows),
  tools/emu/steps.sh prefix n (press A n times, screenshot each).
- SC rows with name codes: the build emits only forced breaks (mid-sentence ones joined,
  tl.join_soft) and the engine's runtime word wrap places the real names; seen OK for
  Rafael/Hodrum. Leading spaces of indented thought lines (sc0 166 etc.) are not drawn.
