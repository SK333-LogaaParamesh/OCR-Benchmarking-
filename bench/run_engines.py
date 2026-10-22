"""Run one OCR engine over every image in data/*/images, for every language, using only that engine.
Usage: python run_engines.py <engine> [--per-group N] [--limit N]
Writes results/raw/<engine>.json: {"<dataset>/<stem>": {text, sec, error, mode, model}}.

mode = how the engine was applied to that language:
  native  a model trained for the language
  script  a model for a different language written in the same script (closest available)
  none    nothing relevant exists; the engine's default (Latin/English) model is run anyway
No language-model, vision-model or post-correction step is used anywhere in this file."""
import json, os, sys, time, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("TESSDATA_PREFIX", str(ROOT / "tessdata"))
LANGS = "eng hin tam ben mal kan tel mar guj ori pan asm kas mai mni nep san sat snd urd lus".split()
LANG = {c: c for c in LANGS}; LANG["funsd"] = "eng"

# language -> (model spec, mode) per engine
MODES = {
    "tesseract": {**{l: (l, "native") for l in "eng asm ben guj hin kan mal mar nep ori pan san snd tam tel urd".split()},
                  "kas": ("urd", "script"), "mai": ("hin", "script"), "mni": ("ben", "script"),
                  "sat": ("eng", "none"), "lus": ("eng", "script")},
    "easyocr": {"eng": ("en", "native"), "hin": ("hi", "native"), "mar": ("mr", "native"), "nep": ("ne", "native"),
                "ben": ("bn", "native"), "asm": ("as", "native"), "tam": ("ta", "native"), "tel": ("te", "native"),
                "kan": ("kn", "native"), "urd": ("ur", "native"), "mai": ("mai", "native"), "mni": ("bn", "script"),
                "san": ("sa", "native"), "kas": ("ur", "script"), "snd": ("ur", "script"), "lus": ("en", "script"),
                "mal": ("en", "none"), "guj": ("en", "none"), "ori": ("en", "none"), "pan": ("en", "none"), "sat": ("en", "none")},
    "paddleocr": {"eng": ("en", "native"), "hin": ("hi", "native"), "mar": ("mr", "native"), "nep": ("ne", "native"),
                  "mai": ("mai", "native"), "san": ("sa", "native"), "tam": ("ta", "native"), "tel": ("te", "native"),
                  "kan": ("ka", "native"), "urd": ("ur", "native"), "snd": ("sd", "native"),
                  "kas": ("ar", "script"), "lus": ("en", "script"),
                  **{l: ("en", "none") for l in "ben asm mni mal guj ori pan sat".split()}},
    "doctr": {"eng": ("default", "native"), "lus": ("default", "script"), **{l: ("default", "none") for l in LANGS if l not in ("eng", "lus")}},
    "rapidocr": {"eng": ("default", "native"), "lus": ("default", "script"), **{l: ("default", "none") for l in LANGS if l not in ("eng", "lus")}},
    "surya": {**{l: ("multi", "native") for l in "eng asm ben guj hin kan mal mar nep ori pan san snd tam tel urd".split()},
              "kas": ("multi", "script"), "mai": ("multi", "script"), "mni": ("multi", "script"), "lus": ("multi", "script"), "sat": ("multi", "none")},
    "indra": {**{l: ("multi", "native") for l in "eng hin mar nep ben tam tel kan mal guj pan ori urd lus".split()},
              **{l: ("multi", "script") for l in "asm mai san kas snd mni".split()}, "sat": ("multi", "none")},
}

def images(limit=None, per_group=None):
    items = sorted((ROOT / "data").glob("*/images/*.png"))
    if per_group:   # evenly spaced N images from each (dataset, language) group
        groups = {}
        for p in items: groups.setdefault((p.parent.parent.name, LANG[p.stem.split("_")[0]]), []).append(p)
        items = []
        for g in groups.values():
            n = len(g); idx = sorted({round(i * (n - 1) / max(per_group - 1, 1)) for i in range(min(per_group, n))})
            items += [g[i] for i in idx]
        items.sort()
    if limit: items = items[:limit]
    for p in items:
        yield f"{p.parent.parent.name}/{p.stem}", p, LANG[p.stem.split("_")[0]]

def make_tesseract():
    import pytesseract
    from PIL import Image
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    # Tesseract's default layout mode expects a full page and returns nothing on single lines, so use the documented
    # mode for the input type: 8 = single word, 7 = single line, 3 = full page (FUNSD forms).
    PSM = {"handwritten": 8, "degraded_handwritten": 8, "handwritten_wild": 8, "funsd": 3}
    def run(p, l):
        code = MODES["tesseract"][l][0]
        psm = PSM.get(Path(p).parent.parent.name, 7)
        return pytesseract.image_to_string(Image.open(p), lang="eng" if code == "eng" else f"{code}+eng", config=f"--psm {psm}").strip()
    return run

def make_easyocr():
    import easyocr
    readers = {}
    def run(p, l):
        code = MODES["easyocr"][l][0]
        if code not in readers:
            try: readers[code] = easyocr.Reader([code] if code in ("en", "ta") else [code, "en"], gpu=False, verbose=False)  # ta model already includes English
            except Exception as e: readers[code] = e
        if isinstance(readers[code], Exception): raise readers[code]
        return " ".join(readers[code].readtext(str(p), detail=0, paragraph=True))
    return run

def make_doctr():
    from doctr.io import DocumentFile
    from doctr.models import ocr_predictor
    m = ocr_predictor(pretrained=True)
    return lambda p, l: m(DocumentFile.from_images(str(p))).render()

def make_rapidocr():
    from rapidocr_onnxruntime import RapidOCR
    eng = RapidOCR()
    def run(p, l):
        res, _ = eng(str(p))
        return " ".join(r[1] for r in (res or []))
    return run

def make_paddle():
    from paddleocr import PaddleOCR
    models = {}
    def run(p, l):
        code = MODES["paddleocr"][l][0]
        if code not in models:
            models[code] = PaddleOCR(lang=code, use_doc_orientation_classify=False, use_doc_unwarping=False,
                                     use_textline_orientation=False, enable_mkldnn=False)  # oneDNN path crashes on paddle 3.3 CPU
        out = models[code].predict(str(p))
        return " ".join(t for r in out for t in r["rec_texts"])
    return run

def make_surya():
    # surya-ocr 0.17 (torch); 0.22+ needs llama-server, which this machine's App Control policy blocks.
    from PIL import Image
    from surya.detection import DetectionPredictor
    from surya.foundation import FoundationPredictor
    from surya.recognition import RecognitionPredictor
    det = DetectionPredictor()
    rec = RecognitionPredictor(FoundationPredictor())
    def run(p, l):
        res = rec([Image.open(p).convert("RGB")], det_predictor=det)[0]
        return " ".join(ln.text for ln in res.text_lines)
    return run

def make_indra():
    import cv2, indra_ocr
    conv = indra_ocr.load(threads=4, mode="ocr")
    def run(p, l):
        page = conv.ocr(cv2.imread(str(p), cv2.IMREAD_GRAYSCALE))
        return " ".join(ln.text for ln in page.lines)
    return run

ENGINES = dict(tesseract=make_tesseract, easyocr=make_easyocr, doctr=make_doctr, rapidocr=make_rapidocr,
               paddleocr=make_paddle, surya=make_surya, indra=make_indra)

if __name__ == "__main__":
    args = sys.argv[1:]
    num = lambda f: int(args[args.index(f) + 1]) if f in args else None
    limit, per_group = num("--limit"), num("--per-group")
    names = [a for a in args if a in ENGINES]
    (ROOT / "results/raw").mkdir(parents=True, exist_ok=True)
    for name in names:
        out_file = ROOT / "results/raw" / f"{name}.json"
        results = json.loads(out_file.read_text(encoding="utf-8")) if out_file.exists() else {}
        try:
            t0 = time.time(); run = ENGINES[name](); print(f"[{name}] init {time.time()-t0:.1f}s", flush=True)
        except Exception:
            print(f"[{name}] INIT FAILED\n{traceback.format_exc()}", flush=True); continue
        todo = [(k, p, l) for k, p, l in images(limit, per_group) if k not in results]
        print(f"[{name}] {len(todo)} images to run, {len(results)} cached", flush=True)
        for i, (key, path, lang) in enumerate(todo):
            spec, mode = MODES[name].get(lang, ("?", "none"))
            t0 = time.time()
            try: results[key] = {"text": run(path, lang), "sec": time.time() - t0, "error": None, "mode": mode, "model": spec}
            except Exception as e:
                results[key] = {"text": "", "sec": time.time() - t0, "error": f"{type(e).__name__}: {e}"[:200], "mode": mode, "model": spec}
            print(f"[{name}] {i+1}/{len(todo)} {key} {results[key]['sec']:.1f}s [{mode}] {results[key]['error'] or ''}", flush=True)
            if (i + 1) % 8 == 0: out_file.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
        out_file.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"[{name}] DONE {len(results)} results", flush=True)
