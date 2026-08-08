from PIL import Image, ImageDraw
import os, math

img = Image.new('RGBA', (512, 512), (30, 30, 35, 255))
draw = ImageDraw.Draw(img)
cx, cy = 256, 256
for i in range(36):
    a = 360 / 36 * i
    ang = math.radians(a)
    inner_r = 175
    outer_r = 210
    x1 = int(cx + math.cos(ang) * inner_r)
    y1 = int(cy + math.sin(ang) * inner_r)
    x2 = int(cx + math.cos(ang) * outer_r)
    y2 = int(cy + math.sin(ang) * outer_r)
    color = (80, 255, 120, 255) if i % 4 < 2 else (80, 80, 90, 255)
    draw.line((x1, y1, x2, y2), fill=color, width=12)

draw.ellipse((90, 90, 422, 422), outline=(30, 255, 95, 255), width=2)
img.save(os.path.join(os.getcwd(), 'scan_spinner.png'))
