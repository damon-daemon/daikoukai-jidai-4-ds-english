# strw.py word ... : pixel width of strings in the game's VWF font (tools/font.py)
import sys; sys.path.insert(0, 'tools')
import font
for s in sys.argv[1:]: print('%3d %s' % (font.width(s), s))
