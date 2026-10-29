# Graphics (S10 part 2, 2026-10-28)

Dumps (gitignored): `work/fs/` (all ROM files), `work/pxlpng/` (every .pxl as PNG, first palette),
`work/grppng/` (GRP archive type-0x10 entries), contact sheets `work/sheet*.png` (`work/sheet.py`).
Decoder: `tools/pxl.py`.

## Formats
- **.pxl**: u8 bpp (4/8/16), u8 flag, u16 0, u32 w **in u16 units** (stride = 2w bytes; px = w*16/bpp),
  u32 h, u32 palette offset (0x14), u32 pixel offset; palette BGR555 (some files hold several
  palettes: 4bpp with 32..1328 colours); pixels **linear**, 4bpp low nibble = left. 16bpp = direct.
- **GRP/*.DK4 ILNK entries type 0x10**: u32 0x10, u32 fmt (8 = 4bpp, 9 = 8bpp), u32 12+palette bytes,
  u16 ?, u16 ?, u16 colours, u16 blocks; palette at +0x14; blocks: u32 size (incl. 12-byte head),
  u16 x, u16 y (texture VRAM slot?), u16 w (u16 units), u16 h, linear pixels. `pxl.parse_blocks`.
  Types 0x12/0x13 (CMMNIMG 4/5, MAPPOINT) and headerless entries (CMMNIMG 0/2/3/7, SLACKIMG
  13-19, CHARA 4+) not decoded.
- Raw GRP files: DSOBJ.DK4 (16 KB) / DSOBJR.DK4: **4bpp OBJ tiles** (1D) with text: sea-screen menu
  機能/水夫編成/甲板画面/情報/航路図/アイテム, "下の画面をタッチしてください", "スタートボタンを...".
  OAM shapes unknown (built in arm9). DSCHR/OCETC/OCINIT/GMONS/RACE/TITLEMAP/SKYWALL: not 4bpp
  tiles, no text seen.

## Which files are used
arm9 names most .pxl directly (`_pxl/x.pxl`, `/evstill/evstill%03u.pxl`, `/towngrp/towngrp%02u.pxl`).
Not referenced (old leftovers): `_pxl/copyright, logo, startmenu0, ship_eurL`.
GRP/SLACKIMG.DK4 (referenced) repeats slackimg00-12/20 + winframe05: patch both copies.

## Text-bearing images (inventory)
| File | Text |
|---|---|
| _pxl/__marker (256x256 tex) | 機能 水夫編成 甲板画面 情報 航路図 アイテム, やりなおし 決定 キャンセル 収支報告 海域委任 寄港 衝攻撃 哨戒 命令変更, 売却品 特産品 積み荷 売り値 買い値, 一時置き場 配布品 戦利品, 男 女 |
| _pxl/__frame (256x256 tex) | 種類 相場% 入荷月 積み荷選択 船選択 終了 等級 キャンセル, 月 日, 装備 助言, 水夫編成 旗艦重視 必要最小 平均化 均等補給 EXIT 変更終了, はい いいえ はずす 使う |
| _pxl/kakutei | 確定 |
| _pxl/chihofleetinfo | レベル 収入額 支出額 投資額 任務 |
| _pxl/dividecrewinfo | 艦隊水夫数 未編成水夫数 航続可能日数 海兵詰所 砲種 縦帆性能 横帆性能 |
| _pxl/fleetinfo, saveloadinfo | レベル (勢力値) |
| _pxl/forceinfo | レベル 所持金 勢力値 本拠地 友好度 |
| _pxl/personinfo | 身体 精神 レベル HP |
| _pxl/shipinfo | 水 食糧 水夫 物資倉庫 積荷 縦帆性能 横帆性能 海兵詰所 武装砲台 砲種 耐久力 |
| _pxl/towninfo | 種類 発展度 状態 武装度 シェア 特産品 |
| _pxl/goldsearoutediscovery, goldsearoutelog(2) | 交易品 利益率 報奨金 (合計) |
| _pxl/haifuhin, senrihin, tempcargo | 配布品, 戦利品, 一時置き場 |
| _pxl/deck04 | 勝敗 (digits + "Perfect!" are fine) |
| _pxl/slackimg12 (+SLACKIMG 12) | 名 ミドルネーム 姓 勢力名 誕生日 |
| _pxl/slackimg20 (+SLACKIMG 20) | ボタンを押してください! |
| _pxl/title/title02 | スタートボタンを押すか / この画面をタッチしてください |
| _pxl/title/title06 | Aボタンを押すか、この画面を / タッチするとスキップします |
| _pxl/online/Online00, Online50-62 | 大航海時代 Online promo slides (Japanese paragraphs) |
| DSOBJ/DSOBJR | see above |
| evstill168-171, 206-209 | handwritten placeholder sketches (アラブの村 etc.), probably unused |
Logo (title03/05, winframe00 "PORTO ESTADO") left as is.
_pxl/charselect.pxl: rows 234-313 below the picture hold the 5 char-select plate labels as a mask
(white 255, shadow 1 at +1,+1, on 0); slackimg12 is NOT what that screen shows.
GRP/CMMNIMG.DK4: entry 5 (type 0x12, 4bpp 512x256) = __marker | __frame side by side (same
indices); entry 4 (type 0x13) = 83 x 16-colour palettes; entries 0/2/3/7 = 256-colour palette +
8bpp thumbnails/portraits; GRP/CMMNIMG.000 = 56x56 8bpp portraits.
DSOBJ.DK4 OBJ layout: objects 0-5 = 64x32 (8x4 tiles) sea command buttons; tiles 368.. = 16x16
(2x2) glyphs 東 南 西 北 月 日 (compass, date); digits elsewhere. Index ~ brightness.
Footer buttons (Ⓐ決定, Ⓑ戻る, Ⓧ共通 ...) are **text**: arm9 0x0211B4E4.. (arm9str range now from
0x02119000).

## Build: `tools/gfx.py` (S10 part 2)
build.py calls gfx.apply(rom). EDITS: file -> [(box, text, opts)]; targets 'x.pxl',
'GRP/X.DK4#n' (type-0x10 entry, block 0), TILED raw OBJ files (TileImg, objects stacked into one
virtual image). label(): erase the old ink (pixels > thresh from the box median: dark/light/both),
layered inpaint from clean neighbours, draw English with the VWF glyphs (font.py) or boldfont caps
(bold=True) in the original ink colour (or ink=, grad= per-row, outline=, shadow=, clear= for masks).
Stone plates on info panels: box = plate outer box (tools/dev/plates.py finds them), widen=W
stretches a plate. COPIES: __marker/__frame are copied into CMMNIMG#5 after editing.
Dev: tools/dev/gfxprev.py (before/after), tools/dev/grid.py (zoom with 8 px grid), work/corrupt.py
(xor files in a test ROM to find which file a screen uses).
Port info header (arm9 0x0215692C 種類状態発展度武装度) is ONE string rendered into a line buffer
shown as 4 sprites cut at px 0/24/48/84: English padded with <$1E> = 1 px blank spacer
(font.SPACER width 1; 0x7F draws garbage).
Test save: work/port_lisbon.sav (Rafael in Lisbon harbour menu; copy to build/<rom>.sav, title ->
Continue: `press.sh /dev/null Return w w x w w w x w w w w x w w w w`).
**Don't test graphics/arm9 changes with savestates**: a state restores the old arm9 + VRAM, so
edits look missing. Always boot the new build and load the in-game save.
`tools/dev/build_roundtrip.py` only passes with an empty `tl/` (IndexError on MESFILE > 41 blocks;
old limitation, not a regression).

Done and seen in melonDS: title prompt, char-select labels, footers, sea command buttons (DSOBJ),
port info header, save/load plates, date "1/ 3".
Done, not yet seen on screen: info panels (fleet/force/person/ship/town/crew/gold route), __marker
/__frame labels, bars (Gifts/Spoils/Temp Hold), kakutei "OK", slackimg20, title06, compass E/S/W/N.

## S11 screen check (2026-10-29)
Seen OK in melonDS (port_lisbon.sav): Mate Info, Ship Info, Fleet Info, Crew Setup, town info
(Route Map), Faction panel, footers. Fixes:
- Footer buttons: width was `(strlen >> 1) * 12` at 0x020ca7a4 (missed by strlen_mul_sites);
  now LASTW **rounded up to even**: labels share one 4bpp strip, an odd x shifts the next label
  1 px left into the previous button ("World!" / "Back(" strays).
- Ship info value x positions: s16 (x, y) tables 0x0211a210 / 0x02150704 (2 copies);
  patch_arm9.SHIPINFO_X moves Water/Sailors/Durability values right of the widened plates.
- Gun type names: inline 19-byte records at 0x0213c192 (patch_arm9.GUN_NAMES); `%s砲`/`%d門`
  -> `%s` / ` x%d` ("Culverin x2").
- Mate attributes on 24 px plates -> STA AGI CHA WIT SPI LUK (full names kept in prose).
  Skills cell = 60 px incl. 3-digit value -> Command, Sailing, Survey, Finance, Insight,
  Diplomacy, Fencing (renamed in HELP/SC too; skills go up to 200+).
- Faction panel values at x 56: plates back to 40 px (Influence 44), 友好度 -> Goodwill everywhere.
- Town info 武装度 plate -> "Arms" (no widen); name format `%s・%s` -> `%s %s`; など -> " etc.".
- **MESFILE alignment bug (ours, also the stock "水 pply" quirk)**: the reader copies a message
  to obj+0x2030 with memcpy 0x020cec74, which uses word copies if len % 4 == 0 / halfwords if
  even, without checking the source alignment (ARM9 unaligned ldr rotates). Repacked English
  blocks had unaligned offsets -> scrambled messages ("The" = message 28 at departure).
  build.py now NUL-pads every message to 4 bytes (49 blocks).
- Number formatter 0x020abf50 wrote full-width digits ("5 0 0 days"): now ASCII (CODE_PATCHES).
- Footer row drops buttons whose x < 0 (packed right-to-left from x 253): 帆開閉 "Furl/Unfurl"
  -> "Sails" brings back L/R "Turn Sails" at sea. `tools/dev/footers.py` lays out every footer
  table with the English widths (only a shifted-window false positive at 0x02119a2c).
- MESFILE 86 "has left %s." -> "Departed %s.".
Not reachable from this save: Golden Route Records (no records), Ancient Maps.

## TODO (graphics)
- __frame tiny labels: done in S18 (gfx.TINY caps), screen still unknown. deck04 勝敗 (stylised,
  battle). MAPPOINT: done (no text). (DSOBJR + Online slides done in S17.)

## FLS = prologue/opening animations (S11)
`FLS/*.fls`, `m02_03.fls`: header u32 anim_off (0x180), u32 table_off, u32 count, u32 data_base;
table = count x 0x18 (u16 type, u16 w, u16 h, u16 flag, u32 pal_off, u32 pal_size, u32 pix_off,
u32 pix_size; offsets from data_base). type 1 = 8bpp picture (LZ10 palette + LZ10 pixels),
type 0 flag 1 = **4bpp caption strip** (16-colour raw palette, LZ10 pixels, stored 256 px wide,
w = shown width). Japanese captions (5): M20#27, M22#1-2, M24#3-4 (prologue: "なんだい、クラウ。
見せたいものって？" ...). M28 (opening) = typewriter name cards in the game's own Latin:
"Rafael Castor", "Hoodlum Joakim Bergstrom", "Lil Argot", "Camille Overijssel" (+ more after #72).
Extract: see work/fls/ (sheets).

**S12: done** (`tools/fls.py`, called from build.py; lz10.compress added). Rebuild keeps stock
blob offsets (the stock padding is irregular and gaps hold leftover bytes) and only shifts blobs
after one that outgrows its slot; unchanged rebuild is byte-identical for all 15 files.
The 32-byte "pal" blob of type-0 strips is a parameter block, not colours; pixel values are
intensity levels (captions 1 fill / 2 outline; cards 7..f or 6/9/b..e). Captions redrawn with
the VWF font + 8-neighbour outline, centred in w. Name cards (HD spellings, user's choice
2026-10-29): letters cut from the stock frames by frame diffs and re-composed (advance =
bbox width - 3), missing letters c, h, K, R hand-drawn in fls.GLYPHS; Kamil card (16 frames,
14 letters) holds the full name for the last frames. Verified in melonDS: opening cards,
M20 (Rafael prologue) and M24 (Hodrum prologue); M22 (Ril?) not seen but same format.
Slightly bigger compressed card strips (+3-6 %) play fine.
**Boot slide (S13)**: logo.fls entries 1-3 are full-screen 4bpp slides (256 px rows, 256 rows,
LZ10; 32-byte param blob kept). Entry 3 "リコエイションゲーム" -> "A RECOEITION GAME" composed in
fls.logo() from entry 2's italic letters ("AN EIJI FUKUZAWA PRODUCTION"): line un-slanted
(row shift round((y-104)*0.25)), letters cut along darkest seams (fls._seam, window +-1),
placed, slanted back (stock letters pixel-exact). G = C + O's lower right + bar; M = N's
halves + its right stem. Seen in melonDS.
Title logo 大航海時代IV + ロッタノヴァ: **kept as is** (user, 2026-10-29).

## S13 screen check (2026-10-29)
Seen OK: boot slide "A RECOEITION GAME", attract movie + name card, prologue caption (M20),
sea screen (date "1/ 3" from DSOBJ glyphs, sea command footer, mate bubble "Rafael, Lv UP!"),
tavern Gather Sailors + crew setup, footer "Ⓐ OK".
Sea footer L and B have no label: same in the stock game (empty strings), not a bug.
Fixed: plaza vendor menu "%s Shop" clipped ("Textiles Sh") -> "%s" (Food / Spices / Textiles).
title06 (skip prompt) is not shown in the prologue or attract movie: probably the ending, unchecked.
Lisbon save: fleet has no sailors (tavern -> Gather Sailors, R = Max, X = Done) and no cargo.
Icons in Lisbon town (bottom screen taps): tavern (84,25), palace? "Fund Military" (126,25),
plaza vendors / Trend Info (180,25), harbor (230,25). Trade market not found yet.
Still not seen: Gifts/Spoils/Temp Hold bars, kakutei.pxl, slackimg20, compass E/S/W/N,
__frame tiny labels, item descriptions.

## S14 market check (2026-10-29)
Seen with work/port_lisbon.sav: Market -> Trade / Invest / Prices, Items (empty: no item to
check descriptions with), plaza vendors (two "Textiles" stalls = stock categories).
- **Text-texture cells**: some screens draw labels into one texture and show it through a table of
  7 x s32 cells (flag, screen x, y, tex x, tex y, w, h) given to the layer's vfunc +0x1c; the
  label x/y passed to layout = the cell's tex x/y, and w fits the Japanese, so English is cut
  ("Balanc", "Statu"). patch_arm9.CELLS moves widened cells into free texture space (trade top
  screen 0x02159a64: Expenses, Status, Trade, Balance, Ship). `tools/dev/cells.py` lists the
  labels drawn into cell tables it can match statically (few; most screens use other paths).
- Trade: town name drawn twice into one opaque cell (first centred by 3 * char count): NOPed
  the first draw (CODE_PATCHES 0x020c135c), "LLisbon" -> "Lisbon". Labels Income / Expenses /
  Ship / Restock.
- **`len * 3` centring sites** now patched (strlen_mul_sites factor -1 = LASTW/2): 0x020be81c
  (prices category plates, 18 - len*3: long names went negative and were not drawn),
  0x020be9d8 (culture area line: centres on the name only, constant 0x24 -> 25 for the English
  suffix " Culture Area"), 0x0201a2e8 ((18 - len) * 3, rewritten by hand). Plates are 36 px:
  Seasoning / Fine Goods get short forms only there (PLATE_SHORT: Season., Finery).
- Amount dialog 0x020c5c40 (Invest, Military investment, Contract fee): label "%10s" at x 0
  and 残金 at x 36, both cut at 60 px -> "%s", Balance x 0, labels "Investment" / "Contract Fee".
Emulator: after run.sh the first title->Continue key sequence lands back on the attract movie;
sending it twice reaches the port (boot takes longer than the 8 s in the recipe).

## S15 town buildings check (2026-10-29)
Seen with work/port_lisbon.sav: shipyard (Buy, Custom Order, Refit/Change Gear, name entry),
guild (Buy Items: item info + descriptions), inn, tavern (drink / rumours), palace, prices.
Town tags: Left/Down cycle them; taps need the screen settled (tap twice). Lisbon buildings:
Market (30,25), Tavern (84,25), Palace (128,30), Plaza (180,25), Harbor (230,25), Shipyard
(232,75), Inn (24,80), Guild (40,145).
- **Centred text 0x020d5340** (town building tags, prices plates header, price bubbles) measured
  width as bytes * cell w: "Shipyard" = 48 px > the 36 px tag -> not drawn. patch_arm9.apply_centre
  (code in a reserved ITCM span before the keyboard code): the measure call leaves the VWF ink
  width (first line, minus the trailing 1 px) in LASTW, the horizontal width uses it if cell w = 6.
  Tags: 36 px; 総督府 tag -> "Gov. Ofc" (0x02157064 kept "Governor's").
- Refit header 装備変更 cut at 48 px ("Change Equ"): -> " Equipment" (cell 48 px, leading space
  centres it like the stock " Ship Info ").
- **Cannon picker row** (refit -> cannons): 144 px line buffer shown as two 72 px rows, sprite
  seam at x 108 (text crossing it gets a ~3 px gap). Stock "%-12s威力%s" padded by bytes;
  rewritten in place (patch_arm9.GUN_ROW): name at x 0, "Pwr %d" at 72, "Range+" (長射程) at 108.
- Item descriptions (MESFILE 2815-3032) overflowed the ~240 px box (engine wraps wider):
  tl.MES_RANGES now pre-wraps them at 228 px (up to 4 lines).
- Rumours 820/821: args are (name, place/faction, role); English follows that order now.
- "It takes %s day(s)", "Wait %s day(s)" (shipyard, 1-day jobs).
Left as is: map items show "Ancient Map-" (the stock "－" no-slot marker drawn right after the long
type name); "Shipyard" S touches the tag border.

## S16 Common menu / sea check (2026-10-29)
Test saves: work/port_lisbon.sav (slot 1, Lisbon harbour) now also has **slot 2 = at sea off
Lisbon** (work/sea_lisbon.sav: 24 sailors, little water/food, so "out of food" pops up soon). Load slot 2:
`press.sh /dev/null Return w w x w w w x w w w Down x w w w w`. At sea Y = At Sea modes (Y cycles
Info -> Search -> Declare War). Tavern gathers sailors once a day (Inn -> Stay One Day resets it).
- **MESFILE %s order**: English that swapped the args (the game fills them in order) rewritten:
  614-628 (place, faction), 342, 849/850, 956-963, 978-983 (possessive form fits either order),
  1182/1184, 2806-2813 ("bad rumors in %s"). Tavern honorific 旦那/姐さん (arm9 02143BD0..) is an
  arg of 870-873/877/878 (ids are decimal in code, 0x368 = 872): reworded; 871/872 drop it
  (tl.MES_DROP_ARGS). Script used: compare %-codes JP vs EN per message (all arm9 ones fine).
- **Deck quick guide** (0x02015510: title + 3 strings at fixed y 12/24/48 via layout, stock
  char-wraps ~260 px, panel hides x < 2): pre-wrapped in tl (1/2/3 lines, <$1E><$1E> left pad);
  titles 02131F30/F3C/02132044 "Deck" (cell ~50 px).
- **Sea mode help** (Search / Declare War / Info + "No one to start a battle with." bubble): drawn by
  overlay 0 0x01ffb4bc, a full-width-only renderer (always 2 bytes per char) into a 4bpp strip of
  12 px cells (32x16 px blocks, 0x3800 B); a per-mode BG map shows strip cells at fixed places made
  for the Japanese (rows start at cells 16/32/56.. and are 16-20 cells visible). Patch
  (patch_arm9.apply_modehelp, ITCM span before apply_centre; overlay 0 `bl` at 0x01ffb540 patched by
  build.py): a 1-byte pair = one cell with two 6 px half-width glyphs. arm9str.MODEHELP holds each
  string's row map (measured with numbered cells); modehelp_layout word-wraps into it and fills
  every mapped cell (undrawn cells keep stale pixels). Declare War text shortened to fit.
  0215F72C/0215F870 (other caller 0x020ce0xx, screen unknown) use the same maps: not seen.
Seen OK: Common menu carousel (overlap is by design), Deck screen + room info, tavern Treat
Everyone (872), crew setup, harbor Depart menu, inn, save screen, all three mode panels.

## S17 (2026-10-29): Online slides, race prompt
- **Sea battles not checked** (user: skip for now). No battle reachable from the test saves:
  event 10 (Valdes battle) hangs when evswapped into the opening; Auto-Move needs a Surveyor
  (Rafael has no mates early); no fleets met near Lisbon; supplies run out in ~10 days.
  Enemy-attack messages are MESFILE 622-628 / 1305-1312 (reader called via vtable 0x0205529c).
  Needs a save near a battle (deck04 勝敗, Spoils bar, battle UI still unseen).
- **Introducing Online** (title -> Extras): Online50-62 = bottom-screen paragraph overlays (4bpp,
  white 15 + outline 1 on 0): gfx.ONLINE + gfx.paragraph() redraw them (x 40, 14 px pitch,
  centred on y 89, 4-way outline). Online00: 版 erased, line 2 -> "Details at the official
  site below". Online01-38 (top screenshots of the PC game) left as is. Seen in melonDS.
- **DSOBJR** race prompt: two lines of three 64x16 OBJs, tiles interleaved (185+16k, line k%2):
  TileImg objects can now carry a pixel position (t0, w, h, x, y). "PRESS START OR / TOUCH THE
  LOWER SCREEN" (bold). Not seen: the race needs a second DS (host lobby screen is fine).
- Seen: Temp Hold bar (Harbor -> Arrange Cargo, needs cargo), race menus/rules, host lobby.
- title06 / kakutei: only their static loaders reference the image objects (0x023127b4,
  0x023139c0); maybe unused, or indexed from a neighbour. Prologue tap = skip, no prompt.
- __frame 積み荷選択/船選択/終了/等級/キャンセル still unplaced (cargo screen with one ship doesn't
  use them; probably needs a multi-ship fleet).

## S18 (2026-10-29)
- __frame 積み荷選択 / 船選択 終了 / 等級 キャンセル: 8 px rows with no gap (y 32/40/48), too short for
  the 9-row VWF caps: own 7-row capitals gfx.TINY (label tiny=True) -> CARGO / SHIP END / RANK
  CANCEL. Boxes start at x 208 (x 207 bleeds into the rounded frame). Screen not seen yet.
- GRP/MAPPOINT.DK4: entries 1/3 (type 0x12) = 4bpp 256x88 at +20, palettes in 0/2 (type 0x13):
  town building signboards (pictures; a few decorative kanji on Asian signs). No edit.
- Stray arm9 rows left Japanese on purpose (14): single kanji 捻袈篭惜侈婁я (font/variant tables),
  full-width Ｌ Ｒ Ｘ Ｙ (button glyphs), name-entry alphabet table, 　　 padding.
