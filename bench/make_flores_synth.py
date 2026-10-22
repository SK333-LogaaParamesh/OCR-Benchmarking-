# Printed-text line images rendered with headless Edge (proper Indic shaping / RTL) from FLORES-200 devtest
# sentences: real text, synthetic rendering, for languages with no public OCR set. NOT handwriting.
import random, subprocess, tempfile, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from PIL import Image, ImageChops, ImageFilter
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
SRC = Path("data_src/flores/flores200_dataset/devtest")
LANGS = {"asm": "asm_Beng", "ben": "ben_Beng", "guj": "guj_Gujr", "hin": "hin_Deva", "kan": "kan_Knda",
         "kas": "kas_Arab", "mai": "mai_Deva", "mal": "mal_Mlym", "mni": "mni_Beng", "mar": "mar_Deva",
         "nep": "npi_Deva", "ori": "ory_Orya", "pan": "pan_Guru", "san": "san_Deva", "sat": "sat_Olck",
         "snd": "snd_Arab", "tam": "tam_Taml", "tel": "tel_Telu", "urd": "urd_Arab", "lus": "lus_Latn"}
random.seed(3)
out = Path("data/flores_synth"); (out / "images").mkdir(parents=True, exist_ok=True); (out / "gt").mkdir(exist_ok=True)
tmp = Path(tempfile.mkdtemp())
jobs = []
for code, fl in LANGS.items():
    lines = [l.strip() for l in (SRC / f"{fl}.devtest").read_text(encoding="utf-8").splitlines() if 25 <= len(l.strip()) <= 70]
    for i, line in enumerate(random.sample(lines, 6)): jobs.append((code, i, line, "Arab" in fl))

def render(job):
    code, i, line, rtl = job
    h = tmp / f"{code}_{i}.html"
    h.write_text(f'<meta charset="utf-8"><body style="margin:0;background:#fff"><div dir="{"rtl" if rtl else "ltr"}" '
                 f'style="font:40px \'Nirmala UI\',\'Segoe UI\';padding:30px;width:1800px;white-space:nowrap">{line}</div>', encoding="utf-8")
    png = tmp / f"{code}_{i}.png"
    # headless Edge sometimes hangs after writing the screenshot, so poll for the file and kill it
    proc = subprocess.Popen([EDGE, "--headless=new", "--disable-gpu", f"--screenshot={png}", "--window-size=1900,120",
                             "--hide-scrollbars", f"--user-data-dir={tmp / (code + str(i) + '_p')}", "--no-first-run", h.as_uri()],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        if png.exists() and png.stat().st_size > 0: time.sleep(0.5); break
        time.sleep(0.5)
    subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
    img = Image.open(png).convert("L")
    bbox = ImageChops.invert(img).getbbox()
    img = img.crop((max(bbox[0] - 30, 0), max(bbox[1] - 25, 0), bbox[2] + 30, bbox[3] + 25))
    if i % 2: img = img.filter(ImageFilter.GaussianBlur(1.0))
    img.convert("RGB").save(out / "images" / f"{code}_{i}.png")
    (out / "gt" / f"{code}_{i}.txt").write_text(line, encoding="utf-8")

with ThreadPoolExecutor(4) as ex: list(ex.map(render, jobs))
print(len(list((out / "images").glob("*.png"))), "images")
