import os
import numpy as np
from PIL import Image, ImageFilter
from scipy.ndimage import label

DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(DIR)
PORTRAIT_PATH = os.path.join(REPO_ROOT, "assets", "portrait.jpg")
OUT_SVG = os.path.join(REPO_ROOT, "ajay-ascii.svg")

im = Image.open(PORTRAIT_PATH)
crop_box = (135, 80, 885, 880)
cropped = im.crop(crop_box)
arr = np.array(cropped)

# Precise outer background detection (flood-filled yellow + white sticker border)
is_yellow = (arr[:, :, 0] > 175) & (arr[:, :, 1] > 135) & (arr[:, :, 2] < 110)
is_white = (arr[:, :, 0] > 235) & (arr[:, :, 1] > 235) & (arr[:, :, 2] > 235)
bg = is_yellow | is_white

labeled, _ = label(bg)
outer_bg = (labeled == labeled[0, 0])

gray = cropped.convert('L')
smooth = gray.filter(ImageFilter.GaussianBlur(radius=1.5))
smooth_arr = np.array(smooth, dtype=float)
smooth_arr[outer_bg] = 255.0

cols = 120
rows = 96
pil_smooth = Image.fromarray(smooth_arr.astype(np.uint8))
resized_smooth = np.array(pil_smooth.resize((cols, rows), Image.Resampling.LANCZOS))

pil_bg = Image.fromarray((outer_bg * 255).astype(np.uint8))
resized_bg = np.array(pil_bg.resize((cols, rows), Image.Resampling.NEAREST)) > 128

# Rich, dark ASCII ramp: dense ink glyphs
RAMP = "@%#*+=-:. "

svg_rows = []
for y in range(rows):
    line_chars = []
    for x in range(cols):
        if resized_bg[y, x]:
            line_chars.append(" ")
        else:
            val = resized_smooth[y, x]
            norm = min(1.0, val / 230.0)
            norm = norm ** 1.35  # Rich contrast curve: deep hair/hoodie, clear dark features
            idx = int(norm * (len(RAMP) - 1))
            line_chars.append(RAMP[max(0, min(len(RAMP) - 1, idx))])
            
    line = "".join(line_chars).ljust(cols)
    clean_line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    y_pos = 37.0 + y * 8.333
    svg_rows.append(f'<text xml:space="preserve" x="20" y="{y_pos:.1f}" textLength="800.0" lengthAdjust="spacing">{clean_line}</text>')

with open(OUT_SVG, 'w', encoding='utf-8') as f:
    f.write('<svg xmlns="http://www.w3.org/2000/svg" width="840" height="880">\n')
    f.write('\n'.join(svg_rows))
    f.write('\n</svg>\n')

print(f"Successfully generated {OUT_SVG} with dark, defined vector ASCII portrait!")
