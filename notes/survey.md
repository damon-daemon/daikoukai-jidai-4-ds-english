# ROM survey (S1, 2026-10-28)

File tree: notes/filetree.txt (ids + paths). 726 files: 660 .pxl, 31 .DK4, 15 .fls, KANJI.FNT, sound_data.sdat.

## ILNK
"ILNK" u32 n, u32 off[n+1] (absolute in file), data 4-aligned. Header padded to 16.

## MESFILE.DK4 (fid 337)
41 blocks, sizes 2188-4092 B. Strings NUL-separated, some with leading spaces (padding? alignment?).
Several strings look like per-personality variants concatenated without NUL, e.g.
"これで、よろしいですか？これでいい？これで、いいですか？..." Maybe a fixed-width/offset table
elsewhere picks substrings. CHECK before translating.

## HELP.DK4 (fid 336)
202 entries, one page each: title line \n body, NUL, padded with NULs.

## SC*.DK4 event scripts
Entry: "CS" 00 01, u32 size, then bytecode. Strings inline, NUL-terminated, followed by NUL padding
(2-byte alignment?). Seen before strings: `00 40 ff ff 00 XX` (XX = speaker/portrait id?),
`80 ff ff 0X f2 00 30 00 02 04 ...` (choice/branch?). Jump targets will need relocation.
SC0: 343 events, 6870 strings; SC1/2/3 share 40-58% of strings with earlier files.

## EV*.DK4: "VE" 00 01, u32 size, counts, offset table. Probably event triggers. No text seen.

## arm9
Uncompressed. Japanese strings 0x12FFE0-0x171A02: crew/people names (0x1389a4+), investment UI,
ship types (0x15e638), sound settings (0x170290), save messages with %s (0x16a07c).
Overlay 0: 6208 B @ 0x01FFA000 (tiny).

## KANJI.FNT (fid 613)
73480 B = 3061.67 × 24. 12 rows × u16 BE MSB-left. Glyph 0 blank; ASCII-like symbols first,
then hiragana/katakana, kanji from ~#250.
