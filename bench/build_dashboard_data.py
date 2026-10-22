"""Build results/dashboard_data.json: aggregates + per-image evidence (with thumbnails) for the dashboard."""
import base64, io, json, re, unicodedata
from collections import defaultdict
from pathlib import Path
import jiwer
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ENGINES = ["indra", "surya", "paddleocr", "easyocr", "tesseract", "doctr", "rapidocr"]
META = {
    "indra":     dict(name="Indra OCR", license="Apache-2.0 code, OpenRAIL-M weights", note="1M-param ONNX model, CPU", ver="indra-ocr (PyPI)"),
    "surya":     dict(name="Surya", license="GPL-3.0 code, OpenRAIL-M weights", note="Transformer, run on a subsample", ver="surya-ocr 0.17"),
    "paddleocr": dict(name="PaddleOCR", license="Apache-2.0", note="PP-OCRv5 per-script models", ver="paddleocr 3.4.1"),
    "easyocr":   dict(name="EasyOCR", license="Apache-2.0", note="CRAFT + CRNN", ver="easyocr 1.7.2"),
    "tesseract": dict(name="Tesseract", license="Apache-2.0", note="LSTM, tessdata_fast packs", ver="Tesseract 5.4"),
    "doctr":     dict(name="docTR", license="Apache-2.0", note="Latin-script models only", ver="python-doctr 1.1.0"),
    "rapidocr":  dict(name="RapidOCR", license="Apache-2.0", note="ONNX PP-OCR, Latin/Chinese only", ver="rapidocr-onnxruntime"),
}
LANGS = {"eng": "English", "hin": "Hindi", "tam": "Tamil", "ben": "Bengali", "mal": "Malayalam", "kan": "Kannada",
         "tel": "Telugu", "mar": "Marathi", "guj": "Gujarati", "ori": "Odia", "pan": "Punjabi", "asm": "Assamese",
         "kas": "Kashmiri", "mai": "Maithili", "mni": "Manipuri (Meitei)", "nep": "Nepali", "san": "Sanskrit",
         "sat": "Santali", "snd": "Sindhi", "urd": "Urdu", "lus": "Mizo"}
COND = {  # condition -> datasets
    "printed": ["flores_synth", "synthetic"],
    "printed_bench": ["printed_indic"],
    "printed_deg": ["degraded_printed"],
    "handwritten": ["handwritten"],
    "handwritten_deg": ["degraded_handwritten"],
    "forms": ["funsd"],
    "handwritten_wild": ["handwritten_wild"],
}
DS_COND = {d: c for c, ds in COND.items() for d in ds}
CLEAN_OF = {"degraded_printed": "flores_synth", "degraded_handwritten": "handwritten"}
DS_LABEL = {"flores_synth": "FLORES-200 text, rendered", "printed_indic": "OCR-Bench1000 printed lines (real corpus)", "synthetic": "Synthetic English",
            "degraded_printed": "FLORES-200 text, rendered + degraded", "handwritten": "IIIT-INDIC-HW-WORDS (handwritten)",
            "degraded_handwritten": "IIIT-INDIC-HW-WORDS + degraded", "funsd": "FUNSD forms (full page)",
            "handwritten_wild": "IIIT-INDIC-HW-WILD word crops (no labels)"}

norm = lambda t: re.sub(r"\s+", " ", unicodedata.normalize("NFC", t)).strip()
def score(ref, hyp):
    ref, hyp = norm(ref), norm(hyp)
    return (min(jiwer.cer(ref, hyp), 1.0), min(jiwer.wer(ref, hyp), 1.0)) if ref else None

raw = {e: json.loads((ROOT / f"results/raw/{e}.json").read_text(encoding="utf-8")) for e in ENGINES if (ROOT / f"results/raw/{e}.json").exists()}
images = {}
for p in sorted((ROOT / "data").glob("*/images/*.png")):
    images[f"{p.parent.parent.name}/{p.stem}"] = p

def lang_of(key):
    ds, stem = key.split("/"); return "eng" if ds == "funsd" else stem.split("_")[0]

res = defaultdict(dict)   # key -> engine -> dict
for e, d in raw.items():
    for key, r in d.items():
        if key not in images: continue
        ds, stem = key.split("/")
        gtp = ROOT / "data" / ds / "gt" / f"{stem}.txt"
        err = r["error"]
        s_ = None if (err or not gtp.exists()) else score(gtp.read_text(encoding="utf-8"), r["text"])
        status = "error" if err else ("ok" if s_ else "unlabelled")
        res[key][e] = dict(cer=s_ and round(s_[0], 4), wer=s_ and round(s_[1], 4), sec=round(r["sec"], 2), hyp=r["text"][:400],
                           status=status, err=err and err[:140], mode=r.get("mode", "native"))

def mean(xs): xs = [x for x in xs if x is not None]; return sum(xs) / len(xs) if xs else None
def r4(x): return None if x is None else round(x, 4)

cells = defaultdict(dict)   # cond -> lang -> engine -> cell
for key, per in res.items():
    c = DS_COND[key.split("/")[0]]; l = lang_of(key)
    for e, r in per.items():
        cells[c].setdefault(l, {}).setdefault(e, []).append(r)
heat = {}
for c, langs in cells.items():
    heat[c] = {}
    for l, per in langs.items():
        heat[c][l] = {}
        for e, rs in per.items():
            ok = [r for r in rs if r["status"] == "ok"]
            modes = [r["mode"] for r in rs]
            heat[c][l][e] = dict(cer=r4(mean(r["cer"] for r in ok)), wer=r4(mean(r["wer"] for r in ok)), n=len(ok),
                                 ran=len(rs), err=sum(r["status"] == "error" for r in rs),
                                 empty=sum(1 for r in rs if r["status"] != "error" and not r["hyp"].strip()),
                                 mode=max(set(modes), key=modes.count), sec=r4(mean(r["sec"] for r in rs if r["status"] != "error")))
# images each language has per condition (denominator for "not run")
tot = defaultdict(lambda: defaultdict(int))
for key in images:
    tot[DS_COND[key.split("/")[0]]][lang_of(key)] += 1

# paired clean vs degraded
paired = {}
for deg, cl in CLEAN_OF.items():
    cond = DS_COND[deg]; paired[cond] = {}
    for e in raw:
        a, b = [], []
        for key in images:
            if not key.startswith(deg + "/"): continue
            ck = f"{cl}/{key.split('/')[1]}"
            x, y = res.get(ck, {}).get(e), res.get(key, {}).get(e)
            if x and y and x["cer"] is not None and y["cer"] is not None: a.append(x["cer"]); b.append(y["cer"])
        if a: paired[cond][e] = dict(clean=r4(mean(a)), degraded=r4(mean(b)), n=len(a))

# evidence samples
def thumb(path, w=560):
    im = Image.open(path).convert("RGB")
    if im.width > w: im = im.resize((w, max(int(im.height * w / im.width), 1)), Image.LANCZOS)
    b = io.BytesIO(); im.save(b, "JPEG", quality=74); return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()

samples = []
bykey = defaultdict(list)
for key in images: bykey[(DS_COND[key.split("/")[0]], lang_of(key))].append(key)
for (c, l), keys in sorted(bykey.items()):
    ranked = sorted(keys, key=lambda k: (-sum(1 for r in res.get(k, {}).values() if r["status"] != "error"), k))
    k_n = 5 if c == "handwritten_wild" else 4 if c.startswith("handwritten") else (3 if c == "forms" else 2)
    if l in ("hin", "tam", "tel", "kan"): k_n = 8   # spotlight languages get more evidence
    for key in ranked[:k_n]:
        ds, stem = key.split("/")
        gp = ROOT / "data" / ds / "gt" / f"{stem}.txt"; gt = gp.read_text(encoding="utf-8") if gp.exists() else None
        s = dict(id=key, cond=c, lang=l, dataset=ds, ref=gt[:400] if gt is not None else None, img=thumb(images[key], 900 if c == "forms" else 560),
                 results={e: res[key][e] for e in raw if e in res.get(key, {})})
        if ds in CLEAN_OF and f"{CLEAN_OF[ds]}/{stem}" in images: s["orig"] = thumb(images[f"{CLEAN_OF[ds]}/{stem}"])
        samples.append(s)

data = dict(engines=ENGINES, meta=META, langs=LANGS, dsLabel=DS_LABEL, cond=list(COND), heat=heat,
            total={c: dict(v) for c, v in tot.items()}, paired=paired, samples=samples,
            counts={e: sum(1 for k in res if e in res[k]) for e in raw}, nImages=len(images))
(ROOT / "results/dashboard_data.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
print(len(samples), "samples;", (ROOT / "results/dashboard_data.json").stat().st_size // 1024, "KB;", data["counts"])
