"""usage: grid.py out.png image.png x y w h [scale=4]  zoomed crop with an 8 px grid (labels every 16 px)"""
import sys
from PIL import Image, ImageDraw
src, (x, y, w, h) = Image.open(sys.argv[2]).convert('RGB'), map(int, sys.argv[3:7])
s = int(sys.argv[7]) if len(sys.argv) > 7 else 4
im = src.crop((x, y, x + w, y + h)).resize((w * s, h * s), Image.NEAREST)
out = Image.new('RGB', (w * s + 30, h * s + 14), (255, 255, 255))
out.paste(im, (30, 14))
d = ImageDraw.Draw(out)
for gx in range(x - x % 8, x + w + 1, 8):
    if gx < x: continue
    X = 30 + (gx - x) * s
    d.line([(X, 14), (X, 14 + h * s)], fill=(255, 0, 255) if gx % 16 == 0 else (0, 200, 255))
    if gx % 16 == 0: d.text((X + 1, 0), str(gx), fill=(0, 0, 0))
for gy in range(y - y % 8, y + h + 1, 8):
    if gy < y: continue
    Y = 14 + (gy - y) * s
    d.line([(30, Y), (30 + w * s, Y)], fill=(255, 0, 255) if gy % 16 == 0 else (0, 200, 255))
    if gy % 16 == 0: d.text((0, Y + 1), str(gy), fill=(0, 0, 0))
out.save(sys.argv[1])
