"""usage: gfxprev.py out.png [file.pxl ...] [--crop x,y,w,h] [--scale n]
Original (left) and gfx.EDITS applied (right) for each file (default: every edited file)."""
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import gfx  # noqa: E402
import pxl  # noqa: E402

args = [a for a in sys.argv[2:] if not a.startswith('--')]
opt = dict(a[2:].split('=') for a in sys.argv[2:] if a.startswith('--'))
scale = int(opt.get('scale', 3))
crop = tuple(map(int, opt['crop'].split(','))) if 'crop' in opt else None
files = args or list(gfx.EDITS)
rows = []
for f in files:
    raw = open(os.path.join('work/fs', f), 'rb').read()
    img = gfx.TileImg(raw, gfx.TILED[f]) if f in gfx.TILED else gfx.Img(raw)
    orig = gfx.TileImg(raw, gfx.TILED[f]) if f in gfx.TILED else None
    for e in gfx.EDITS.get(f, []):
        gfx.edit(img, e)
    pair = []
    for d in (raw, img.save()):
        if orig:
            t = gfx.TileImg(d, gfx.TILED[f])
            im = pxl.to_image(dict(bpp=4, w=t.w, h=t.h, pal=t.pal, idx=bytes(t.px))).convert('RGB')
        else:
            im = pxl.to_image(pxl.parse(d)).convert('RGB')
        if crop:
            im = im.crop((crop[0], crop[1], crop[0] + crop[2], crop[1] + crop[3]))
        pair.append(im.resize((im.width * scale, im.height * scale), Image.NEAREST))
    rows.append(pair)
W = max(a.width + b.width + 8 for a, b in rows)
H = sum(a.height + 8 for a, _ in rows)
out = Image.new('RGB', (W, H), (255, 0, 255))
y = 0
for a, b in rows:
    out.paste(a, (0, y)); out.paste(b, (a.width + 8, y)); y += a.height + 8
out.save(sys.argv[1])
print(sys.argv[1], out.size)
