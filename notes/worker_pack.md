# Worker pack: Daikoukai Jidai IV Rota Nova (DS) English translation

Read only this file and your brief. Do not read CLAUDE.md, other notes, or tools source.

## The game
大航海時代IV ROTA NOVA (Koei, DS 2006) = **Uncharted Waters IV: Rota Nova**. Age of Exploration
(16th century) trading/exploring/naval-battle game. The player is an admiral with a fleet and
mates (航海士), sails between ports (街), trades goods (交易品), discovers sites (史跡), fights
pirates and fleets, collects treasures/equipment. Tone: light adventure, friendly, youthful
characters; plain modern English, not archaic.

Protagonists (official English of the 2021 HD release where known):
- ラファエル・カストール = **Rafael Castor** (Portuguese boy, Lisbon)
- リル・アーゴット = **Lil Argot** (Dutch merchant girl)
- ホドラム・ヨアキム・ベルグストロン = **Hodrum Joachim Bergstrom** (Swedish admiral)
- マリア・リー・ホアメイ = **Maria Huamei Li** (Ming China; table order is given/family/other)

## Fixed terms
提督 Admiral · 航海士 mate · 艦隊 fleet · 旗艦 flagship · 街 port (town if inland) ·
交易品 trade goods · 史跡 historic site · 総帥 Leader (head of a faction) · 副官 First Mate ·
艦長 Captain · 水夫 sailors · 私掠艦隊 privateer fleet · 海賊 pirate · 金貨 gold coins ·
酒場 Tavern · 交易所 Market · 造船所 Shipyard · 出港所 Harbor · ギルド Guild · 広場 Plaza ·
商用X Merchant X · 武装X Armed X · 軍用X Military X / War X · 輸送用X Transport X.

## Spelling rules
- **ASCII only** (the font has nothing else): no accents (Joao, not João), straight quotes ' ".
- Real historical people/places: their standard English names (リスボン Lisbon, ヴェネツィア
  Venice, バルバロッサ・ハイレディン Hayreddin Barbarossa, アルブケルケ Albuquerque).
- Japanese names Hepburn without macrons; Chinese pinyin; Arabic/Turkish/Indian the usual English
  spellings. Fictional names: natural spelling for the character's nationality.
- Ship types: standard English (キャラック Carrack, ナオ Nao, ジーベック Xebec, 関船 Sekibune,
  安宅船 Atakebune, 鉄甲船 Ironclad, ダウ Dhow, サムブーク Sambuk).
- Items/goods: natural English, Title Case for item/treasure names, lowercase never needed.
- Name particles デ/ダ/フォン/イブン/ベイ = de/da/von/ibn/Bey (keep case as in real usage).

## Format rules
- Input line: `ADDR<TAB>JPpx<TAB>Japanese` (`\n` = line break, JPpx = Japanese pixel width).
  Output line: `ADDR<TAB>English` (keep the address exactly; `\n` for line breaks).
- Same printf codes (`%s %d %4d %2d ...`) in the same order. Never more lines than the Japanese.
- **Width**: JPpx is the Japanese pixel width; English averages ~5 px/char (space 3, digits 5).
  Up to 1.5x JPpx is fine (most UI has room; screens get checked in the emulator later), so
  **prefer clear full words**: 王宮 Palace, 薬 Medicine, 鯨 Whale. Only beyond 1.5x (the checker
  says LONG) shorten, and then still readably (e.g. "Merch. Galleon", "Lt. Galleon"); never
  cryptic forms like "Whl", "Rx". Different Japanese terms in one list must stay distinct.
- Full-width spaces used for column alignment in the Japanese: use plain spaces only if needed.
- Skip (output nothing) for strings that are not text to translate: kana/kanji tables, name-entry
  keyboards, single punctuation symbols, internal debug labels. List skipped addresses in your report.
- Identical Japanese gets the same English automatically; translate each address anyway (cheap)
  unless the brief says otherwise.

## Check
`.venv/bin/python tools/dev/arm9chk.py <your output file>` (run from the project root).
Fix all ERRORs; fix WARN (too wide) where a sensible shorter form exists.
`.venv/bin/python tools/dev/strw.py "Some text"` prints a pixel width.

## Glossary
`work/glossary.tsv` (JP<TAB>EN) holds names and terms already translated (people, ships, items,
goods, places). Use `grep` on it for any name you meet; use exactly that English.

## MESFILE (system / mate / NPC messages)
Your brief gives a file `work/mes_todo/NN.txt` (made by `tools/tl.py show mesfile ... --todo`):

    @123    # 216px x4
      Japanese text (\n = line break)

Write `tl/mesfile/NN.txt` with the same `@id` lines (the `# ...` hint may be dropped) and the
English under each:

    @123
    Admiral, there seems to be a crowd\nin the plaza.

- The hint is the box: `216px x4` = the build wraps your text to 216 px and allows 4 lines.
  You don't need `\n` for wrapping, only where a break means something (the line after a
  form of address like "Admiral," or a pause). `one line, no \n` = a one-line label (gallery
  titles); keep it about as short as the Japanese. `no \n, the game wraps` = item description,
  write plain sentences, no `\n`, about the length of the Japanese at most.
- **Codes, same ones in the same order**: `%s` (a name, a port, goods, a number as text),
  `%d`. Work out from context what each `%s` is and build the sentence so every order works.
  `{FI}` `{FA}` `{FO}` `{FU}` names, `{IC}` the speaker's "I": write just "I" instead (the
  code may be dropped; the checker ignores {I?}).
- **Mates' personality sets**: many messages come as 7-8 consecutive variants of one line, one
  per mate personality (polite, cheerful girl, rough sailor, old man "じゃ", childish "～",
  gentleman "ですな", etc.). Same meaning, different voice: keep each voice recognisable
  (old man: "Hmm, ...", rough: "Hey, ...", childish: "Admiraaal!"), but light; never dialect
  spelling that's hard to read. Identical Japanese gets identical English.
- 提督 when addressing the player: "Admiral". ～様/さん: drop or use Mr./Ms. sparingly.
- `…` -> "...", `！？` -> "!?", `～` at the end of a word -> stretch the word or drop it,
  `『』` / `「」` -> double quotes.

Check: `.venv/bin/python tools/tl.py check mesfile` (from the project root). Fix every
problem it lists for your ids (codes, width, lines, non-ASCII).

## HELP (in-game manual pages)
Your brief gives a file `work/help_todo_N.txt`: one block per page, the whole page on one line:

    @87
      宣戦モード（洋上コマンド）\n画面上の艦隊・街に{戦闘:<$59>}をしかけます。\n...\n\n

Write `tl/help/0N.txt`, the same `@id` lines, each page as **one physical line** with `\n` for
line breaks, a blank line between blocks:

    @87
    Declare War Mode (At-Sea Commands)\nStart a {battle:<$59>} with a fleet or port on screen.\n...\n\n

- **Title** (text before the first `\n`): copy it exactly from `work/help_titles.tsv` (column 4,
  by page id). Every page title is fixed there so all chunks agree.
- **Layout**: keep the Japanese `\n` structure (one `\n` per paragraph, the same trailing
  `\n\n` or `\n`). Don't add `\n` for wrapping: the game word-wraps at 252 px (~50 characters).
  A page may use at most **12 rows** including the title; long Japanese pages may need tighter
  English. Keep every fact, cut padding ("It is possible to" -> "You can").
- **Links** `{label:<$NN>}`: keep `<$NN>` exactly (NN = target page id in hex, look it up in
  help_titles.tsv column 2). The label is English: the target's title without the part in
  parentheses, or the natural word in your sentence ("Start a {battle:<$59>} with..."). Links
  must stay in the first 10 rows (the checker says so if not): rephrase or move the sentence up.
  `→{X:<$NN>}` -> `> {X:<$NN>}`; a full-width space between links -> two spaces.
- Symbols: `【！】` -> `[!]` (the contents page explains it); `「」『』` -> double quotes;
  `［ラファエル］` -> `[Rafael]`; full-width digits/letters -> ASCII (ＨＰ HP); `／` -> `/`;
  `〈〉` -> parentheses. 『大航海時代４』 = "Uncharted Waters IV".
- **Buttons**: keep `○ × △ □` as they are (the game draws them as button icons; the checker
  allows them in HELP). Write L1 / R1 as `L` / `R` ("press L", "L/R" for L1R1): "L1"/"R1" are
  rejected. 十字ボタン = "the +Control Pad". タッチスクリーン = touch screen, タッチペン = stylus.
- Command and data names: use the UI names from help_titles.tsv and `work/glossary.tsv`
  (Tavern, Market, Shipyard, Harbor, Deck Screen, Route Map, Victor's Mark, Golden Route...).
  Quote in-game option values with double quotes as the Japanese does ("Allied", "Healthy").

Check: `.venv/bin/python tools/tl.py check help` (rows, link rows, codes = the same links
in the same order, non-ASCII).

## SC (story event scripts)
Your brief gives a file `work/sc_todo/sc0_NN.txt` (made by `tools/tl.py show sc0 ... --todo`):

    @005.01B6    # Fernan, 216px x4
      さぁて、FI君\n私のためにも、奮戦してもらわんとな\nはっはっは！

Write `tl/sc0/NN.txt` in the MESFILE format (`@id` line, English below, blank line between
blocks; the `# ...` hint may be dropped). Ids are `EEE.PPPP` (event.position): rows of one
event are one scene, in order; read the whole event before translating it.

- **Speaker** (in the hint): who says the line. `no nameplate` = narration, tutorial/system
  text, or an unnamed voice (sometimes the Japanese names it: `＜男の子＞` -> `<Boy>`).
  `mate, <voice>` = one of 8 variants (`.0`-`.7`) of the same line, said by whichever mate is
  present; voices: .0/.1 polite, .2 cheerful boy, .3 girl, .4 rough sailor, .5 old man,
  .6 childish ("Admiraaal!"), .7 gentleman. Same meaning, light voice differences.
  `choice N` = player answer options: one short line each.
- **Box**: 216 px x 4 lines (~40 characters a line). The build word-wraps; use `\n` only for a
  meaningful break (after an exclamation/pause, a new sentence that should start a line), never
  to wrap. If the checker says `5 lines > 4`, tighten the English (don't split rows; you can't
  add rows). Keep it natural spoken English; trim filler rather than meaning.
- **Name codes** (keep the same set; order may change with English word order):
  `{FI}` the player's given name (Rafael), `{FA}` family name (Castor); the Japanese `FI・FA`
  is the full name -> `{FI} {FA}`. `{FU}` the player's full formal name (incl. middle names).
  `{FO}` the player's fleet/company name (like "Castor Fleet"): write "the {FO}" where English
  needs an article. `FI君` -> `{FI}`, `FA提督` -> `Admiral {FA}`, `FIさん` -> `{FI}`.
  `{IC}` = the speaker's "I": just write I (the code may be dropped).
- **Event size**: an event's total text has a hard cap; `tl.py check sc0` names any event over
  it ("shorten text in those events"). Rare; when it happens, tighten that event's rows.
- Sound effects/interjections: （コンコン） -> (knock knock), ざわざわ -> (murmuring),
  はっはっは -> Hahaha!, …… -> "...", ！！ alone -> "!!". `『』`/`「」`/`“”` -> double quotes.
  ７つ etc. (full-width digits) -> words or ASCII digits as natural ("seven").
- Tutorial text (no nameplate, buttons): Ａボタン -> "the A Button", Ｌボタン "L", Ｒボタン "R",
  十字ボタン "the +Control Pad". Never write "L1"/"R1". Screen/command names as in the glossary
  (甲板画面 Deck Screen, 情報 Info, 戦闘 Battle, 探索 Search...).

- Story terms: 覇者の証 = Victor's Mark, 『証』 alone = "the Mark", 覇者 = Victor (one who holds
  all the Marks); 無敵艦隊 = the Invincible Armada. Mate duties as in the glossary (操帆手
  Sailhand, 操舵手 Helmsman, 測量士 Surveyor, 見張り Lookout, 砲撃手 Gunner). FI提督 -> Admiral {FI}.
  エシュタード = "the Estado" (Portuguese: a trade domain; 交易圏 explains it), ヘラルド = Gerardo
  (Julio's son, Christina's father). X商会 in dialogue = "the X Company" (the glossary's "X Co." is the short UI form).

**Main cast voices** (keep consistent across chunks):
- Rafael (0): the player in SC0; earnest, kind, upbeat Portuguese teen. Calls Claudio クラウ = "Clau".
- Claudio (5): brash, quick-tempered sailor, rough talk, secretly easily scared; calls Rafael by name.
- Julio (6): old veteran sailor (じゃ/のう): knowledgeable, "Hmm", grandfatherly.
- Christina (7): lively, outspoken young woman, teases the men.
- Arcadius (8): polite, formal, studious young Greek; precise speech. **Secret: Arcadius is a
  woman, real name Eirene (エイレネ)**, disguised as a man. Follow the Japanese: lines that say
  エイレネ or 彼女 use "Eirene"/"she"; where the Japanese keeps up the disguise (アルカディウス,
  彼), keep "Arcadius"/"he". Her own speech: neutral polite while disguised, softer and
  feminine (あら, ～わ) once the secret is out between them.
- Jenas (4): polite, a bit of a worrier ("This doesn't look good...").
- Gerhard (16): stern old master, calls the hero 貴様 -> blunt "you", "fool".
- Generic speakers (Henchman = a crewman/subordinate; Guild Boss, Tavern Owner, Harbor Boss...):
  natural voices fitting the role.

Check: `.venv/bin/python tools/tl.py check sc0` (from the project root). Fix every problem it
lists for your ids (codes, width, lines, non-ASCII, event size).

## SC1-3 (the other three protagonists)
Same format as SC0, files `work/sc_todo/scN_NN.txt` -> `tl/scN/NN.txt`. Many lines are shared
with SC0 and already translated: they appear in your todo file as context only,

    (done) Gerhard: Understood.

Do **not** write anything for `(done)` lines (they have no id); just keep your lines consistent
with them (they are the same scene). Translate every `@id` block.
The player is not Rafael: `{FI}` = the protagonist's given name, `{FA}` family name.
**SC2 and SC3 protagonists are women**: "she/her"; FI殿/FI様 -> "Lady {FI}", FIさん -> "{FI}" (from
formal strangers "Ms. {FI}"); where the Japanese uses
様/さん in a respectful way, never "boy"/"lad"; 提督 is still "Admiral".

**SC1: Hodrum Joachim Bergstrom** (Swedish admiral in royal service; 30s): stern, disciplined,
terse military speech, dry; uses "I" (俺/私). Crew:
- Gerhard (16): Hodrum's loyal second-in-command here (not the old master of SC0): formal,
  "Admiral", "sir".
- Charles (18): nervous, "logically" minded Frenchman, panics, then surprisingly capable.
- Sera (24): mysterious girl rescued at sea, few words, halting ("Here... I know... this place").
- Cesare (13): eager, over-formal ("であります" -> "sir!", "reporting, sir!").
- Carlo (19): kind, observant merchant (notices people's health); Manuel (23): rough sailor.
- Christina (7), Julio (6): as in SC0.

**SC2: Lil Argot** (Dutch merchant girl, Amsterdam; teen): confident, cheeky, money-minded,
quick-tempered but warm ("Heh, that's skill!"). Crew:
- Camille (9): her laid-back, sensible childhood friend; mild, a little reluctant.
- Fernando (20): cocky, rough-talking sailor; knows trade and politics.
- Emilio (14): young cook boy, childish, always hungry (おいら -> plain "I", kid speech).
- Julian (26, ユリアン Julian Lopez; not ジュリアン = Julien Vermeer, a traitor merchant): flamboyant romantic, flirts with every woman; born and raised in Ming.
- Gerhard, Christina, Julio, Carlo: as above.

**SC3: Maria Huamei Li** (commander of the Ming navy; young woman): dignified, decisive,
proud, kind underneath; soft feminine endings (わ/よ) -> polished, firm English. Crew:
- Xian (10): her old advisor (じゃ): elderly, wise, "Hmm", grandfatherly.
- Yukihisa (12): formal Japanese samurai (as in SC0).
- Jam (11): slangy French rogue ("っス" -> "yeah, boss", casual and brash).
- Angelo (15): passionate, hot-blooded Italian; romantic.
- Ian (21): polite, devoted officer, calls her "Admiral"/"my lady".
- Richard (74): businesslike English merchant/official.

`♪` at the end of a line: drop it or use "!" (no symbol). **Symbol speech** (SC): runs of ○×△□◎▲◇ are an alien language or garbled shouting: keep those
symbols exactly as in the Japanese (they're allowed), translate only the normal words around them.
