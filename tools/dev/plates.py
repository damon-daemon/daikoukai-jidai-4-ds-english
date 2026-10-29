"""usage: plates.py file.pxl [...]   (paths under work/fs/)
Bounding boxes of the stone label plates on teal info panels: connected regions of non-teal
pixels (R >= B), 8..200 px wide, 8..24 px tall."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import pxl  # noqa: E402

for f in sys.argv[1:]:
    p = pxl.parse(open(os.path.join('work/fs', f), 'rb').read())
    w, h, pal = p['w'], p['h'], p['pal']
    stone = [pal[i][0] >= pal[i][2] and sum(pal[i]) > 150 for i in range(len(pal))]
    m = [stone[v] for v in p['idx'][:w * h]]
    seen = [False] * (w * h)
    out = []
    for s in range(w * h):
        if not m[s] or seen[s]:
            continue
        st, comp = [s], []
        seen[s] = True
        while st:
            q = st.pop(); comp.append(q)
            x, y = q % w, q // w
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and m[ny * w + nx] and not seen[ny * w + nx]:
                    seen[ny * w + nx] = True; st.append(ny * w + nx)
        xs = [q % w for q in comp]; ys = [q // w for q in comp]
        bx, by, bw, bh = min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
        if 8 <= bw <= 200 and 8 <= bh <= 24 and len(comp) > bw * bh // 3:
            out.append((by, bx, bw, bh))
    print(f, ' '.join('(%d, %d, %d, %d)' % (x, y, ww, hh) for y, x, ww, hh in sorted(out)))
