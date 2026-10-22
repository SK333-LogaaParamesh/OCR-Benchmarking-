# Harsh degradation of existing sets (same ground truth). Each image gets 4 random effects at high strength.
import io, random
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter, ImageDraw

rng = random.Random(11); nrng = np.random.default_rng(11)

def blur(im):      return im.filter(ImageFilter.GaussianBlur(rng.uniform(1.4, 2.4)))
def noise(im):
    a = np.asarray(im, np.float32) + nrng.normal(0, rng.uniform(35, 60), (im.height, im.width, 1)); return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8).repeat(3, 2) if a.shape[2] == 1 else np.clip(a, 0, 255).astype(np.uint8))
def saltpepper(im):
    a = np.array(im); m = nrng.random(a.shape[:2]); a[m < 0.04] = 0; a[m > 0.96] = 255; return Image.fromarray(a)
def lowres(im):
    s = rng.uniform(0.5, 0.65); w, h = im.size
    return im.resize((max(int(w * s), 8), max(int(h * s), 8)), Image.BILINEAR).resize((w, h), Image.BILINEAR)
def jpeg(im):
    b = io.BytesIO(); im.save(b, "JPEG", quality=rng.randint(6, 14)); return Image.open(b).convert("RGB")
def rotate(im):    return im.rotate(rng.choice([-1, 1]) * rng.uniform(7, 14), expand=True, fillcolor=(255, 255, 255), resample=Image.BICUBIC)
def perspective(im):
    # pad first so the warp tilts the page without cutting text off
    pad = int(im.height * 0.6); canvas = Image.new("RGB", (im.width + 2 * pad, im.height + 2 * pad), (255, 255, 255)); canvas.paste(im, (pad, pad)); im = canvas
    w, h = im.size; ph = im.height * 0.1; pw = w * 0.02; d = lambda m: rng.uniform(-m, m)
    q = [d(pw), d(ph), d(pw), h + d(ph), w + d(pw), h + d(ph), w + d(pw), d(ph)]  # NW, SW, SE, NE
    return im.transform((w, h), Image.QUAD, q, Image.BICUBIC, fillcolor=(255, 255, 255))
def shade(im):
    a = np.asarray(im, np.float32); w = im.width
    g = np.linspace(rng.uniform(0.5, 0.7), 1.0, w)[None, :, None]; g = g if rng.random() < .5 else g[:, ::-1]
    return Image.fromarray(np.clip(a * g, 0, 255).astype(np.uint8))
def stains(im):
    im = im.copy(); d = ImageDraw.Draw(im, "RGBA")
    for _ in range(rng.randint(2, 4)):
        x, y = rng.randrange(im.width), rng.randrange(im.height); r = rng.randint(8, 22)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(90, 90, 90, rng.randint(60, 130)))
    for _ in range(rng.randint(1, 2)):
        y = rng.randrange(im.height); d.line([0, y, im.width, y + rng.randint(-8, 8)], fill=(40, 40, 40, 150), width=2)
    return im
def erode(im):     return im.filter(ImageFilter.MaxFilter(3))   # thickens/merges dark strokes like ink bleed

from PIL import ImageChops
def autocrop(im, m=20):
    bb = ImageChops.invert(im.convert('L').point(lambda v: 255 if v < 235 else 0)).getbbox()
    bb = ImageChops.invert(im.convert('L').point(lambda v: 0 if v < 235 else 255)).getbbox() or (0, 0, *im.size)
    return im.crop((max(bb[0] - m, 0), max(bb[1] - m, 0), min(bb[2] + m, im.width), min(bb[3] + m, im.height)))

GEOM = (rotate, perspective)
FX = [blur, noise, saltpepper, lowres, jpeg, rotate, perspective, shade, stains, erode]
for src, dst in (("flores_synth", "degraded_printed"), ("handwritten", "degraded_handwritten")):
    out = Path("data") / dst; (out / "images").mkdir(parents=True, exist_ok=True); (out / "gt").mkdir(exist_ok=True)
    for p in sorted((Path("data") / src / "images").glob("*.png")):
        im = Image.open(p).convert("RGB")
        geom = rng.choice(GEOM); pool = [f for f in FX if f not in GEOM]
        fx = rng.sample(pool, 3)
        im = geom(im); im = autocrop(im, 25)          # geometric first, then crop to content
        for f in fx: im = f(im)
        im.convert("RGB").save(out / "images" / f"{p.stem}.png")
        (out / "gt" / f"{p.stem}.txt").write_bytes((Path("data") / src / "gt" / f"{p.stem}.txt").read_bytes())
    print(dst, len(list((out / "images").glob("*.png"))))
