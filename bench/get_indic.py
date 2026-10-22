# Indic sets: real handwritten word images (IIIT-INDIC-HW-WORDS: Hindi, Tamil) and
# synthetic *printed* line images (OCR-Bench1000) for the languages with no public handwritten set found.
from pathlib import Path
from datasets import load_dataset
N = 30
def dump(repo, code, kind, split, **kw):
    out = Path("data") / kind; (out / "images").mkdir(parents=True, exist_ok=True); (out / "gt").mkdir(exist_ok=True)
    ds = load_dataset(repo, split=split, **kw).shuffle(seed=1).select(range(N))
    tcol = next(c for c in ("text", "label", "transcription", "ground_truth") if c in ds.column_names)
    for i, ex in enumerate(ds):
        ex["image"].convert("RGB").save(out / "images" / f"{code}_{i}.png")
        (out / "gt" / f"{code}_{i}.txt").write_text(ex[tcol], encoding="utf-8")
    print(kind, code, len(ds), flush=True)
for code, lang in (("hin", "Hindi"), ("tam", "Tamil")):
    dump(f"c3rl/IIIT-INDIC-HW-WORDS-{lang}", code, "handwritten", "test")
for code, lang in (("mal", "Malayalam"), ("kan", "Kannada"), ("tel", "Telugu"), ("mar", "Marathi"),
                   ("guj", "Gujarati"), ("ben", "Bengali"), ("pan", "Punjabi")):
    try: dump(f"meharuhanzz/OCR-Bench1000-{lang}", code, "printed_indic", "train")
    except Exception as e: print("FAILED", lang, repr(e)[:200], flush=True)
