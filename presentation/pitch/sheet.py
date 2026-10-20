"""Contact sheet of out/pages/pNN.png -> out/sheet.png (3 columns)."""
from PIL import Image
import glob, sys
files = sorted(glob.glob("out/pages/p*.png"))
W, H, cols, gap = 640, 360, 3, 16
rows = (len(files) + cols - 1) // cols
sheet = Image.new("RGB", (cols * W + (cols + 1) * gap, rows * H + (rows + 1) * gap), (32, 36, 46))
for i, f in enumerate(files):
    im = Image.open(f).convert("RGB").resize((W, H), Image.LANCZOS)
    sheet.paste(im, (gap + (i % cols) * (W + gap), gap + (i // cols) * (H + gap)))
sheet.save(sys.argv[1] if len(sys.argv) > 1 else "out/sheet.png")
print(len(files))
