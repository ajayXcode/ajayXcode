import os
import numpy as np
from PIL import Image, ImageFilter
from scipy.ndimage import label, binary_dilation, sobel

DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(DIR)
PORTRAIT_PATH = os.path.join(REPO_ROOT, "assets", "portrait.jpg")
OUT_SVG = os.path.join(REPO_ROOT, "ajay-ascii.svg")

im = Image.open(PORTRAIT_PATH)
crop_box = (150, 90, 874, 830)
cropped = im.crop(crop_box)
arr = np.array(cropped)

# Full outer background removal (yellow background + white sticker border)
is_yellow = (arr[:, :, 0] > 175) & (arr[:, :, 1] > 135) & (arr[:, :, 2] < 110)
labeled_y, _ = label(is_yellow)
yellow_bg = (labeled_y == labeled_y[0, 0])
is_white = (arr[:, :, 0] > 230) & (arr[:, :, 1] > 230) & (arr[:, :, 2] > 230)
dilated_yellow = binary_dilation(yellow_bg, iterations=25)
full_bg = yellow_bg | (is_white & dilated_yellow)

# Smooth image to eliminate halftone raster screen dots
gray = cropped.convert('L')
smooth = gray.filter(ImageFilter.GaussianBlur(radius=2.5))
smooth_arr = np.array(smooth, dtype=float)
smooth_arr[full_bg] = 255.0

# Extract contours / facial edges (jawline, nose, eyes, lips, ears)
sx = sobel(smooth_arr, axis=1)
sy = sobel(smooth_arr, axis=0)
edges = np.hypot(sx, sy)

cols = 120
rows = 96
pil_smooth = Image.fromarray(smooth_arr.astype(np.uint8))
resized_smooth = np.array(pil_smooth.resize((cols, rows), Image.Resampling.LANCZOS))

pil_edges = Image.fromarray(np.clip(edges, 0, 255).astype(np.uint8))
resized_edges = np.array(pil_edges.resize((cols, rows), Image.Resampling.LANCZOS))

pil_bg = Image.fromarray((full_bg * 255).astype(np.uint8))
resized_bg = np.array(pil_bg.resize((cols, rows), Image.Resampling.NEAREST)) > 128

RAMP = "@%#*+=-"

svg_rows = []
for y in range(rows):
    line_chars = []
    # Smooth bust fade out below row 76 so there are no solid zebra blocks
    fade_prob = max(0.0, 1.0 - (y - 76) / 10.0) if y > 76 else 1.0
    
    for x in range(cols):
        if resized_bg[y, x] or fade_prob <= 0.0:
            line_chars.append(" ")
        else:
            val = resized_smooth[y, x]
            edge = resized_edges[y, x]
            
            # Dark hair and deep shadow features
            if val < 95:
                if y > 74 and (x + y) % 2 == 1:
                    line_chars.append(" ")
                else:
                    norm = val / 95.0
                    idx = int(norm * 4)
                    line_chars.append(RAMP[max(0, min(3, idx))])
            # Facial features (eyebrows, eyes, mustache, mouth, jawline, ears)
            elif val < 125 and edge > 22:
                line_chars.append("*" if val < 110 else "+")
            # Clear anatomical contours
            elif edge > 48:
                line_chars.append("+")
            else:
                # Clean paper skin (cheeks, forehead, nose bridge): pure whitespace!
                # NO horizontal lines or scan-line grid!
                line_chars.append(" ")
            
    line = "".join(line_chars).ljust(cols)
    clean_line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    y_pos = 37.0 + y * 8.333
    svg_rows.append(f'<text xml:space="preserve" x="20" y="{y_pos:.1f}" textLength="800.0" lengthAdjust="spacing">{clean_line}</text>')

with open(OUT_SVG, 'w', encoding='utf-8') as f:
    f.write('<svg xmlns="http://www.w3.org/2000/svg" width="840" height="880">\n')
    f.write('\n'.join(svg_rows))
    f.write('\n</svg>\n')

print(f"Successfully generated clean line-art {OUT_SVG} without scan lines!")
